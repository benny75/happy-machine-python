# TD Sequential Credit Spread Strategy

## 1. Strategy Overview
**Type:** Mean Reversion / Trend Exhaustion  
**Instrument:** Vertical Credit Spreads (Options)  
**Core Logic:** The strategy identifies exhaustion points in a trend using the **TD Sequential 9** signal. Instead of betting on a hard reversal, we sell out-of-the-money (OTM) credit spreads. We rely on the trend stalling or reversing slightly, allowing Theta (time decay) and Delta (directional move) to erode the option premium.

---

## 2. Entry Conditions & Setup

### Signal Trigger
The strategy relies on the **TD Sequential** indicator on the **Daily** timeframe.
*   **Bullish Signal (Buy Setup 9):** 9 consecutive closes lower than the close 4 bars prior.
    *   *Implication:* Downside momentum is exhausted. Expect a bounce or consolidation.
    *   *Action:* **Sell Bull Put Spread**.
*   **Bearish Signal (Sell Setup 9):** 9 consecutive closes higher than the close 4 bars prior.
    *   *Implication:* Upside momentum is exhausted. Expect a pullback or consolidation.
    *   *Action:* **Sell Bear Call Spread**.

### Option Construction
*   **Frequency:** 1-2 positions per day.
*   **Selection:** Pick from the Top 10 most liquid stocks (High Dollar Volume) in the daily report.
*   **Expiration (DTE):** 5 - 10 days. (Short duration captures rapid decay).
*   **Short Strike Delta:** ~0.30 Delta (approx. 70% probability of expiring OTM).
*   **Spread Width:** $5 - $10 (Balances risk/reward and commission efficiency).

---

## 3. Operational Workflow

### A. Research & Validation (Periodical)
To validate the statistical edge of the strategy on current market conditions:
```bash
python3 research/td_sequential_probability.py
```
*   **Goal:** Ensure "Win Rate" (Price holding buffer zone) remains > 75%.
*   **Buffer:** The script uses a 3% buffer by default to simulate OTM cushion.

### B. Daily Scanning (Daily)
To generate the list of potential trade targets for the day:
```bash
python3 reports/td_sequential_report.py
```
*   **Output:** Generates a CSV in `reports/td_sequential_signals_YYYY-MM-DD.csv`.
*   **Key Columns to Read:** `symbol`, `signal_type`, `dollar_volume`, `close_price`.

---

## 4. Risk Management Rules

1.  **Earnings Check:** NEVER open a position if the company reports earnings within the contract's life (5-10 days). Volatility crush and gap risk are too high.
2.  **Sector Diversity:** If taking 2 trades, ensure they are uncorrelated (e.g., do NOT trade NVDA and AMD on the same day).
3.  **Position Sizing:** Max risk per trade = 1-2% of total account capital.
4.  **Exit Rules:**
    *   **Take Profit:** Close at 50% - 60% of max profit.
    *   **Stop Loss:** Close if the price **touches the Short Strike** OR if the position loss equals **1.5x the credit received**.
    *   **Time Stop:** If the trend continues strong (TD Count moves toward 13), exit immediately. Do not hold a losing spread hoping for a miracle on expiration day.

---

## 5. Agent Guidelines (For AI/Automation)

When acting as an agent executing or analyzing this strategy, adhere to these directives:

*   **Liquidity is King:** Always sort the CSV by `dollar_volume` descending. Do not suggest trades on illiquid stocks (slippage will destroy the edge).
*   **Context Matters:** 
    *   A "Buy 9" (Bullish) works best in a general uptrend (buying the dip) or a flat market.
    *   A "Sell 9" (Bearish) works best in a general downtrend (selling the rip) or flat market.
    *   *Warning:* Be cautious fading a "parabolic" move where news drives the price (e.g., buyout rumors).
*   **Data Validation:** Before recommending a trade, cross-reference the `close_price` in the CSV with the current market price to ensure data freshness.
*   **File Locations:**
    *   Scanner: `reports/td_sequential_report.py`
    *   Daily CSVs: `reports/`
    *   Research: `research/td_sequential_probability.py`

---

## 6. Example Trade
**Scenario:** `AAPL` triggers a **TD Sell Setup 9** (Bearish) at $200.
1.  **View:** Expect AAPL to stay below $205 for the next week.
2.  **Action:** Sell Bear Call Spread.
    *   **Sell:** $205 Call (Short Strike, ~0.30 Delta).
    *   **Buy:** $210 Call (Long Strike, Protection).
3.  **Outcome:** If AAPL stays below $205 by expiration, keep full credit.
