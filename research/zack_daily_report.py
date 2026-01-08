#%%
from datetime import datetime, timezone, timedelta

import pandas as pd
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from research.zack import fetch_data_for_date, parse_json_blob

# Calculate the coming Tuesday through Friday
def get_next_weekdays():
    """Get the dates for the next Tuesday through Friday"""
    today = datetime.now().replace(hour=5, minute=0, second=0, microsecond=0)
    
    # Find next Tuesday (weekday 1)
    days_until_tuesday = (1 - today.weekday()) % 7
    if days_until_tuesday == 0 and today.weekday() == 1:  # If today is Tuesday, get next Tuesday
        days_until_tuesday = 7
    
    next_tuesday = today + timedelta(days=days_until_tuesday)
    
    # Generate Tuesday through Friday
    weekdays = []
    for i in range(4):  # Tuesday, Wednesday, Thursday, Friday
        weekdays.append(next_tuesday + timedelta(days=i))
    
    return weekdays

# Get the target dates
target_dates = get_next_weekdays()
print(f"Fetching data for dates: {[date.strftime('%Y-%m-%d (%A)') for date in target_dates]}")

# Fetch and parse data for each day
daily_dataframes = []
for date in target_dates:
    print(f"Fetching data for {date.strftime('%Y-%m-%d (%A)')}")
    content_str = fetch_data_for_date(date)
    if content_str:
        earnings_df_day = parse_json_blob(content_str)
        if earnings_df_day is not None:
            earnings_df_day['Date'] = date.strftime('%Y-%m-%d')
            
            # Calculate effective trading date
            # For BMO: effective date is previous day
            # For AMC: effective date is same day
            effective_dates = []
            for _, row in earnings_df_day.iterrows():
                if row['AMC/BMO'].lower() == 'bmo':
                    # BMO: previous day
                    effective_date = date - timedelta(days=1)
                else:
                    # AMC: same day
                    effective_date = date
                effective_dates.append(effective_date.strftime('%Y-%m-%d'))
            
            earnings_df_day['Effective Trading Date'] = effective_dates
            
            daily_dataframes.append(earnings_df_day)
            print(f"Successfully fetched {len(earnings_df_day)} records for {date.strftime('%Y-%m-%d')}")
        else:
            print(f"Failed to parse data for {date.strftime('%Y-%m-%d')}")
    else:
        print(f"No data returned for {date.strftime('%Y-%m-%d')}")

# Combine all dataframes
if daily_dataframes:
    earnings_df = pd.concat(daily_dataframes, ignore_index=True)
    print(f"Combined data from {len(daily_dataframes)} days. Total records: {len(earnings_df)}")
else:
    print("Failed to extract data for any day.")
    earnings_df = pd.DataFrame()  # Create empty DataFrame to prevent errors

# Define dates as strings for comparison
dates_str = [date.strftime('%Y-%m-%d') for date in target_dates]

#%%
# Apply the filtering conditions
# Filter for earnings with non-zero EPS percentage and appropriate timing:
# - Tuesday AMC (After Market Close)
# - Wednesday BMO (Before Market Open) 
# - Thursday AMC (After Market Close)
# - Friday BMO (Before Market Open)
if not earnings_df.empty:
    today_action_df = earnings_df[
        (earnings_df['EPS Percentage'] != 0.0) &
        (((earnings_df['Date'] == dates_str[0]) & (earnings_df['AMC/BMO'].str.lower() == 'amc')) |  # Tuesday AMC
         ((earnings_df['Date'] == dates_str[1]) & (earnings_df['AMC/BMO'].str.lower() == 'bmo')) |  # Wednesday BMO
         ((earnings_df['Date'] == dates_str[2]) & (earnings_df['AMC/BMO'].str.lower() == 'amc')) |  # Thursday AMC
         ((earnings_df['Date'] == dates_str[3]) & (earnings_df['AMC/BMO'].str.lower() == 'bmo')))   # Friday BMO
    ]
else:
    today_action_df = pd.DataFrame()  # Create empty DataFrame if no data

# Save today_action_df to CSV in the specified path
# Create directory if it doesn't exist
output_path = os.getenv("ZACK_REPORTS_DIR", "/Users/benny/Documents/zack-reports")
os.makedirs(output_path, exist_ok=True)

# Generate filename with timestamp
current_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
csv_filename = f"zack_report_{current_timestamp}.csv"
csv_filepath = os.path.join(output_path, csv_filename)

# Save DataFrame to CSV
today_action_df.to_csv(csv_filepath, index=False)
print(f"Saved report to: {csv_filepath}")
