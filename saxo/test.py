# https://www.developer.saxo/openapi/referencedocs/trade/v1/optionschain/addsubscriptionasync/8ff796d4153fb5ae1dbce9ebf2d48b82
subscribe_option_uri = "https://gateway.saxobank.com/sim/openapi/trade/v1/optionschain/subscriptions"

json_data = """
{
  "Arguments": {
    "AccountKey": "LZTc7DdejXODf-WSl2aCyQ==",
    "AssetType": "StockIndexOption",
    "Expiries": [
      {
        "Index": 1,
        "StrikeStartIndex": 0
      }
    ],
    "Identifier": 18,
    "MaxStrikesPerExpiry": 3
  },
  "ContextId": "20230922015144937",
  "ReferenceId": "C0190668",
  "RefreshRate": 1000
}
"""
data = json.loads(json_data)
data['Arguments']['AccountKey'] = account_key

res = requests.post(url=subscribe_option_uri, headers=headers, data=json.dumps(data))