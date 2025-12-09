"""
Smart Trade Executor

Intelligent trade execution with:
- Pre-execution slippage analysis
- Capital tier-based strategy selection
- Sliced order execution
- Execution quality monitoring
"""

import asyncio
import logging
import random
from datetime import datetime
from typing import Dict, Any, List, Optional, Literal
import json

try:
    import httpx
except ImportError:
    httpx = None

from app.core.trading.execution_config import (
    ExecutionConfig, ExecutionPlan, ExecutionResult, CapitalTier,
    get_execution_config
)

logger = logging.getLogger(__name__)


class SlippageAnalyzer:
    """
    Analyze orderbook to estimate slippage for a given order size.
    """
    
    async def _get_orderbook(self, symbol: str = "BTC", limit: int = 100) -> Optional[Dict]:
        """Get orderbook from Binance or fallback exchanges"""
        if not httpx:
            logger.warning("httpx not installed, skipping orderbook fetch")
            return None
            
        # Normalize symbol
        symbol = symbol.upper().replace('-USDT', '').replace('/USDT', '').replace('USDT', '')
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    "https://api.binance.com/api/v3/depth",
                    params={"symbol": f"{symbol}USDT", "limit": limit}
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.warning(f"Orderbook fetch failed: {e}")
        
        return None
    
    async def analyze_slippage(
        self,
        amount_usdt: float,
        direction: Literal["long", "short"],
        symbol: str = "BTC"
    ) -> Dict[str, Any]:
        """
        Analyze expected slippage for a given order.
        
        Args:
            amount_usdt: Order size in USDT
            direction: "long" (buy) or "short" (sell)
            symbol: Trading symbol
            
        Returns:
            Slippage analysis with estimated cost and liquidity rating
        """
        orderbook = await self._get_orderbook(symbol, limit=100)
        
        if not orderbook:
            # Return conservative estimate when orderbook unavailable
            return {
                "estimated_slippage_percent": 0.1,
                "liquidity_rating": "unknown",
                "can_execute_one_shot": amount_usdt < 5000,
                "warning": "Orderbook data unavailable, using conservative estimate",
                "orderbook_available": False
            }
        
        # Parse orderbook: for long (buy), we look at asks; for short (sell), we look at bids
        if direction == "long":
            orders = [[float(p), float(q)] for p, q in orderbook.get("asks", [])[:50]]
        else:
            orders = [[float(p), float(q)] for p, q in orderbook.get("bids", [])[:50]]
        
        if not orders:
            return {
                "estimated_slippage_percent": 0.2,
                "liquidity_rating": "low",
                "can_execute_one_shot": False,
                "warning": "Orderbook empty",
                "orderbook_available": False
            }
        
        # Calculate how many price levels we need to fill the order
        best_price = orders[0][0]
        remaining_usdt = amount_usdt
        filled_usdt = 0
        weighted_price = 0
        levels_used = 0
        
        for price, quantity in orders:
            level_usdt = price * quantity
            if remaining_usdt <= 0:
                break
                
            fill_amount = min(remaining_usdt, level_usdt)
            fill_quantity = fill_amount / price
            
            weighted_price += price * fill_quantity
            filled_usdt += fill_amount
            remaining_usdt -= fill_amount
            levels_used += 1
        
        if filled_usdt == 0:
            return {
                "estimated_slippage_percent": 1.0,
                "liquidity_rating": "very_low",
                "can_execute_one_shot": False,
                "warning": "Insufficient liquidity",
                "orderbook_available": True
            }
        
        # Calculate average execution price and slippage
        avg_price = weighted_price / (amount_usdt / best_price) if best_price > 0 else best_price
        slippage_percent = abs((avg_price - best_price) / best_price * 100) if best_price > 0 else 0
        
        # Calculate total available liquidity in top 50 levels
        total_liquidity_usdt = sum(p * q for p, q in orders)
        
        # Determine liquidity rating
        if slippage_percent < 0.1 and levels_used <= 3:
            liquidity_rating = "high"
        elif slippage_percent < 0.3 and levels_used <= 10:
            liquidity_rating = "medium"
        else:
            liquidity_rating = "low"
        
        # Determine if one-shot is advisable
        config = get_execution_config()
        can_one_shot = (
            slippage_percent <= config.max_slippage_percent and
            amount_usdt <= total_liquidity_usdt * 0.1  # Order is <10% of visible liquidity
        )
        
        return {
            "estimated_slippage_percent": round(slippage_percent, 4),
            "avg_execution_price": round(avg_price, 2),
            "best_price": round(best_price, 2),
            "levels_used": levels_used,
            "total_liquidity_usdt": round(total_liquidity_usdt, 2),
            "liquidity_rating": liquidity_rating,
            "can_execute_one_shot": can_one_shot,
            "orderbook_available": True,
            "recommendation": (
                "Direct execution recommended" if can_one_shot else
                "Consider sliced execution to reduce slippage"
            )
        }


