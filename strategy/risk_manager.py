"""
Risk management module for the trading strategy.
"""
from dataclasses import dataclass
from typing import Optional
import pandas as pd

@dataclass
class RiskParameters:
    max_position_size: float  # Maximum position size in base currency
    max_leverage: float  # Maximum allowed leverage
    max_daily_loss: float  # Maximum daily loss as percentage of account
    max_open_trades: int  # Maximum number of open trades
    min_volume_24h: float  # Minimum 24h volume for trading
    min_market_cap: float  # Minimum market cap for trading

class RiskManager:
    def __init__(
        self,
        account_balance: float,
        risk_parameters: RiskParameters,
        atr_multiplier_stop: float = 2.0,
        atr_multiplier_tp: float = 3.0
    ):
        self.account_balance = account_balance
        self.risk_parameters = risk_parameters
        self.atr_multiplier_stop = atr_multiplier_stop
        self.atr_multiplier_tp = atr_multiplier_tp
        self.daily_pnl = 0.0
        self.open_trades = 0

    def calculate_stop_loss(
        self,
        entry_price: float,
        atr: float,
        direction: str
    ) -> float:
        """
        Calculate stop loss based on ATR.
        direction: 'long' or 'short'
        """
        if direction.lower() == 'long':
            return entry_price - (atr * self.atr_multiplier_stop)
        else:
            return entry_price + (atr * self.atr_multiplier_stop)

    def calculate_take_profit(
        self,
        entry_price: float,
        atr: float,
        direction: str
    ) -> float:
        """
        Calculate take profit based on ATR.
        direction: 'long' or 'short'
        """
        if direction.lower() == 'long':
            return entry_price + (atr * self.atr_multiplier_tp)
        else:
            return entry_price - (atr * self.atr_multiplier_tp)

    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss: float,
        leverage: float
    ) -> float:
        """
        Calculate position size based on risk parameters and account balance.
        Returns position size in base currency.
        """
        # Calculate risk per trade (2% of account)
        risk_amount = self.account_balance * 0.02
        
        # Calculate price risk
        price_risk = abs(entry_price - stop_loss)
        
        # Calculate base position size
        position_size = risk_amount / price_risk
        
        # Apply leverage
        leveraged_size = position_size * leverage
        
        # Ensure we don't exceed max position size
        return min(leveraged_size, self.risk_parameters.max_position_size)

    def validate_trade(
        self,
        symbol: str,
        direction: str,
        position_size: float,
        leverage: float,
        volume_24h: float,
        market_cap: float
    ) -> tuple[bool, str]:
        """
        Validate if a trade meets risk management criteria.
        Returns (is_valid, reason_if_invalid)
        """
        # Check leverage
        if leverage > self.risk_parameters.max_leverage:
            return False, f"Leverage {leverage}x exceeds maximum {self.risk_parameters.max_leverage}x"
            
        # Check position size
        if position_size > self.risk_parameters.max_position_size:
            return False, f"Position size {position_size} exceeds maximum {self.risk_parameters.max_position_size}"
            
        # Check open trades
        if self.open_trades >= self.risk_parameters.max_open_trades:
            return False, f"Maximum open trades ({self.risk_parameters.max_open_trades}) reached"
            
        # Check daily loss limit
        if self.daily_pnl <= -self.account_balance * self.risk_parameters.max_daily_loss:
            return False, "Daily loss limit reached"
            
        # Check volume
        if volume_24h < self.risk_parameters.min_volume_24h:
            return False, f"24h volume {volume_24h} below minimum {self.risk_parameters.min_volume_24h}"
            
        # Check market cap
        if market_cap < self.risk_parameters.min_market_cap:
            return False, f"Market cap {market_cap} below minimum {self.risk_parameters.min_market_cap}"
            
        return True, "Trade validated"

    def update_daily_pnl(self, pnl: float) -> None:
        """Update daily P&L tracking."""
        self.daily_pnl += pnl

    def increment_open_trades(self) -> None:
        """Increment open trades counter."""
        self.open_trades += 1

    def decrement_open_trades(self) -> None:
        """Decrement open trades counter."""
        self.open_trades = max(0, self.open_trades - 1)

    def reset_daily_stats(self) -> None:
        """Reset daily statistics."""
        self.daily_pnl = 0.0
        self.open_trades = 0 