import logging
import threading
from decimal import Decimal
from threading import Condition
from time import sleep
from typing import Dict

from sortedcontainers import SortedDict

from ibapi.client import EClient
from ibapi.common import ListOfPriceIncrements
from ibapi.contract import Contract, ContractDetails
from ibapi.wrapper import EWrapper

logger = logging.getLogger(__name__)


class ResultsWrapper(EWrapper):
    market_rule_condition: Condition = Condition()
    market_rule_id: int = None
    price_increments: Dict[int, SortedDict[Decimal, Decimal]] = {}
    nextOrderId = 1

    def __init__(self):
        super().__init__()
        self.price_increments = {}
        self.market_rule_id = None

    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)
        self.nextOrderId = orderId

    def contractDetails(self, reqId: int, contractDetails: ContractDetails):
        self.market_rule_condition.acquire()
        try:
            exchanges = contractDetails.validExchanges.split(",")
            exchange_idx = exchanges.index("OMXNO")
            self.market_rule_id = int(contractDetails.marketRuleIds.split(",")[exchange_idx])
        except Exception as e:
            print(f"Exception getting Market Rule Id: {e}")
        self.market_rule_condition.notify()
        self.market_rule_condition.release()

    def marketRule(self, marketRuleId: int, priceIncrements: ListOfPriceIncrements):
        self.market_rule_condition.acquire()

        self.price_increments[marketRuleId] = SortedDict(
            {Decimal(str(price_increment.lowEdge)): Decimal(str(price_increment.increment)) for price_increment in
             priceIncrements}
        )

        self.market_rule_condition.notify()
        self.market_rule_condition.release()
        logger.info("priceIncrements: " + str(self.price_increments[marketRuleId]))


def start():
    wrapper = ResultsWrapper()
    client = EClient(wrapper)
    client.connect("localhost", 7496, 5)
    sleep(1)

    handle_responses_thred = threading.Thread(target=lambda: client.run())
    handle_responses_thred.start()

    contract = stock_contract()

    client.reqContractDetails(wrapper.nextOrderId, contract)
    wrapper.market_rule_condition.acquire()
    wrapper.market_rule_condition.wait()

    client.reqMarketRule(wrapper.market_rule_id)
    wrapper.market_rule_condition.acquire()
    wrapper.market_rule_condition.wait()


def stock_contract():
    contract = Contract()
    contract.symbol = "NOD"
    contract.secType = "STK"
    contract.currency = "NOK"
    contract.exchange = "OMXNO"
    return contract


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logging.getLogger('ibapi.utils').setLevel(logging.INFO)
    logging.getLogger('ibapi.client').setLevel(logging.INFO)
    logging.getLogger('ibapi.decoder').setLevel(logging.INFO)

    start()
