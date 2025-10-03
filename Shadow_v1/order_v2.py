import json
from typing import Any, Dict, List
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

    def run(self, state: TradingState) -> tuple[Dict[str, List[Order]], int, str]:
        """
        Only method required. It takes all buy and sell orders for all symbols as an input,
        and outputs a list of orders to be sent
        """
        # Initialize the method output dict as an empty dict
        result = {}
        if state.traderData:
            trader_data = json.loads(state.traderData)
        else:
            trader_data = {"KELP": [2025] * 100, "RAINFOREST_RESIN": [10_000] * 100}

        MAX = 50

        for product in state.order_depths.keys():
                # Retrieve the Order Depth containing all the market BUY and SELL orders
                order_depth: OrderDepth = state.order_depths[product]

                # Initialize the list of Orders to be sent as an empty list
                orders: list[Order] = []

                if product not in state.position:
                    pos = 0
                else:
                    pos = state.position[product]

                buy_success = 0
                sell_success = 0
                if product in state.own_trades:
                    for trade in state.own_trades[product]:
                        if trade.buyer == "SUBMISSION":
                            buy_success += trade.quantity
                        elif trade.seller == "SUBMISSION":
                            sell_success += trade.quantity
                        else:
                            logger.print("ERRORR WHAAAAAAAAAAAAATTTTT")

                success_cutoff = 10

                profiters = {"KELP": 0.75, "RAINFOREST_RESIN": 0.75}
                profiter = profiters[product]

                best_bid = max(state.order_depths[product].buy_orders.keys())
                best_ask = min(state.order_depths[product].sell_orders.keys())
                mid_price = (best_bid + best_ask) / 2

                midder_price = sum(trader_data[product]) / len(trader_data[product])

                logger.print("MID", midder_price)

                bid = best_bid * profiter + mid_price * (1 - profiter)
                vol = MAX - pos

                bid = round(min(bid, midder_price))
                logger.print("BUY", str(vol) + "x", bid)
                orders.append(Order(product, bid, vol))


                ask = best_ask * profiter + mid_price * (1 - profiter)
                vol = -MAX - pos

                ask = round(max(ask, midder_price))
                logger.print("SELL", str(vol) + "x", ask)
                orders.append(Order(product, ask, vol))

                trader_data[product].pop(0)
                trader_data[product].append(mid_price)

                # Add all the above the orders to the result dict
                result[product] = orders


        traderData = json.dumps(trader_data)  # String value holding Trader state data required. It will be delivered as TradingState.traderData on next execution.

        conversions = 0

        # Return the dict of orders
        # These possibly contain buy or sell orders
        # Depending on the logic above

        logger.flush(state, result, conversions, traderData)
        return result, conversions, traderData
