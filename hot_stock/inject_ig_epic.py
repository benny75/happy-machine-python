import logging
import time

import pandas as pd
from trading_ig import IGService, IGStreamService


logging.basicConfig(level=logging.INFO)
ig_service = IGService(
    'bennywong75',
    'noum4WEEC*klut',
    '5a7543c7f7a5a148c1620078c116f31c8ea2249e',
    'live',
    acc_number='WYP20',
)
ig = IGStreamService(ig_service)
ig.create_session(version="3")


def get_epic(keyword) -> str:
    try:
        response = ig_service.search_markets(keyword)
        time.sleep(3)  # Be mindful of rate limiting or API call quotas
        epic = response[response['expiry'] == 'DFB']['epic'].iloc[0]
        logging.info(f'Got epic for {keyword}: {epic}')
        return epic
    except Exception as e:
        logging.error(f'Error getting epic for {keyword}: {e}')
        return ""  # Return empty string if there's an exception


df = pd.read_csv('hot_stock.csv')
df['ig_epic'] = df['name'].apply(get_epic)
df.to_csv('hot_stock.csv', index=False, encoding='utf-8')