class SlicedExecutor:
    """
    Execute large orders in slices to minimize market impact.
    """
    
    def __init__(self, paper_trader=None):
        self.paper_trader = paper_trader
        self.config = get_execution_config()
        self.slippage_analyzer = SlippageAnalyzer()
    
    def generate_slice_amounts(
        self,
        total_amount: float,
        slice_count: int,
        variance_percent: float = 10.0
    ) -> List[float]:
        """
        Generate slice amounts with random variance.
        
        Args:
            total_amount: Total USDT to allocate
            slice_count: Number of slices
            variance_percent: Variance as percentage (±%)
            
        Returns:
            List of slice amounts that sum to total_amount
        """
        base_amount = total_amount / slice_count
        slices = []
        
        for i in range(slice_count - 1):
            variance = random.uniform(-variance_percent/100, variance_percent/100)
            slice_amount = base_amount * (1 + variance)
            slices.append(slice_amount)
        
        # Last slice gets the remainder to ensure exact total
        slices.append(total_amount - sum(slices))
        
        # Shuffle to avoid predictable pattern
        random.shuffle(slices)
        
        return slices
    
    async def create_execution_plan(
        self,
        amount_usdt: float,
        direction: Literal["long", "short"],
        leverage: int = 1,
        tp_percent: float = 5.0,
        sl_percent: float = 2.0,
        symbol: str = "BTC"
    ) -> ExecutionPlan:
        """
        Create an execution plan based on order size and market conditions.
        
        Args:
            amount_usdt: Total USDT to trade
            direction: Trade direction
            leverage: Leverage multiplier
            tp_percent: Take profit percentage
            sl_percent: Stop loss percentage
            symbol: Trading symbol
            
        Returns:
            ExecutionPlan with strategy and parameters
        """
        # Analyze slippage
        slippage = await self.slippage_analyzer.analyze_slippage(
            amount_usdt, direction, symbol
        )
        
        # Determine strategy based on capital tier
        tier = self.config.get_capital_tier(amount_usdt)
        strategy = self.config.get_recommended_strategy(amount_usdt)
        slice_count = self.config.get_recommended_slices(amount_usdt)
        
        # Adjust based on slippage analysis
        if slippage.get("orderbook_available"):
            if slippage["estimated_slippage_percent"] > self.config.max_slippage_percent:
                # High slippage detected - force sliced execution
                if strategy == "direct":
                    strategy = "sliced"
                    slice_count = max(3, slice_count)
                    logger.warning(
                        f"[SmartExecutor] High slippage detected ({slippage['estimated_slippage_percent']:.2f}%), "
                        f"switching to sliced execution"
                    )
        
        # Generate slice amounts
        slice_amounts = []
        if slice_count > 1:
            slice_amounts = self.generate_slice_amounts(
                amount_usdt, slice_count, self.config.slice_variance_percent
            )
        else:
            slice_amounts = [amount_usdt]
        
        # Determine execution risk
        if slippage["estimated_slippage_percent"] > 0.5:
            execution_risk = "high"
        elif slippage["estimated_slippage_percent"] > 0.2:
            execution_risk = "medium"
        else:
            execution_risk = "low"
        
        plan = ExecutionPlan(
            strategy=strategy,
            direction=direction,
            total_amount_usdt=amount_usdt,
            slice_count=slice_count,
            slice_interval_seconds=self.config.slice_interval_seconds,
            slice_amounts=slice_amounts,
            max_slippage_percent=self.config.max_slippage_percent,
            abort_on_volatility=self.config.abort_on_volatility,
            leverage=leverage,
            tp_percent=tp_percent,
            sl_percent=sl_percent,
            estimated_slippage_percent=slippage["estimated_slippage_percent"],
            liquidity_rating=slippage.get("liquidity_rating", "unknown"),
            execution_risk=execution_risk
        )
        
        logger.info(
            f"[SmartExecutor] Created plan: {strategy} with {slice_count} slices, "
            f"estimated slippage {slippage['estimated_slippage_percent']:.2f}%"
        )
        
        return plan
    
    async def execute_plan(self, plan: ExecutionPlan) -> ExecutionResult:
        """
        Execute a trading plan.
        
        Args:
            plan: ExecutionPlan with all parameters
            
        Returns:
            ExecutionResult with execution metrics
        """
        result = ExecutionResult(
            plan=plan,
            status="completed",
            execution_start_time=datetime.now().isoformat()
        )
        
        slice_results = []
        total_filled = 0
        total_cost = 0
        
        try:
            for i, slice_amount in enumerate(plan.slice_amounts):
                # Execute single slice
                logger.info(
                    f"[SmartExecutor] Executing slice {i+1}/{plan.slice_count}: "
                    f"${slice_amount:,.2f} {plan.direction}"
                )
                
                slice_result = await self._execute_single_slice(
                    amount_usdt=slice_amount,
                    direction=plan.direction,
                    leverage=plan.leverage,
                    tp_percent=plan.tp_percent if i == len(plan.slice_amounts) - 1 else None,
                    sl_percent=plan.sl_percent if i == len(plan.slice_amounts) - 1 else None,
                    is_final_slice=(i == len(plan.slice_amounts) - 1)
                )
                
                slice_results.append(slice_result)
                
                if slice_result.get("success"):
                    total_filled += slice_result.get("filled_amount", slice_amount)
                    total_cost += slice_result.get("filled_amount", slice_amount) * slice_result.get("price", 0)
                    result.executed_slices += 1
                else:
                    logger.warning(f"[SmartExecutor] Slice {i+1} failed: {slice_result.get('error')}")
                    if not slice_result.get("retry_allowed", True):
                        result.status = "partial"
                        result.error_message = slice_result.get("error")
                        break
                
                # Wait between slices (except for last one)
                if i < len(plan.slice_amounts) - 1:
                    logger.info(f"[SmartExecutor] Waiting {plan.slice_interval_seconds}s before next slice")
                    await asyncio.sleep(plan.slice_interval_seconds)
                    
                    # Check for volatility spike before continuing
                    if plan.abort_on_volatility:
                        # TODO: Implement volatility check
                        pass
            
            # Calculate final metrics
            result.total_filled_usdt = total_filled
            if total_filled > 0 and total_cost > 0:
                result.average_entry_price = total_cost / (total_filled / slice_results[-1].get("price", 1))
            
            result.slice_results = slice_results
            result.execution_end_time = datetime.now().isoformat()
            
            # Calculate total slippage
            if slice_results and slice_results[0].get("price"):
                initial_price = slice_results[0]["price"]
                if result.average_entry_price:
                    result.total_slippage_percent = abs(
                        (result.average_entry_price - initial_price) / initial_price * 100
                    )
            
            logger.info(
                f"[SmartExecutor] Execution complete: {result.executed_slices}/{plan.slice_count} slices, "
                f"${result.total_filled_usdt:,.2f} filled, "
                f"slippage {result.total_slippage_percent:.2f}%"
            )
            
        except Exception as e:
            logger.error(f"[SmartExecutor] Execution error: {e}")
            result.status = "failed"
            result.error_message = str(e)
        
        return result
    
    async def _execute_single_slice(
        self,
        amount_usdt: float,
        direction: Literal["long", "short"],
        leverage: int,
        tp_percent: Optional[float] = None,
        sl_percent: Optional[float] = None,
        is_final_slice: bool = False
    ) -> Dict[str, Any]:
        """Execute a single slice order via paper trader"""
        
        if not self.paper_trader:
            # Dry run mode - simulate execution
            logger.info(f"[SmartExecutor] Dry run: {direction} ${amount_usdt:.2f}")
            return {
                "success": True,
                "filled_amount": amount_usdt,
                "price": 98000,  # Simulated price
                "slippage": 0.0,
                "dry_run": True
            }
        
        try:
            # Get current price for slippage calculation
            from app.core.trading.price_service import get_current_btc_price
            current_price = await get_current_btc_price()
            
            # Calculate TP/SL prices only for final slice
            tp_price = None
            sl_price = None
            if is_final_slice and tp_percent and sl_percent:
                if direction == "long":
                    tp_price = current_price * (1 + tp_percent / 100)
                    sl_price = current_price * (1 - sl_percent / 100)
                else:
                    tp_price = current_price * (1 - tp_percent / 100)
                    sl_price = current_price * (1 + sl_percent / 100)
            
            # Execute via paper trader
            if direction == "long":
                result = await self.paper_trader.open_long(
                    leverage=leverage,
                    amount_usdt=amount_usdt,
                    tp_price=tp_price,
                    sl_price=sl_price
                )
            else:
                result = await self.paper_trader.open_short(
                    leverage=leverage,
                    amount_usdt=amount_usdt,
                    tp_price=tp_price,
                    sl_price=sl_price
                )
            
            executed_price = result.get("executed_price", current_price)
            slippage = abs((executed_price - current_price) / current_price * 100)
            
            return {
                "success": result.get("success", False),
                "filled_amount": amount_usdt if result.get("success") else 0,
                "price": executed_price,
                "slippage": slippage,
                "order_id": result.get("order_id"),
                "error": result.get("error")
            }
            
        except Exception as e:
            logger.error(f"[SmartExecutor] Slice execution error: {e}")
            return {
                "success": False,
                "error": str(e),
                "retry_allowed": True
            }


