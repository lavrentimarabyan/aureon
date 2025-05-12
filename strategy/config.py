"""
Configuration module for strategy parameters.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from .risk_manager import RiskParameters

@dataclass
class StrategyConfig:
    # Technical indicator parameters
    rsi_period: int = 14
    ema_fast: int = 20
    ema_slow: int = 50
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    bb_period: int = 20
    bb_std: float = 2.0
    adx_period: int = 14
    adx_threshold: float = 25.0
    atr_period: int = 14

    # Risk management parameters
    risk_per_trade: float = 0.02  # 2% risk per trade
    max_leverage: float = 25.0
    max_position_size: float = 1.0  # in BTC
    max_daily_loss: float = 0.05  # 5% max daily loss
    max_open_trades: int = 3
    min_volume_24h: float = 1_000_000  # $1M minimum 24h volume
    min_market_cap: float = 100_000_000  # $100M minimum market cap

    # Trade execution parameters
    max_slippage: float = 0.001  # 0.1% max slippage
    use_market_orders: bool = True
    default_leverage: float = 15.0

    # Trading pairs to monitor
    trading_pairs: List[str] = field(default_factory=lambda: [
        "BTC/USDT",
        "ETH/USDT",
        "BNB/USDT",
        "SOL/USDT",
        "ADA/USDT"
    ])

    # Timeframes to analyze
    timeframes: List[str] = field(default_factory=lambda: [
        "1h",
        "4h",
        "1d"
    ])

    # Exchange configuration
    exchange_config: Dict = field(default_factory=dict)

    def get_risk_parameters(self) -> RiskParameters:
        """Convert config to RiskParameters object."""
        return RiskParameters(
            max_position_size=self.max_position_size,
            max_leverage=self.max_leverage,
            max_daily_loss=self.max_daily_loss,
            max_open_trades=self.max_open_trades,
            min_volume_24h=self.min_volume_24h,
            min_market_cap=self.min_market_cap
        )

# Default configuration
DEFAULT_CONFIG = StrategyConfig()

# Production configuration with more conservative settings
PRODUCTION_CONFIG = StrategyConfig(
    risk_per_trade=0.01,  # 1% risk per trade
    max_leverage=15.0,
    max_daily_loss=0.03,  # 3% max daily loss
    max_open_trades=2,
    min_volume_24h=5_000_000,  # $5M minimum 24h volume
    min_market_cap=500_000_000,  # $500M minimum market cap
    default_leverage=10.0
)

# Aggressive configuration for experienced traders
AGGRESSIVE_CONFIG = StrategyConfig(
    risk_per_trade=0.03,  # 3% risk per trade
    max_leverage=25.0,
    max_daily_loss=0.07,  # 7% max daily loss
    max_open_trades=4,
    min_volume_24h=500_000,  # $500K minimum 24h volume
    min_market_cap=50_000_000,  # $50M minimum market cap
    default_leverage=20.0
) 