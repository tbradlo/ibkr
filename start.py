import asyncio
import logging
import sys
import threading
from threading import Condition
from decimal import Decimal
from time import sleep
from typing import Dict

from ibapi.client import EClient
from ibapi.common import TickerId, TickAttrib
from ibapi.contract import Contract, ComboLeg, ContractDetails
from ibapi.ticktype import TickType
from ibapi.wrapper import EWrapper

logger = logging.getLogger(__name__)

TICKFIELD_IB2VT: Dict[int, str] = {
    # 0: "bid_volume_1",
    # 1: "bid_price_1",
    # 2: "ask_price_1",
    # 3: "ask_volume_1",
    4: "last_price",
    # 5: "last_volume",
    # 6: "high_price",
    # 7: "low_price",
    # 8: "volume",
    # 9: "pre_close",
    # 14: "open_price",
}

class ResultsWrapper(EWrapper):

    wait_for_ticks: Condition = Condition()
    total_ticks = 0
    nextOrderId = 1

    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)
        self.nextOrderId = orderId

    def managedAccounts(self, accountsList:str):
        super().managedAccounts(accountsList)

    def contractDetails(self, reqId: int, contractDetails: ContractDetails):
        super().contractDetails(reqId, contractDetails)

    def tickPrice(self, reqId: TickerId, tickType: TickType, price: float, attrib: TickAttrib):

        # super().tickPrice(reqId, tickType, price, attrib)
        if tickType in TICKFIELD_IB2VT:
            logger.info("tickPrice: " + str(tickType) + " " + str(price) + " att: " + str(attrib))

            self.total_ticks += 1
            if self.total_ticks > 100:
                self.wait_for_ticks.acquire()
                self.wait_for_ticks.notify()
                self.wait_for_ticks.release()

    def tickSize(self, reqId: TickerId, tickType: TickType, size: Decimal):
        # super().tickSize(reqId, tickType, size)
        # print("tickSize: " + str(tickType) + " att: " + str(size))
        pass

    def tickString(self, reqId: TickerId, tickType: TickType, value: str):
        # super().tickString(reqId, tickType, value)
        # print("tickString: " + str(tickType) + " value: " + value)
        pass


def start():
    wrapper = ResultsWrapper()
    client = EClient(wrapper)
    client.connect("localhost", 7496, 5)
    sleep(1)

    handle_responses_thred = threading.Thread(target=lambda: client.run())
    handle_responses_thred.start()

    contract = spread_contract()
    # contract = euro_stock_contract()

    # client.reqContractDetails(wrapper.nextOrderId, contract)

    # https://interactivebrokers.github.io/tws-api/tick_types.html
    # tickTypes = '4,84,85' # lastPrice + lastExchange + timestamp
    tickTypes = ''

    client.reqMktData(wrapper.nextOrderId + 1, contract, tickTypes, False, False, [])
    # client.reqTickByTickData(wrapper.nextOrderId + 1, contract, "Last", 0, True)
    client.reqHistoricalTicks(wrapper.nextOrderId + 2, contract, "20230701 21:39:33 US/Eastern", "", 0, "TRADES", 1, False, [])

    wrapper.wait_for_ticks.acquire()
    wrapper.wait_for_ticks.wait()

def fx_contract():
    contract = Contract()
    contract.symbol = "USD"
    contract.secType = "CASH"
    contract.currency = "PLN"
    contract.exchange = "IDEALPRO"
    return contract

def euro_stock_contract():
    contract = Contract()
    contract.symbol = "VNA"
    contract.secType = "STK"
    contract.currency = "EUR"
    contract.exchange = "SMART"
    return contract

def spread_contract():
    contract = Contract()
    contract.symbol = "CL"
    contract.secType = "BAG"
    contract.currency = "USD"
    contract.exchange = "NYMEX"
    leg1 = ComboLeg()
    leg1.conId = 296574769  # CL FUT 202308
    leg1.ratio = 1
    leg1.action = "SELL"
    leg1.exchange = "NYMEX"
    leg2 = ComboLeg()
    leg2.conId = 296574772  # CL FUT 202309
    leg2.ratio = 1
    leg2.action = "BUY"
    leg2.exchange = "NYMEX"
    contract.comboLegs = []
    contract.comboLegs.append(leg1)
    contract.comboLegs.append(leg2)
    return contract


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logging.getLogger('ibapi.utils').setLevel(logging.INFO)
    logging.getLogger('ibapi.client').setLevel(logging.INFO)
    logging.getLogger('ibapi.decoder').setLevel(logging.INFO)

    start()