# Convenience function for quick execution analysis
async def analyze_execution(
    amount_usdt: float,
    direction: Literal["long", "short"],
    symbol: str = "BTC"
) -> Dict[str, Any]:
    """
    Quick analysis of execution conditions.
    
    Returns a summary suitable for TradeExecutor decision making.
    """
    config = get_execution_config()
    analyzer = SlippageAnalyzer()
    
    # Get capital tier
    tier = config.get_capital_tier(amount_usdt)
    strategy = config.get_recommended_strategy(amount_usdt)
    slices = config.get_recommended_slices(amount_usdt)
    
    # Analyze slippage
    slippage = await analyzer.analyze_slippage(amount_usdt, direction, symbol)
    
    return {
        "amount_usdt": amount_usdt,
        "direction": direction,
        "capital_tier": tier.value,
        "recommended_strategy": strategy,
        "recommended_slices": slices,
        "estimated_slippage_percent": slippage["estimated_slippage_percent"],
        "liquidity_rating": slippage.get("liquidity_rating", "unknown"),
        "can_execute_one_shot": slippage.get("can_execute_one_shot", False),
        "slice_interval_seconds": config.slice_interval_seconds,
        "max_slippage_threshold": config.max_slippage_percent,
        "recommendation": (
            f"Use {strategy} execution with {slices} slice(s). "
            f"Estimated slippage: {slippage['estimated_slippage_percent']:.2f}%. "
            f"Liquidity: {slippage.get('liquidity_rating', 'unknown')}."
        )
    }
