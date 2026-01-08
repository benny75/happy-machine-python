# 0DTE Intraday Short Strangle / Iron Condor

## 1. Strategy Overview
**Type:** Volatility Selling / Range Trading  
**Instrument:** SPX (Cash Settled) or SPY (ETF) Options  
**Core Logic:** This strategy exploits the **Variance Risk Premium (VRP)** and **Exponential Theta Decay**. On most trading days, the S&P 500 stays within a ±1% range. 0DTE (Zero Days to Expiration) options are often priced for a larger move than realized, allowing us to sell "insurance" that expires worthless by 4:00 PM EST.

---

## 2. Entry Conditions & Setup

### Timing
*   **Entry:** 10:00 AM EST (30-45 minutes after the open). This allows the "Morning Volatility" to settle and the day's range to begin forming.
*   **Duration:** Intraday only. **NEVER** hold 0DTE positions overnight.

### Structure
*   **Preferred Instrument:** **SPX** (Tax efficiency Section 1256, cash-settled, no assignment risk).
*   **Legs:** 
    *   **Short Strangle:** Sell OTM Call + Sell OTM Put (For larger accounts).
    *   **Iron Condor:** Short Strangle + Long OTM wings (For defined risk/smaller accounts).
*   **Strikes:** 
    *   **Delta:** 0.10 to 0.15 on both sides.
    *   **Distance:** Typically ±1% to ±1.5% from current spot price.

---

## 3. Mathematical Edge (The "Why")
*   **Theta Decay:** 0DTE options lose ~10-15% of their value *per hour* during the middle of the day.
*   **Realized vs Implied:** Historical data shows that SPY stays within the 10-Delta range ~88% of the time, yet the market prices it as if it only stays within range ~80% of the time.

---

## 4. Risk Management (The "How to Survive")

1.  **Stop Loss (Crucial):** 
    *   Set a **Hard Stop** at **3x the Credit Received**. (e.g., if you collect $1.00, exit if the position value hits $3.00). 
    *   This prevents "Gamma Risk" (delta moving against you too fast) from wiping out months of gains.
2.  **Gamma Risk Management:** Exit early (2:00 PM - 3:00 PM) if you have already captured 80% of the profit. The last 20% of premium carries 100% of the "Gamma Bomb" risk.
3.  **VIX Filter:** Do not trade if the VIX is spiking (>10% increase intraday). High volatility days are "Trend Days" where the market breaks ranges.
4.  **Trend Awareness:** If the market is clearly trending in one direction, consider a **Skewed Entry** (Selling further OTM on the side the market is moving toward).

---

## 5. Script Workflow

### A. Probability Check
Check historical move probabilities to set your strike distance:
```bash
python3 research/0DTE-short-strangle.py
```

### B. Backtesting (Planned)
Run the backtester to see PnL with Stop Losses:
```bash
python3 research/0DTE_backtester.py
```

---

## 6. Execution Example
**Time:** 10:00 AM EST  
**SPY Price:** $500  
1.  **Sell Put:** $495 (10 Delta) - Collect $0.40  
2.  **Sell Call:** $505 (10 Delta) - Collect $0.40  
**Total Credit:** $0.80 ($80 per contract)  
**Stop Loss:** Exit if total spread costs > $2.40.  
**Profit Target:** Close at $0.10 or let expire at $0.00.
