import json
import os
from typing import Dict, Any

basePath = "/Users/benny/git/happy-machine-cache"

EURUSD = "CS.D.EURUSD.TODAY.IP"
USDJPY = "CS.D.USDJPY.TODAY.IP"
GBPUSD = "CS.D.GBPUSD.TODAY.IP"
NZDUSD = "CS.D.NZDUSD.TODAY.IP"
USDCAD = "CS.D.USDCAD.TODAY.IP"
USDCHF = "CS.D.USDCHF.TODAY.IP"
AUDUSD = "CS.D.AUDUSD.TODAY.IP"
AUDNZD = "CS.D.AUDNZD.TODAY.IP"
DOLLAR = "CC.D.DX.USS.IP"

CURRENCIES = [EURUSD, USDJPY, GBPUSD, NZDUSD, USDCAD, USDCHF, AUDUSD, AUDNZD, DOLLAR]

DOW = "IX.D.DOW.DAILY.IP"
DAX = "IX.D.DAX.DAILY.IP"
SPTRD = "IX.D.SPTRD.DAILY.IP"
HASE = "IX.D.HANGSENG.DAILY.IP"
NIKKEI = "IX.D.NIKKEI.DAILY.IP"
FTSE = "IX.D.FTSE.DAILY.IP"

INDEXES = [DOW, DAX, SPTRD, HASE, NIKKEI, FTSE]

GOLD = "CS.D.USCGC.TODAY.IP"
GAS = "CC.D.NG.USS.IP"
CRUDE = "CC.D.CL.USS.IP"


def healthy_shares() -> list[str]:
    with open(f'{basePath}/healthy-shares', 'r') as f:
        return json.load(f)


def load_symbols_info() -> dict[str, str]:
    with open(f"{basePath}/dfb-share-list", 'r') as file:
        data = json.load(file)

    epic_to_instrumentname = {}
    for item in data:
        epic = item["epic"]
        instrument_name = item["instrumentName"]
        epic_to_instrumentname[epic] = instrument_name
    return epic_to_instrumentname


def search_symbol(keyword: str) -> list[str]:
    dct = load_symbols_info()
    matching_keys = [key for key, value in dct.items() if keyword in value]
    return matching_keys
