from data.TimescaleDBSticksDao import get_sticks
import pandas as pd

# Get daily candles for SPY
df = get_sticks("SI.D.SPY.DAILY.IP", 1440)

# Calculate mid prices
df['mid_open'] = (df['bid_open'] + df['ask_open']) / 2
df['mid_close'] = (df['bid_close'] + df['ask_close']) / 2

# Calculate daily return percentage
df['daily_return_pct'] = (df['mid_close'] - df['mid_open']) / df['mid_open'] * 100

# Calculate absolute daily return
df['abs_daily_return_pct'] = df['daily_return_pct'].abs()

# Calculate probability of moving less than 2%
total_days = len(df)
days_less_than_1pct = len(df[df['abs_daily_return_pct'] < 1])
probability = days_less_than_1pct / total_days * 100

print(f"Total trading days: {total_days}")
print(f"Days with <1% move: {days_less_than_1pct}")
print(f"Probability of <1% move: {probability:.2f}%")

# Optional: Show some statistics
print("\nAdditional Statistics:")
print(f"Average absolute daily move: {df['abs_daily_return_pct'].mean():.2f}%")
print(f"Median absolute daily move: {df['abs_daily_return_pct'].median():.2f}%")
print(f"Max daily move: {df['abs_daily_return_pct'].max():.2f}%")
print(f"Min daily move: {df['abs_daily_return_pct'].min():.2f}%")

# Analysis for days following a significant close-to-close move
print("\nAnalysis of days following significant close-to-close moves:")
# Create column for previous day close-to-close change
df['prev_close_to_close_pct'] = df['mid_close'].pct_change() * 100
df['abs_prev_close_to_close_pct'] = df['prev_close_to_close_pct'].abs()

# Shift to get T-2 to T-1 close change (i.e., previous day's close-to-close)
df['t_minus_2_to_t_minus_1_change'] = df['abs_prev_close_to_close_pct'].shift(1)

# Filter days where T-2 to T-1 had >1% move
significant_prior_move = df[df['t_minus_2_to_t_minus_1_change'] > 1].dropna()
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
small_prior_move = df[df['t_minus_2_to_t_minus_1_change'] < 1].dropna()
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