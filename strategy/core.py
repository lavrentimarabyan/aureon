"""
Core implementation of the high-confidence trend-following crypto trading strategy.
"""
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from dataclasses import dataclass
from enum import Enum

class TradeDirection(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"

@dataclass
class TradeSignal:
    direction: TradeDirection
    confidence_score: float
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float
    timestamp: pd.Timestamp

class TrendFollowingStrategy:
    def __init__(
        self,
        rsi_period: int = 14,
        ema_fast: int = 20,
        ema_slow: int = 50,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        bb_period: int = 20,
        bb_std: float = 2.0,
        adx_period: int = 14,
        adx_threshold: float = 25.0,
        atr_period: int = 14,
        risk_per_trade: float = 0.02,  # 2% risk per trade
    ):
        self.rsi_period = rsi_period
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold
        self.atr_period = atr_period
        self.risk_per_trade = risk_per_trade

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators required for the strategy."""
        # RSI
        df['rsi'] = self._calculate_rsi(df['close'])
        
        # EMAs
        df['ema_fast'] = df['close'].ewm(span=self.ema_fast, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=self.ema_slow, adjust=False).mean()
        
        # MACD
        df['macd'], df['macd_signal'], df['macd_hist'] = self._calculate_macd(df['close'])
        
        # Bollinger Bands
        df['bb_middle'], df['bb_upper'], df['bb_lower'] = self._calculate_bollinger_bands(df['close'])
        
        # ADX
        df['adx'], df['plus_di'], df['minus_di'] = self._calculate_adx(df)
        
        # ATR
        df['atr'] = self._calculate_atr(df)
        
        return df

    def analyze_market(self, df: pd.DataFrame) -> Tuple[TradeDirection, float]:
        """
        Analyze market conditions and return trade direction with confidence score.
        Returns (TradeDirection, confidence_score)
        """
        # Calculate all indicators
        df = self.calculate_indicators(df)
        
        # Get latest values
        latest = df.iloc[-1]
        
        # Initialize scoring
        long_score = 0
        short_score = 0
        max_score = 7  # Total possible points
        
        # 1. RSI Analysis (1 point)
        if latest['rsi'] > 50 and latest['rsi'] < 70:
            long_score += 1
        elif latest['rsi'] < 50 and latest['rsi'] > 30:
            short_score += 1
            
        # 2. EMA Trend Analysis (2 points)
        if latest['ema_fast'] > latest['ema_slow']:
            long_score += 2
        elif latest['ema_fast'] < latest['ema_slow']:
            short_score += 2
            
        # 3. MACD Analysis (1 point)
        if latest['macd'] > latest['macd_signal'] and latest['macd_hist'] > 0:
            long_score += 1
        elif latest['macd'] < latest['macd_signal'] and latest['macd_hist'] < 0:
            short_score += 1
            
        # 4. Bollinger Bands Analysis (1 point)
        if latest['close'] > latest['bb_upper']:
            long_score += 1
        elif latest['close'] < latest['bb_lower']:
            short_score += 1
            
        # 5. ADX and Volume Analysis (2 points)
        if latest['adx'] > self.adx_threshold:
            if latest['plus_di'] > latest['minus_di']:
                long_score += 2
            elif latest['minus_di'] > latest['plus_di']:
                short_score += 2
                
        # Calculate confidence scores
        long_confidence = long_score / max_score
        short_confidence = short_score / max_score
        
        # Determine trade direction
        if long_confidence >= 0.85:  # 85% confidence threshold
            return TradeDirection.LONG, long_confidence
        elif short_confidence >= 0.85:
            return TradeDirection.SHORT, short_confidence
        else:
            return TradeDirection.NEUTRAL, max(long_confidence, short_confidence)

    def calculate_position_size(
        self,
        account_balance: float,
        entry_price: float,
        stop_loss: float
    ) -> float:
        """Calculate position size based on risk management rules."""
        risk_amount = account_balance * self.risk_per_trade
        price_risk = abs(entry_price - stop_loss)
        position_size = risk_amount / price_risk
        return position_size

    def _calculate_rsi(self, prices: pd.Series) -> pd.Series:
        """Calculate RSI indicator."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def _calculate_macd(
        self,
        prices: pd.Series
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD indicator."""
        exp1 = prices.ewm(span=self.macd_fast, adjust=False).mean()
        exp2 = prices.ewm(span=self.macd_slow, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=self.macd_signal, adjust=False).mean()
        hist = macd - signal
        return macd, signal, hist

    def _calculate_bollinger_bands(
        self,
        prices: pd.Series
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands."""
        middle = prices.rolling(window=self.bb_period).mean()
        std = prices.rolling(window=self.bb_period).std()
        upper = middle + (std * self.bb_std)
        lower = middle - (std * self.bb_std)
        return middle, upper, lower

    def _calculate_adx(
        self,
        df: pd.DataFrame
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate ADX indicator."""
        high = df['high']
        low = df['low']
        close = df['close']
        
        # Calculate True Range
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Calculate Directional Movement
        up_move = high - high.shift()
        down_move = low.shift() - low
        
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        # Calculate smoothed averages
        tr_smoothed = tr.rolling(window=self.adx_period).sum()
        plus_di = 100 * pd.Series(plus_dm).rolling(window=self.adx_period).sum() / tr_smoothed
        minus_di = 100 * pd.Series(minus_dm).rolling(window=self.adx_period).sum() / tr_smoothed
        
        # Calculate ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=self.adx_period).mean()
        
        return adx, plus_di, minus_di

    def _calculate_atr(self, df: pd.DataFrame) -> pd.Series:
        """Calculate Average True Range."""
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=self.atr_period).mean()
        
        return atr 