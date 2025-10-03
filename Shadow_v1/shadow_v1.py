import json
from typing import Any
from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState

class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state: TradingState, orders: dict[Symbol, list[Order]], conversions: int, trader_data: str) -> None:
        base_length = len(
            self.to_json(
                [
                    self.compress_state(state, ""),
                    self.compress_orders(orders),
                    conversions,
                    "",
                    "",
                ]
            )
        )

        # We truncate state.traderData, trader_data, and self.logs to the same max. length to fit the log limit
        max_item_length = (self.max_log_length - base_length) // 3

        print(
            self.to_json(
                [
                    self.compress_state(state, self.truncate(state.traderData, max_item_length)),
                    self.compress_orders(orders),
                    conversions,
                    self.truncate(trader_data, max_item_length),
                    self.truncate(self.logs, max_item_length),
                ]
            )
        )

        self.logs = ""

    def compress_state(self, state: TradingState, trader_data: str) -> list[Any]:
        return [
            state.timestamp,
            trader_data,
            self.compress_listings(state.listings),
            self.compress_order_depths(state.order_depths),
            self.compress_trades(state.own_trades),
            self.compress_trades(state.market_trades),
            state.position,
            self.compress_observations(state.observations),
        ]

    def compress_listings(self, listings: dict[Symbol, Listing]) -> list[list[Any]]:
        compressed = []
        for listing in listings.values():
            compressed.append([listing.symbol, listing.product, listing.denomination])

        return compressed

    def compress_order_depths(self, order_depths: dict[Symbol, OrderDepth]) -> dict[Symbol, list[Any]]:
        compressed = {}
        for symbol, order_depth in order_depths.items():
            compressed[symbol] = [order_depth.buy_orders, order_depth.sell_orders]

        return compressed

    def compress_trades(self, trades: dict[Symbol, list[Trade]]) -> list[list[Any]]:
        compressed = []
        for arr in trades.values():
            for trade in arr:
                compressed.append(
                    [
                        trade.symbol,
                        trade.price,
                        trade.quantity,
                        trade.buyer,
                        trade.seller,
                        trade.timestamp,
                    ]
                )

        return compressed

    def compress_observations(self, observations: Observation) -> list[Any]:
        conversion_observations = {}
        for product, observation in observations.conversionObservations.items():
            conversion_observations[product] = [
                observation.bidPrice,
                observation.askPrice,
                observation.transportFees,
                observation.exportTariff,
                observation.importTariff,
                observation.sugarPrice,
                observation.sunlightIndex,
            ]

        return [observations.plainValueObservations, conversion_observations]

    def compress_orders(self, orders: dict[Symbol, list[Order]]) -> list[list[Any]]:
        compressed = []
        for arr in orders.values():
            for order in arr:
                compressed.append([order.symbol, order.price, order.quantity])

        return compressed

    def to_json(self, value: Any) -> str:
        return json.dumps(value, cls=ProsperityEncoder, separators=(",", ":"))

    def truncate(self, value: str, max_length: int) -> str:
        if len(value) <= max_length:
            return value

        return value[: max_length - 3] + "..."


logger = Logger()


class Trader:

    def run(self, state: TradingState) -> tuple[dict[Symbol, list[Order]], int, str]:
        result = {}
        conversion = 0
        trader_data = ""
        """
        Only method required. It takes all buy and sell orders for all symbols as an input,
        and outputs a list of orders to be sent
        """
        # Initialize the method output dict as an empty dict
        result = {}

        # Iterate over all the keys (the available products) contained in the order dephts
        for product in state.order_depths.keys():

                # Retrieve the Order Depth containing all the market BUY and SELL orders
                order_depth: OrderDepth = state.order_depths[product]

                # Initialize the list of Orders to be sent as an empty list
                orders: list[Order] = []

                # Get position data
                if product in state.position.keys():
                    position = state.position[product]
                else:
                    position = 0
                logger.print(position)

                # In this algo we only provide quotes
                best_ask = min(order_depth.sell_orders.keys())
                best_bid = max(order_depth.buy_orders.keys())
                if product == "KELP":
                    continue
                    mid_price = (best_ask + best_bid)/2
                    if product not in state.market_trades:
                        ask = best_ask
                        bid = best_bid
                    elif state.market_trades[product] == []:
                        ask = best_ask 
                        bid = best_bid
                    elif state.market_trades[product][0].quantity > 6 and mid_price > 2019:
                        ask = best_bid
                        bid = best_bid*2
                    elif state.market_trades[product][0].quantity > 6 and mid_price < 2019:
                        bid = best_ask
                        ask = 0
                    else:
                        ask = best_ask 
                        bid = best_bid
                else:
                    if best_bid > 10000:
                        ask = best_bid
                        bid = 0
                    elif best_ask < 10000:
                        bid = best_ask
                        ask = best_ask*2
                    else:
                        bid = best_bid + 1
                        ask = best_ask - 1
                spread_constant = 30
                alpha = 1.5  
                bid_volume = int(max(spread_constant - alpha*position, 0))
                ask_volume = int(min(-spread_constant - alpha*position, 0))

                logger.print(state.market_trades)
                logger.print("BUY", str(bid_volume) + "x", bid)
                orders.append(Order(product, bid, bid_volume))
                logger.print("SELL", str(ask_volume) + "x", ask)
                orders.append(Order(product, ask, ask_volume))
                
                # Add all the above the orders to the result dict
                result[product] = orders
                
        traderData = "SAMPLE" # String value holding Trader state data required. It will be delivered as TradingState.traderData on next execution.
        
        conversions = 1 

                # Return the dict of orders
                # These possibly contain buy or sell orders
                # Depending on the logic above
        

        logger.flush(state, result, conversions, trader_data)

        return result, conversions, traderData
