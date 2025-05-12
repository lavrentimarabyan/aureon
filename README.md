# High-Confidence Trend-Following Crypto Trading Strategy

A robust, conservative trend-following strategy for cryptocurrency markets that focuses on high-probability setups with strict risk management.

## Strategy Overview

This trading strategy implements a high-confidence, conservative trend-following system for crypto markets. It focuses on quality over quantity – only entering trades when multiple trusted indicators all confirm the same direction. The goal is to capture significant moves in the direction of the prevailing trend while avoiding false signals.

### Key Features

- Multi-indicator confirmation system
- Strict risk management (1-2% risk per trade)
- ATR-based stop loss and take profit levels
- Position sizing based on account risk
- Support for multiple timeframes
- Real-time market analysis
- Automated trade execution
- Comprehensive logging and monitoring

## Technical Indicators Used

1. **RSI (Relative Strength Index)**
   - Period: 14
   - Used to confirm momentum direction
   - Avoids extreme overbought/oversold conditions

2. **EMA Crossovers (20 & 50)**
   - Fast EMA: 20 periods
   - Slow EMA: 50 periods
   - Confirms trend direction and strength

3. **MACD (Moving Average Convergence Divergence)**
   - Fast: 12 periods
   - Slow: 26 periods
   - Signal: 9 periods
   - Confirms momentum and trend changes

4. **Bollinger Bands**
   - Period: 20
   - Standard Deviation: 2
   - Identifies volatility and potential breakouts

5. **ADX (Average Directional Index)**
   - Period: 14
   - Threshold: 25
   - Confirms trend strength

6. **ATR (Average True Range)**
   - Period: 14
   - Used for stop loss and take profit calculations

## Entry Conditions

### Long (Buy) Setup
- RSI above 50 and rising (but below 70)
- 20 EMA above 50 EMA
- MACD line above signal line with positive histogram
- Price above upper Bollinger Band or breaking out
- ADX above 25 with +DI above -DI
- Volume confirmation

### Short (Sell) Setup
- RSI below 50 and falling (but above 30)
- 20 EMA below 50 EMA
- MACD line below signal line with negative histogram
- Price below lower Bollinger Band or breaking down
- ADX above 25 with -DI above +DI
- Volume confirmation

## Risk Management

- Maximum 1-2% risk per trade
- Stop loss: 2 × ATR from entry
- Take profit: 3 × ATR from entry
- Maximum leverage: 15-25x (configurable)
- Maximum daily loss: 5% of account
- Maximum open trades: 3
- Minimum 24h volume: $1M
- Minimum market cap: $100M

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/crypto-trading-strategy.git
cd crypto-trading-strategy
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your exchange API credentials:
```
EXCHANGE_API_KEY=your_api_key
EXCHANGE_API_SECRET=your_api_secret
```

## Usage

1. Configure the strategy parameters in `strategy/config.py`:
   - Adjust risk parameters
   - Set trading pairs
   - Configure timeframes
   - Modify indicator settings

2. Run the strategy:
```bash
python main.py
```

The bot will:
- Connect to the exchange
- Monitor configured trading pairs
- Analyze market conditions
- Execute trades when conditions are met
- Manage open positions
- Log all activities

## Configuration Options

The strategy offers three pre-configured risk profiles:

1. **Default Configuration**
   - 2% risk per trade
   - 25x maximum leverage
   - 5% maximum daily loss
   - 3 maximum open trades

2. **Production Configuration** (More Conservative)
   - 1% risk per trade
   - 15x maximum leverage
   - 3% maximum daily loss
   - 2 maximum open trades

3. **Aggressive Configuration** (For Experienced Traders)
   - 3% risk per trade
   - 25x maximum leverage
   - 7% maximum daily loss
   - 4 maximum open trades

## Logging

The strategy logs all activities to `trading.log` with the following information:
- Trade entries and exits
- Order status updates
- Error messages
- Account balance updates
- Market analysis results

## Safety Features

1. **Exchange Integration**
   - Uses CCXT library for reliable exchange connectivity
   - Supports multiple exchanges
   - Handles API rate limits

2. **Error Handling**
   - Comprehensive exception handling
   - Automatic retry on temporary failures
   - Graceful shutdown on critical errors

3. **Risk Controls**
   - Position size limits
   - Daily loss limits
   - Maximum open trades
   - Minimum volume requirements
   - Market cap filters

## Performance Monitoring

The strategy includes built-in performance tracking:
- Trade success rate
- Average win/loss ratio
- Maximum drawdown
- Daily P&L tracking
- Position management statistics

## Disclaimer

This trading strategy is provided for educational purposes only. Cryptocurrency trading involves significant risk. Always:
- Test thoroughly in a paper trading environment first
- Start with small position sizes
- Monitor the strategy's performance
- Never risk more than you can afford to lose

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 