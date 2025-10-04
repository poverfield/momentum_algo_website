"""
Alpaca Service - Handles paper trading through Alpaca API
"""
import os
import logging
from typing import Dict, Optional, List
from datetime import datetime
import alpaca_trade_api as tradeapi

logger = logging.getLogger(__name__)

class AlpacaService:
    def __init__(self):
        self.api_key = os.getenv('ALPACA_API_KEY')
        self.secret_key = os.getenv('ALPACA_SECRET_KEY')
        self.base_url = os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')
        # Whether to mark orders as eligible for extended hours
        self.extended_hours = os.getenv('EXTENDED_HOURS', 'false').lower() == 'true'
        
        if not self.api_key or not self.secret_key:
            logger.warning("Alpaca API credentials not found in environment variables")
            self.api = None
        else:
            try:
                self.api = tradeapi.REST(
                    self.api_key,
                    self.secret_key,
                    self.base_url,
                    api_version='v2'
                )
                logger.info(f"Alpaca API initialized with base URL: {self.base_url}")
                logger.info(f"Alpaca extended_hours enabled: {self.extended_hours}")
            except Exception as e:
                logger.error(f"Failed to initialize Alpaca API: {e}")
                self.api = None
    
    def is_connected(self) -> bool:
        """Check if Alpaca API is connected and working"""
        try:
            if self.api is None:
                return False
            
            # Try to get account info
            account = self.api.get_account()
            return account is not None
            
        except Exception as e:
            logger.error(f"Alpaca connection check failed: {e}")
            return False
    
    def get_account_info(self) -> Optional[Dict]:
        """Get account information"""
        try:
            if self.api is None:
                return None
            
            account = self.api.get_account()
            
            def to_float(value):
                try:
                    return float(value) if value is not None else None
                except Exception:
                    return None
            
            def to_int(value):
                try:
                    return int(value) if value is not None else None
                except Exception:
                    return None
            
            # Use getattr with defaults since fields may vary across API versions
            return {
                'account_id': getattr(account, 'id', None),
                'status': getattr(account, 'status', None),
                'currency': getattr(account, 'currency', None),
                'buying_power': to_float(getattr(account, 'buying_power', None)),
                'cash': to_float(getattr(account, 'cash', None)),
                'portfolio_value': to_float(getattr(account, 'portfolio_value', None)),
                'equity': to_float(getattr(account, 'equity', None)),
                'last_equity': to_float(getattr(account, 'last_equity', None)),
                'multiplier': to_int(getattr(account, 'multiplier', None)),
                'day_trade_count': to_int(getattr(account, 'day_trade_count', None)),
                'daytrade_buying_power': to_float(getattr(account, 'daytrade_buying_power', None)),
                'pattern_day_trader': getattr(account, 'pattern_day_trader', None),
                'trading_blocked': getattr(account, 'trading_blocked', None),
                'transfers_blocked': getattr(account, 'transfers_blocked', None),
                'account_blocked': getattr(account, 'account_blocked', None),
                'created_at': getattr(account, 'created_at', None),
                'trade_suspended_by_user': getattr(account, 'trade_suspended_by_user', None),
                'shorting_enabled': getattr(account, 'shorting_enabled', None),
                'long_market_value': to_float(getattr(account, 'long_market_value', None)),
                'short_market_value': to_float(getattr(account, 'short_market_value', None)),
                'initial_margin': to_float(getattr(account, 'initial_margin', None)),
                'maintenance_margin': to_float(getattr(account, 'maintenance_margin', None))
            }
        
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return None
    
    def get_account_value(self) -> float:
        """Get total account value"""
        try:
            if self.api is None:
                return 0.0
            
            account = self.api.get_account()
            return float(account.portfolio_value)
            
        except Exception as e:
            logger.error(f"Error getting account value: {e}")
            return 0.0
    
    def get_positions(self) -> List[Dict]:
        """Get all current positions"""
        try:
            if self.api is None:
                return []
            
            positions = self.api.list_positions()
            
            position_list = []
            for position in positions:
                position_list.append({
                    'symbol': position.symbol,
                    'quantity': int(position.qty),
                    'side': position.side,
                    'market_value': float(position.market_value),
                    'cost_basis': float(position.cost_basis),
                    'unrealized_pl': float(position.unrealized_pl),
                    'unrealized_plpc': float(position.unrealized_plpc),
                    'current_price': float(position.current_price),
                    'lastday_price': float(position.lastday_price),
                    'change_today': float(position.change_today),
                    'avg_entry_price': float(position.avg_entry_price)
                })
            
            return position_list
            
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """Get position for a specific symbol"""
        try:
            if self.api is None:
                return None
            
            position = self.api.get_position(symbol)
            
            return {
                'symbol': position.symbol,
                'quantity': int(position.qty),
                'side': position.side,
                'market_value': float(position.market_value),
                'cost_basis': float(position.cost_basis),
                'unrealized_pl': float(position.unrealized_pl),
                'unrealized_plpc': float(position.unrealized_plpc),
                'current_price': float(position.current_price),
                'lastday_price': float(position.lastday_price),
                'change_today': float(position.change_today),
                'avg_entry_price': float(position.avg_entry_price)
            }
            
        except Exception as e:
            logger.warning(f"Error getting position for {symbol}: {e}")
            return None
    
    def place_buy_order(self, symbol: str, quantity: int, order_type: str = 'market', limit_price: Optional[float] = None) -> Dict:
        """
        Place a buy order
        Returns dict with success status and order details or error message
        """
        try:
            if self.api is None:
                return {'success': False, 'error': 'Alpaca API not initialized'}
            
            # Validate inputs
            if quantity <= 0:
                return {'success': False, 'error': 'Quantity must be positive'}
            
            # Extended hours eligibility requires DAY limit orders only
            if self.extended_hours:
                order_type = 'limit'
                if limit_price is None:
                    return {'success': False, 'error': 'Extended hours requires limit orders with limit_price'}

            params = dict(
                symbol=symbol,
                qty=quantity,
                side='buy',
                type=order_type,
                time_in_force='day',
                extended_hours=self.extended_hours
            )
            if order_type == 'limit':
                if limit_price is None:
                    return {'success': False, 'error': 'limit_price is required for limit orders'}
                params['limit_price'] = limit_price

            # Place the order
            order = self.api.submit_order(**params)
            
            logger.info(f"Buy order placed: {quantity} shares of {symbol}")
            
            return {
                'success': True,
                'order_id': order.id,
                'symbol': order.symbol,
                'quantity': int(order.qty),
                'side': order.side,
                'type': order.type,
                'status': order.status,
                'submitted_at': order.submitted_at,
                'filled_at': order.filled_at,
                'filled_qty': int(order.filled_qty) if order.filled_qty else 0,
                'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else None
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error placing buy order for {symbol}: {error_msg}")
            return {'success': False, 'error': error_msg}
    
    def place_sell_order(self, symbol: str, quantity: int, order_type: str = 'market', limit_price: Optional[float] = None) -> Dict:
        """
        Place a sell order
        Returns dict with success status and order details or error message
        """
        try:
            if self.api is None:
                return {'success': False, 'error': 'Alpaca API not initialized'}
            
            # Validate inputs
            if quantity <= 0:
                return {'success': False, 'error': 'Quantity must be positive'}
            
            # Extended hours eligibility requires DAY limit orders only
            if self.extended_hours:
                order_type = 'limit'
                if limit_price is None:
                    return {'success': False, 'error': 'Extended hours requires limit orders with limit_price'}

            params = dict(
                symbol=symbol,
                qty=quantity,
                side='sell',
                type=order_type,
                time_in_force='day',
                extended_hours=self.extended_hours
            )
            if order_type == 'limit':
                if limit_price is None:
                    return {'success': False, 'error': 'limit_price is required for limit orders'}
                params['limit_price'] = limit_price

            # Place the order
            order = self.api.submit_order(**params)
            
            logger.info(f"Sell order placed: {quantity} shares of {symbol}")
            
            return {
                'success': True,
                'order_id': order.id,
                'symbol': order.symbol,
                'quantity': int(order.qty),
                'side': order.side,
                'type': order.type,
                'status': order.status,
                'submitted_at': order.submitted_at,
                'filled_at': order.filled_at,
                'filled_qty': int(order.filled_qty) if order.filled_qty else 0,
                'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else None
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error placing sell order for {symbol}: {error_msg}")
            return {'success': False, 'error': error_msg}
    
    def get_order(self, order_id: str) -> Optional[Dict]:
        """Get order details by ID"""
        try:
            if self.api is None:
                return None
            
            order = self.api.get_order(order_id)
            
            return {
                'order_id': order.id,
                'symbol': order.symbol,
                'quantity': int(order.qty),
                'side': order.side,
                'type': order.type,
                'status': order.status,
                'submitted_at': order.submitted_at,
                'filled_at': order.filled_at,
                'filled_qty': int(order.filled_qty) if order.filled_qty else 0,
                'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else None,
                'canceled_at': order.canceled_at,
                'expired_at': order.expired_at,
                'replaced_at': order.replaced_at,
                'replaced_by': order.replaced_by,
                'replaces': order.replaces
            }
            
        except Exception as e:
            logger.error(f"Error getting order {order_id}: {e}")
            return None
    
    def get_orders(self, status: str = 'all', limit: int = 100) -> List[Dict]:
        """Get list of orders"""
        try:
            if self.api is None:
                return []
            
            orders = self.api.list_orders(
                status=status,
                limit=limit,
                direction='desc'
            )
            
            order_list = []
            for order in orders:
                order_list.append({
                    'order_id': order.id,
                    'symbol': order.symbol,
                    'quantity': int(order.qty),
                    'side': order.side,
                    'type': order.type,
                    'status': order.status,
                    'submitted_at': order.submitted_at,
                    'filled_at': order.filled_at,
                    'filled_qty': int(order.filled_qty) if order.filled_qty else 0,
                    'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else None
                })
            
            return order_list
            
        except Exception as e:
            logger.error(f"Error getting orders: {e}")
            return []
    
    def cancel_order(self, order_id: str) -> Dict:
        """Cancel an order"""
        try:
            if self.api is None:
                return {'success': False, 'error': 'Alpaca API not initialized'}
            
            self.api.cancel_order(order_id)
            
            logger.info(f"Order {order_id} cancelled")
            return {'success': True}
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error cancelling order {order_id}: {error_msg}")
            return {'success': False, 'error': error_msg}
    
    def get_portfolio_history(self, period: str = '1M', timeframe: str = '1D') -> Optional[Dict]:
        """Get portfolio history"""
        try:
            if self.api is None:
                return None
            
            history = self.api.get_portfolio_history(
                period=period,
                timeframe=timeframe
            )
            
            return {
                'timestamp': history.timestamp,
                'equity': history.equity,
                'profit_loss': history.profit_loss,
                'profit_loss_pct': history.profit_loss_pct,
                'base_value': history.base_value,
                'timeframe': history.timeframe
            }
            
        except Exception as e:
            logger.error(f"Error getting portfolio history: {e}")
            return None
    
    def is_market_open_alpaca(self) -> bool:
        """Check if market is open according to Alpaca"""
        try:
            if self.api is None:
                return False
            
            clock = self.api.get_clock()
            return clock.is_open
            
        except Exception as e:
            logger.error(f"Error checking market status: {e}")
            return False
    
    def get_market_calendar(self, start: str = None, end: str = None) -> List[Dict]:
        """Get market calendar"""
        try:
            if self.api is None:
                return []
            
            calendar = self.api.get_calendar(start=start, end=end)
            
            calendar_list = []
            for day in calendar:
                calendar_list.append({
                    'date': day.date,
                    'open': day.open,
                    'close': day.close
                })
            
            return calendar_list
            
        except Exception as e:
            logger.error(f"Error getting market calendar: {e}")
            return []
