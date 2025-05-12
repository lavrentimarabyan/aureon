"""
Trade execution module for handling order placement and management.
"""
from dataclasses import dataclass
from typing import Optional, Dict, List
import pandas as pd
from datetime import datetime
import ccxt
from .core import TradeDirection, TradeSignal

@dataclass
class Order:
    symbol: str
    direction: TradeDirection
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float
    leverage: float
    timestamp: datetime
    order_id: Optional[str] = None
    status: str = "PENDING"

class TradeExecutor:
    def __init__(
        self,
        exchange: ccxt.Exchange,
        risk_manager,
        max_slippage: float = 0.001  # 0.1% max slippage
    ):
        self.exchange = exchange
        self.risk_manager = risk_manager
        self.max_slippage = max_slippage
        self.open_orders: Dict[str, Order] = {}

    async def execute_trade(self, signal: TradeSignal, symbol: str) -> Optional[Order]:
        """
        Execute a trade based on the signal.
        Returns Order object if successful, None if failed.
        """
        try:
            # Validate market conditions
            ticker = await self.exchange.fetch_ticker(symbol)
            volume_24h = ticker['quoteVolume']
            market_cap = await self._get_market_cap(symbol)

            # Calculate position size and validate
            position_size = self.risk_manager.calculate_position_size(
                signal.entry_price,
                signal.stop_loss,
                signal.leverage
            )

            # Validate trade against risk parameters
            is_valid, reason = self.risk_manager.validate_trade(
                symbol=symbol,
                direction=signal.direction.value,
                position_size=position_size,
                leverage=signal.leverage,
                volume_24h=volume_24h,
                market_cap=market_cap
            )

            if not is_valid:
                print(f"Trade validation failed: {reason}")
                return None

            # Create order
            order = Order(
                symbol=symbol,
                direction=signal.direction,
                entry_price=signal.entry_price,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                position_size=position_size,
                leverage=signal.leverage,
                timestamp=datetime.now()
            )

            # Set leverage
            await self.exchange.set_leverage(signal.leverage, symbol)

            # Place entry order
            entry_order = await self._place_entry_order(order)
            if not entry_order:
                return None

            # Place stop loss and take profit orders
            await self._place_exit_orders(order)

            # Update risk manager
            self.risk_manager.increment_open_trades()
            self.open_orders[entry_order['id']] = order

            return order

        except Exception as e:
            print(f"Error executing trade: {str(e)}")
            return None

    async def _place_entry_order(self, order: Order) -> Optional[Dict]:
        """Place the entry order."""
        try:
            side = "buy" if order.direction == TradeDirection.LONG else "sell"
            
            # Calculate slippage-adjusted price
            slippage = order.entry_price * self.max_slippage
            adjusted_price = (
                order.entry_price + slippage if side == "buy"
                else order.entry_price - slippage
            )

            # Place market order
            entry_order = await self.exchange.create_order(
                symbol=order.symbol,
                type='market',
                side=side,
                amount=order.position_size
            )

            return entry_order

        except Exception as e:
            print(f"Error placing entry order: {str(e)}")
            return None

    async def _place_exit_orders(self, order: Order) -> None:
        """Place stop loss and take profit orders."""
        try:
            # Place stop loss
            sl_side = "sell" if order.direction == TradeDirection.LONG else "buy"
            await self.exchange.create_order(
                symbol=order.symbol,
                type='stop',
                side=sl_side,
                amount=order.position_size,
                price=order.stop_loss,
                params={'stopPrice': order.stop_loss}
            )

            # Place take profit
            tp_side = "sell" if order.direction == TradeDirection.LONG else "buy"
            await self.exchange.create_order(
                symbol=order.symbol,
                type='limit',
                side=tp_side,
                amount=order.position_size,
                price=order.take_profit
            )

        except Exception as e:
            print(f"Error placing exit orders: {str(e)}")
            # Cancel entry order if exit orders fail
            await self.cancel_order(order.order_id)

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order and clean up."""
        try:
            await self.exchange.cancel_order(order_id)
            if order_id in self.open_orders:
                self.risk_manager.decrement_open_trades()
                del self.open_orders[order_id]
            return True
        except Exception as e:
            print(f"Error canceling order: {str(e)}")
            return False

    async def _get_market_cap(self, symbol: str) -> float:
        """Get market cap for a symbol."""
        try:
            # This is a placeholder - you'll need to implement actual market cap fetching
            # Could use CoinGecko API or similar
            return 1_000_000_000  # Placeholder value
        except Exception as e:
            print(f"Error getting market cap: {str(e)}")
            return 0.0

    async def update_order_status(self, order_id: str) -> None:
        """Update status of an order."""
        try:
            order_info = await self.exchange.fetch_order(order_id)
            if order_id in self.open_orders:
                self.open_orders[order_id].status = order_info['status']
                
                # If order is closed, update risk manager
                if order_info['status'] == 'closed':
                    self.risk_manager.decrement_open_trades()
                    # Calculate and update P&L
                    pnl = self._calculate_pnl(order_info)
                    self.risk_manager.update_daily_pnl(pnl)
                    del self.open_orders[order_id]

        except Exception as e:
            print(f"Error updating order status: {str(e)}")

    def _calculate_pnl(self, order_info: Dict) -> float:
        """Calculate P&L for a closed order."""
        try:
            if order_info['side'] == 'buy':
                return (order_info['price'] - order_info['cost']) * order_info['amount']
            else:
                return (order_info['cost'] - order_info['price']) * order_info['amount']
        except Exception as e:
            print(f"Error calculating P&L: {str(e)}")
            return 0.0 