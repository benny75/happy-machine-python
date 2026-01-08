import csv
import os
from datetime import datetime, timedelta
import glob

def process_earnings_files():
    csv_dir = 'csv'
    output_dir = '/Users/benny/Documents/zack-reports'
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename with current date
    current_date = datetime.now().strftime('%Y%m%d')
    output_filename = f'combined_earnings_{current_date}.csv'
    output_file = os.path.join(output_dir, output_filename)
    
    all_data = []
    headers = None
    
    for csv_file in glob.glob(os.path.join(csv_dir, '*.csv')):
        if os.path.basename(csv_file) == 'combined_earnings.csv':
            continue
            
        filename = os.path.basename(csv_file)
        date_str = filename.replace('.csv', '')
        
        try:
            earnings_date = datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            print(f"Skipping file {filename} - invalid date format")
            continue
        
        try:
            with open(csv_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                
                if headers is None:
                    headers = reader.fieldnames + ['date', 'trading_date']
                
                for row in reader:
                    # Clean market cap and convert to numeric for filtering
                    market_cap_str = row.get('Market Cap(M)', '').replace(',', '').replace('"', '')
                    try:
                        market_cap = float(market_cap_str) if market_cap_str and market_cap_str != 'NA' else 0
                    except ValueError:
                        market_cap = 0
                    
                    # Clean ESP and check if it's not 0
                    esp_str = row.get('ESP', '').replace('%', '')
                    try:
                        esp = float(esp_str) if esp_str and esp_str != '--' else 0
                    except ValueError:
                        esp = 0
                    
                    # Apply filters: market cap >= 10000 and ESP != 0
                    if market_cap >= 10000 and esp != 0:
                        row['date'] = earnings_date.strftime('%Y-%m-%d')
                        
                        # Remove commas from market cap in output
                        row['Market Cap(M)'] = str(int(market_cap)) if market_cap == int(market_cap) else str(market_cap)
                        
                        time_value = row.get('Time', '').lower()
                        if time_value == 'bmo':
                            trading_date = earnings_date - timedelta(days=1)
                        else:
                            trading_date = earnings_date
                        
                        row['trading_date'] = trading_date.strftime('%Y-%m-%d')
                        
                        # Store numeric values for sorting
                        row['_market_cap_num'] = market_cap
                        row['_esp_abs'] = abs(esp)
                        
                        all_data.append(row)
            
        except Exception as e:
            print(f"Error processing {filename}: {e}")
    
    if all_data:
        # Sort by trading_date, then abs(ESP%) asc, then market cap desc
        all_data.sort(key=lambda x: (x['trading_date'], x['_esp_abs'], -x['_market_cap_num']))
        
        # Remove temporary sorting columns before writing
        for row in all_data:
            row.pop('_market_cap_num', None)
            row.pop('_esp_abs', None)
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(all_data)
        
        print(f"Combined data saved to {output_file}")
        print(f"Total records: {len(all_data)}")
    else:
        print("No valid CSV files found to process")

if __name__ == "__main__":
    process_earnings_files()