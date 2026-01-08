from data.TimescaleDBSticksDao import get_sticks
import pandas as pd
import pytz

# Get hourly candles for SPY
df = get_sticks("SI.D.SPY.DAILY.IP", 60)

# Convert timestamp to datetime and set timezone
df.index = pd.to_datetime(df.index, unit='ms')
est = pytz.timezone('America/New_York')
df.index = df.index.tz_convert(est)

# Filter for 10 AM EST candles
df_10am = df[df.index.hour == 10].copy()

# Create a 'date' column from the index
df_10am['date'] = df_10am.index.date

# Ensure each day has only one 10 AM candle (take the first if multiple exist for some reason)
df_10am = df_10am.groupby('date').first().reset_index()

# Calculate mid prices for 10 AM open
df_10am['mid_open_10am'] = (df_10am['bid_open'] + df_10am['ask_open']) / 2

# Get daily close for each day from the last hourly candle of the day
df['date'] = df.index.date
df_daily_close = df.groupby('date').last().reset_index()
df_daily_close['mid_close'] = (df_daily_close['bid_close'] + df_daily_close['ask_close']) / 2

# Merge 10 AM open with daily close
df_final = pd.merge(df_10am[['date', 'mid_open_10am']], df_daily_close[['date', 'mid_close']], on='date', how='inner')

# Calculate daily return percentage using 10 AM open
df_final['daily_return_pct'] = (df_final['mid_close'] - df_final['mid_open_10am']) / df_final['mid_open_10am'] * 100

# Calculate absolute daily return
df_final['abs_daily_return_pct'] = df_final['daily_return_pct'].abs()

# Calculate probability of moving less than 2%
total_days = len(df_final)
days_less_than_1pct = len(df_final[df_final['abs_daily_return_pct'] < 1])
probability = days_less_than_1pct / total_days * 100

print(f"Total trading days: {total_days}")
print(f"Days with <1% move: {days_less_than_1pct}")
print(f"Probability of <1% move: {probability:.2f}%")

# Optional: Show some statistics
print("\nAdditional Statistics:")
print(f"Average absolute daily move: {df_final['abs_daily_return_pct'].mean():.2f}%")
print(f"Median absolute daily move: {df_final['abs_daily_return_pct'].median():.2f}%")
print(f"Max daily move: {df_final['abs_daily_return_pct'].max():.2f}%")
print(f"Min daily move: {df_final['abs_daily_return_pct'].min():.2f}%")

# Analysis for days following a significant close-to-close move
print("\nAnalysis of days following significant close-to-close moves:")
# Create column for previous day close-to-close change
df_final['prev_close_to_close_pct'] = df_final['mid_close'].pct_change() * 100
df_final['abs_prev_close_to_close_pct'] = df_final['prev_close_to_close_pct'].abs()

# Shift to get T-2 to T-1 close change (i.e., previous day's close-to-close)
df_final['t_minus_2_to_t_minus_1_change'] = df_final['abs_prev_close_to_close_pct'].shift(1)

# Filter days where T-2 to T-1 had >1% move
significant_prior_move = df_final[df_final['t_minus_2_to_t_minus_1_change'] > 1].dropna()
total_significant_prior_days = len(significant_prior_move)

# Calculate probability of <1% move on day T after significant T-2 to T-1 move
days_less_than_1pct_after_significant = len(significant_prior_move[significant_prior_move['abs_daily_return_pct'] < 1])
conditional_probability = days_less_than_1pct_after_significant / total_significant_prior_days * 100 if total_significant_prior_days > 0 else 0

print(f"Total days with >1% T-2 to T-1 close-to-close move: {total_significant_prior_days}")
print(f"Days with <1% open-to-close move following a >1% prior close-to-close move: {days_less_than_1pct_after_significant}")
print(f"Probability of <1% open-to-close move given >1% prior close-to-close move: {conditional_probability:.2f}%")
print(f"Compared to unconditional probability of <1% move: {probability:.2f}%")

# Analysis for days following a small close-to-close move
print("\nAnalysis of days following small close-to-close moves:")
# Filter days where T-2 to T-1 had <1% move
small_prior_move = df_final[df_final['t_minus_2_to_t_minus_1_change'] < 1].dropna()
total_small_prior_days = len(small_prior_move)

# Calculate probability of <1% move on day T after small T-2 to T-1 move
days_less_than_1pct_after_small = len(small_prior_move[small_prior_move['abs_daily_return_pct'] < 1])
conditional_probability_small = days_less_than_1pct_after_small / total_small_prior_days * 100 if total_small_prior_days > 0 else 0

print(f"Total days with <1% T-2 to T-1 close-to-close move: {total_small_prior_days}")
print(f"Days with <1% open-to-close move following a <1% prior close-to-close move: {days_less_than_1pct_after_small}")
print(f"Probability of <1% open-to-close move given <1% prior close-to-close move: {conditional_probability_small:.2f}%")
print(f"Compared to unconditional probability of <1% move: {probability:.2f}%")

# Summary comparison
print("\nComparison Summary:")
print(f"Unconditional probability of <1% daily move: {probability:.2f}%")
print(f"Probability after >1% prior day move: {conditional_probability:.2f}%")
print(f"Probability after <1% prior day move: {conditional_probability_small:.2f}%")
print(f"Difference (large vs small prior move): {conditional_probability - conditional_probability_small:.2f}%")