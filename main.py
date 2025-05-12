"""
Main script to run the high-confidence trend-following crypto trading strategy.
"""
import asyncio
import ccxt.async_support as ccxt
import pandas as pd
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv
import json
import hmac
import hashlib
import time
import urllib.parse
import telegram
from telegram.ext import Application

from strategy.core import TrendFollowingStrategy, TradeDirection, TradeSignal
from strategy.risk_manager import RiskManager, RiskParameters
from strategy.config import StrategyConfig, PRODUCTION_CONFIG

# Set up logging
logging.basicConfig(
    level=logging.INFO,  # Changed from DEBUG to INFO
    format='%(asctime)s - %(levelname)s - %(message)s',  # Simplified format
    handlers=[
        logging.FileHandler('trading.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_environment():
    """Load environment variables and verify API credentials."""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    logger.debug(f"Looking for .env file at: {env_path}")

    if not os.path.exists(env_path):
        raise FileNotFoundError(f".env file not found at {env_path}")

    load_dotenv(env_path)
    api_key = os.getenv('EXCHANGE_API_KEY')
    api_secret = os.getenv('EXCHANGE_API_SECRET')
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')

    if not api_key or not api_secret:
        raise ValueError("API credentials not found in environment variables")
    if not telegram_token or not telegram_chat_id:
        raise ValueError("Telegram credentials not found in environment variables")

    # Log API key details (first 4 and last 4 characters only)
    masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"
    logger.info(f"Loaded API key: {masked_key}")

    return api_key, api_secret, telegram_token, telegram_chat_id

class SignalBot:
    def __init__(
        self,
        config: StrategyConfig,
        exchange_id: str = 'binance'
    ):
        self.config = config
        self.exchange_id = exchange_id

        # Load environment variables
        self.api_key, self.api_secret, self.telegram_token, self.telegram_chat_id = load_environment()

        # Initialize exchange
        self.exchange = self._initialize_exchange()

        # Initialize strategy components
        self.strategy = TrendFollowingStrategy(
            rsi_period=config.rsi_period,
            ema_fast=config.ema_fast,
            ema_slow=config.ema_slow,
            macd_fast=config.macd_fast,
            macd_slow=config.macd_slow,
            macd_signal=config.macd_signal,
            bb_period=config.bb_period,
            bb_std=config.bb_std,
            adx_period=config.adx_period,
            adx_threshold=config.adx_threshold,
            atr_period=config.atr_period,
            risk_per_trade=config.risk_per_trade
        )

        # Initialize Telegram bot
        self.telegram_bot = Application.builder().token(self.telegram_token).build()

        # Store market data
        self.market_data: Dict[str, Dict[str, pd.DataFrame]] = {}

        # Store last sent signals to avoid duplicates
        self.last_signals: Dict[str, TradeSignal] = {}

    async def _validate_api_credentials(self) -> bool:
        """Validate API credentials by making a test request."""
        try:
            # Log the request details
            logger.debug("Attempting to fetch account information...")

            # Try to fetch account information
            balance = await self.exchange.fetch_balance()
            logger.info("API credentials validated successfully")
            logger.debug(f"Account balance: {json.dumps(balance, indent=2)}")
            return True
        except ccxt.AuthenticationError as e:
            logger.error(f"Authentication error: {str(e)}")
            logger.error("Please check your API key permissions and IP whitelist settings")
            return False
        except Exception as e:
            logger.error(f"Error validating API credentials: {str(e)}")
            return False

    def _initialize_exchange(self) -> ccxt.Exchange:
        """Initialize exchange connection."""
        try:
            # Initialize exchange with loaded credentials
            exchange_class = getattr(ccxt, self.exchange_id)

            # Configure exchange options
            exchange_options = {
                'apiKey': self.api_key,
                'secret': self.api_secret,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future',
                    'adjustForTimeDifference': True,
                    'recvWindow': 60000,
                    'createMarketBuyOrderRequiresPrice': False,
                    'defaultContractType': 'perpetual',
                    'fetchMarkets': {
                        'method': 'fapiPublicGetExchangeInfo'
                    },
                    'fetchBalance': {
                        'method': 'fapiPrivateGetAccount'
                    }
                }
            }

            # Log exchange configuration
            logger.debug("Initializing exchange with options:")
            logger.debug(f"Exchange ID: {self.exchange_id}")
            logger.debug(f"Default Type: {exchange_options['options']['defaultType']}")
            logger.debug(f"Contract Type: {exchange_options['options']['defaultContractType']}")

            exchange = exchange_class(exchange_options)
            logger.info("Exchange initialized successfully")
            return exchange

        except Exception as e:
            logger.error(f"Error initializing exchange: {str(e)}")
            raise

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 100
    ) -> pd.DataFrame:
        """Fetch OHLCV data for a symbol."""
        try:
            logger.debug(f"Fetching OHLCV data for {symbol} ({timeframe})")
            ohlcv = await self.exchange.fetch_ohlcv(
                symbol,
                timeframe=timeframe,
                limit=limit
            )

            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            df = df.astype({
                'open': 'float64',
                'high': 'float64',
                'low': 'float64',
                'close': 'float64',
                'volume': 'float64'
            })
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)

            logger.info(f"Successfully fetched {len(df)} candles for {symbol}")
            return df

        except Exception as e:
            logger.error(f"Error fetching OHLCV data for {symbol}: {str(e)}")
            return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error fetching OHLCV data: {str(e)}")
            return pd.DataFrame()

    async def update_market_data(self) -> None:
        """Update market data for all trading pairs and timeframes."""
        for symbol in self.config.trading_pairs:
            self.market_data[symbol] = {}
            for timeframe in self.config.timeframes:
                df = await self.fetch_ohlcv(symbol, timeframe)
                if not df.empty:
                    self.market_data[symbol][timeframe] = df

    async def send_signal(self, symbol: str, signal: TradeSignal) -> None:
        """Send trading signal via Telegram."""
        try:
            # Format the signal message
            message = (
                f"🚨 *Trading Signal Alert* 🚨\n\n"
                f"Symbol: {symbol}\n"
                f"Direction: {signal.direction.value}\n"
                f"Confidence: {signal.confidence_score:.2%}\n"
                f"Entry Price: {signal.entry_price:.8f}\n"
                f"Stop Loss: {signal.stop_loss:.8f}\n"
                f"Take Profit: {signal.take_profit:.8f}\n"
                f"Time: {signal.timestamp}\n\n"
                f"Technical Analysis:\n"
                f"- RSI: {self.market_data[symbol][self.config.timeframes[0]].iloc[-1]['rsi']:.2f}\n"
                f"- MACD: {self.market_data[symbol][self.config.timeframes[0]].iloc[-1]['macd']:.2f}\n"
                f"- ADX: {self.market_data[symbol][self.config.timeframes[0]].iloc[-1]['adx']:.2f}\n"
                f"- ATR: {self.market_data[symbol][self.config.timeframes[0]].iloc[-1]['atr']:.8f}\n\n"
                f"Risk Management:\n"
                f"- Risk per trade: {self.config.risk_per_trade:.1%}\n"
                f"- Max position size: {self.config.max_position_size} USDT\n"
                f"- Max daily loss: {self.config.max_daily_loss:.1%}\n"
            )

            # Send the message
            await self.telegram_bot.bot.send_message(
                chat_id=self.telegram_chat_id,
                text=message,
                parse_mode='Markdown'
            )
            logger.info(f"Signal sent for {symbol}")

        except Exception as e:
            logger.error(f"Error sending signal: {str(e)}")

    async def analyze_markets(self) -> None:
        """Analyze all markets and send trading signals."""
        for symbol in self.config.trading_pairs:
            # Get highest timeframe data for trend confirmation
            highest_tf = self.config.timeframes[-1]
            if highest_tf not in self.market_data[symbol]:
                continue

            df = self.market_data[symbol][highest_tf]

            # Analyze market
            direction, confidence = self.strategy.analyze_market(df)

            if direction != TradeDirection.NEUTRAL and confidence >= 0.50:
                # Get entry timeframe data for precise entry
                entry_tf = self.config.timeframes[0]  # Use lowest timeframe for entry
                if entry_tf not in self.market_data[symbol]:
                    continue

                entry_df = self.market_data[symbol][entry_tf]
                latest = entry_df.iloc[-1]

                # Calculate stop loss and take profit
                atr = latest['atr']
                entry_price = latest['close']

                # Create signal
                signal = TradeSignal(
                    direction=direction,
                    confidence_score=confidence,
                    entry_price=entry_price,
                    stop_loss=entry_price - (2 * atr) if direction == TradeDirection.LONG else entry_price + (2 * atr),
                    take_profit=entry_price + (3 * atr) if direction == TradeDirection.LONG else entry_price - (3 * atr),
                    position_size=0.0,  # Not needed for signals
                    timestamp=latest.name
                )

                # Check if this is a new signal
                last_signal = self.last_signals.get(symbol)
                if (not last_signal or 
                    last_signal.direction != signal.direction or 
                    (latest.name - last_signal.timestamp).total_seconds() > 3600):  # 1 hour minimum between signals

                    # Send the signal
                    await self.send_signal(symbol, signal)

                    # Update last signal
                    self.last_signals[symbol] = signal

    async def start(self) -> None:
        """Start the signal bot."""
        try:
            # Validate API credentials first
            if not await self._validate_api_credentials():
                raise ValueError("Failed to validate API credentials")

            # Start the Telegram bot
            await self.telegram_bot.initialize()
            await self.telegram_bot.start()

            # Send startup message
            await self.telegram_bot.bot.send_message(
                chat_id=self.telegram_chat_id,
                text="🚀 Signal Bot Started\nMonitoring markets for trading opportunities..."
            )

            while True:
                try:
                    # Update trading pairs dynamically
                    self.config.trading_pairs = await self.strategy.select_active_pairs(self.exchange)
                    logger.info(f"Selected pairs for trading: {self.config.trading_pairs}")

                    # Update market data
                    await self.update_market_data()

                    # Analyze markets and send signals
                    await self.analyze_markets()

                    # Wait before next iteration
                    await asyncio.sleep(60)  # Check every minute

                except Exception as e:
                    logger.error(f"Error in main loop: {str(e)}")
                    await asyncio.sleep(60)  # Wait before retrying

        except Exception as e:
            logger.error(f"Fatal error: {str(e)}")
        finally:
            await self.exchange.close()
            await self.telegram_bot.stop()

async def main():
    """Main entry point."""
    # Initialize and start the signal bot
    bot = SignalBot(
        config=PRODUCTION_CONFIG,
        exchange_id='binance'
    )

    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot stopped due to error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())