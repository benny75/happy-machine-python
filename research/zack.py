import json
import re
from datetime import datetime, timezone

import pandas as pd
import pytz
import requests
from bs4 import BeautifulSoup
from pandas import DataFrame


def parse_json_blob(content: str) -> DataFrame:
    try:
        # Removing all line breaks from the content
        content = content.replace('\n', '').replace('\r', '')

        # Finding the start and end of the JSON blob using regular expressions
        pattern = re.compile(r'"data" : \[\s*(.*?)\s*\]\s*}', re.DOTALL)
        match = pattern.search(content)

        if not match:
            raise ValueError("JSON data not found in the file.")

        # Extracting and cleaning the JSON string
        json_str = '{' + match.group()

        # Parsing the JSON string
        data_json = json.loads(json_str)
        data_ = data_json["data"]

        # Processing each item in data_
        processed_data = []
        for item in data_:
            # Extracting symbol
            soup_symbol = BeautifulSoup(item[0], 'html.parser')
            symbol = soup_symbol.find('span', {'class': 'hoverquote-symbol'}).text if soup_symbol.find('span', {'class': 'hoverquote-symbol'}) else 'N/A'

            # Extracting name
            soup_name = BeautifulSoup(item[1], 'html.parser')
            name = soup_name.text.strip()

            # Extracting market cap (remove commas and convert to string for now)
            market_cap = item[2].strip().replace(',', '') if item[2].strip() else 'N/A'

            # Extracting amc/bmo
            amc_bmo = item[3].strip().lower()

            # Extracting EPS percentage and converting to float
            eps_percentage = item[6].strip().replace('%', '')
            try:
                eps_percentage = float(eps_percentage)
            except ValueError:
                eps_percentage = 0.0

            processed_data.append([symbol, name, market_cap, amc_bmo, eps_percentage])

        # Forming a DataFrame
        df = pd.DataFrame(processed_data, columns=['Symbol', 'Name', 'Market Cap', 'AMC/BMO', 'EPS Percentage'])

        return df
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def fetch_data_for_date(date):
    # Set the timezone to GMT -6
    gmt_minus_6 = pytz.timezone('Etc/GMT+6')
    # Ensure the date is at 00:00 in GMT -6
    _date = gmt_minus_6.localize(datetime(date.year, date.month, date.day, 0, 0, 0))
    # Convert localized datetime to UTC
    date_utc = _date.astimezone(timezone.utc)
    # Convert to Unix timestamp
    timestamp = int(date_utc.timestamp())


    _URL = 'https://www.zacks.com/includes/classes/z2_class_calendarfunctions_data.php'
    _ZACKS_HEADER = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    params = {
        'calltype': 'eventscal',
        'date': str(timestamp),
        'type': '1',
        'search_trigger': '0'
    }

    response = requests.get(_URL, headers=_ZACKS_HEADER, params=params)

    if response.status_code == 200:
        return response.text
    else:
        print("Failed to fetch data: Status code", response.status_code)
        return None
