# BTC/ETH, US stocks, ETFs and mixed portfolios: DCA extension

## Executive summary

This is a reproducible extension of the earlier BTC/ETH research. The primary simulation uses 60 monthly contributions of $100 from 27 September 2021 through 27 August 2026, evaluated on the last common available session, 25 September 2026 UTC. Total contributions are $6,000 and every portfolio receives the same cash-flow schedule.

Among diversified portfolios, VOO 80% / BTC 20% with annual rebalancing finished at **$10,339.29**, followed by VT 80% / BTC 20% with annual rebalancing at **$10,166.80**. Crypto DCA finished at $9,998.90; VOO DCA at $9,536.57.

The strongest result overall was the pre-selected single-stock experiment, NVDA at $32,389.18. This is not a representative random-stock result: the ticker was selected after observing its historical prominence.

The principal risk distinction is drawdown. Crypto DCA reached -75.42%; VOO DCA reached -24.46%; VOO/BTC annual rebalancing reached -34.34%. Diversification reduced observed drawdown but did not remove it.

## Main comparison table

|Portfolio|Contributions|Final value|Profit|Return|XIRR|Max drawdown|Fees|Slippage|Trades|Dividends|Final cash|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|A_Crypto_DCA|$6,000.00|$9,998.90|$3,998.90|66.65%|20.55%|-75.42%|$5.99|$3.00|120|$0.00|$-0.00|
|A_Crypto_DCA_annual_rebalance|$6,000.00|$9,766.42|$3,766.42|62.77%|19.58%|-75.42%|$8.17|$4.09|128|$0.00|$-0.00|
|B_S&P500_VOO|$6,000.00|$9,536.57|$3,536.57|58.94%|18.61%|-24.46%|$0.00|$3.00|60|$244.19|$-0.00|
|C_Total_US_VTI|$6,000.00|$9,394.55|$3,394.55|56.58%|17.99%|-25.38%|$0.00|$3.00|60|$238.87|$-0.00|
|D_Global_VT|$6,000.00|$9,269.13|$3,269.13|54.49%|17.44%|-26.29%|$0.00|$3.00|60|$361.34|$0.00|
|E_VOO_BTC|$6,000.00|$9,997.55|$3,997.55|66.63%|20.55%|-34.34%|$1.20|$3.00|120|$195.36|$0.00|
|E_VOO_BTC_annual_rebalance|$6,000.00|$10,339.29|$4,339.29|72.32%|21.94%|-34.34%|$2.49|$4.29|128|$214.71|$-0.00|
|F_VOO_BTC_ETH|$6,000.00|$9,537.25|$3,537.25|58.95%|18.61%|-46.07%|$2.40|$3.00|180|$146.52|$-0.00|
|F_VOO_BTC_ETH_annual_rebalance|$6,000.00|$9,816.67|$3,816.67|63.61%|19.79%|-46.07%|$3.95|$4.51|192|$161.91|$-0.00|
|G_VT_BTC|$6,000.00|$9,783.60|$3,783.60|63.06%|19.66%|-37.10%|$1.20|$3.00|120|$289.07|$-0.00|
|G_VT_BTC_annual_rebalance|$6,000.00|$10,166.80|$4,166.80|69.45%|21.24%|-37.10%|$2.59|$4.39|128|$322.12|$-0.00|
|AAPL_only|$6,000.00|$10,797.95|$4,797.95|79.97%|23.74%|-33.34%|$0.00|$3.00|60|$90.31|$-0.00|
|MSFT_only|$6,000.00|$8,978.15|$2,978.15|49.64%|16.14%|-36.73%|$0.00|$3.00|60|$156.67|$0.00|
|NVDA_only|$6,000.00|$32,389.18|$26,389.18|439.82%|72.94%|-66.15%|$0.00|$3.00|60|$112.43|$-0.00|
|GOOGL_only|$6,000.00|$13,701.82|$7,701.82|128.36%|33.78%|-44.09%|$0.00|$3.00|60|$71.63|$-0.00|
|B_S&P500_VOO_SMA150|$6,000.00|$8,658.99|$2,658.99|44.32%|14.66%|-20.30%|$0.00|$46.94|84|$172.43|$-0.00|
|B_S&P500_VOO_SMA200|$6,000.00|$8,406.46|$2,406.46|40.11%|13.46%|-22.68%|$0.00|$33.64|75|$187.25|$-0.00|
|C_Total_US_VTI_SMA150|$6,000.00|$8,209.05|$2,209.05|36.82%|12.50%|-20.64%|$0.00|$48.35|84|$147.42|$-0.00|
|C_Total_US_VTI_SMA200|$6,000.00|$8,165.68|$2,165.68|36.09%|12.29%|-21.59%|$0.00|$37.30|75|$165.69|$-0.00|
|A_Crypto_DCA_SMA150|$6,000.00|$12,573.36|$6,573.36|109.56%|30.12%|-47.43%|$208.11|$104.05|156|$0.00|$-0.00|
|A_Crypto_DCA_SMA200|$6,000.00|$10,112.13|$4,112.13|68.54%|21.02%|-44.07%|$107.20|$53.60|108|$0.00|$-0.00|


## Methodology

- BTC/USDT and ETH/USDT use the existing Binance Spot daily files from the parent research. VOO, VTI, VT, AAPL, MSFT, NVDA and GOOGL use Nasdaq's public historical endpoint for OHLC.
- Stock dividends are reinvested explicitly into the same asset at that day's close. Adjusted close is not used for the simulation, so dividends are not counted twice. ETF distributions come from DividendSmart's split-adjusted historical distribution pages for VOO, VTI and VT; URLs and download timestamp are recorded in `results/market_metadata.json`.
- Corporate actions are represented by the source's split-adjusted historical series. No missing prices are filled with invented values.
- Cash is scheduled on the 27th; if that is not a US session, execution moves to the next common US trading session. For synchronized comparison, crypto trades in this extension use the same common session calendar. The last common date is 25 September 2026 because 26 September is not a US session.
- Stocks/ETFs use 0% commission and 0.05% slippage per side. Crypto uses 0.10% commission and 0.05% slippage per side. Fractional units are allowed.
- SMA signals use only the previous completed daily close and execute at the next session open. Annual rebalancing values positions at the session open, preventing use of that day's later close.
- No taxes, financing, custody, staking, lending or jurisdiction-specific fees are included. Cash/USDT is valued at exactly $1.

XIRR is the annualized `r` solving `sum(CF_i / (1+r)^((date_i-date_0)/365)) = 0`, with deposits negative and terminal portfolio value positive. Maximum drawdown is measured on time-weighted wealth: each external deposit is removed before that day's return is calculated.

## What drove the results

1. **Crypto exposure drove both upside and downside.** Crypto DCA finished above the broad equity ETFs in this sample, but its maximum drawdown was roughly three times VOO's. Adding VOO or VT kept meaningful upside while reducing the observed drawdown.
2. **Annual rebalancing was regime-dependent.** It improved VOO/BTC and VT/BTC in this window but reduced pure BTC/ETH DCA. Rebalancing sells relative winners and buys relative losers, so sequence matters.
3. **Single-stock results are not an asset-class benchmark.** NVDA and GOOGL were exceptional; MSFT underperformed VOO and AAPL outperformed it. The dispersion is itself a concentration-risk warning.
4. **SMA controlled risk more consistently than terminal wealth.** SMA150/200 reduced VOO/VTI drawdown relative to DCA but also reduced ending value here. On the crypto portfolio, SMA150 improved terminal value and reduced drawdown; SMA200 was close to crypto DCA with a smaller drawdown.

## Cost sensitivity

The base case includes the stated commission and slippage assumptions. A zero-cost run and a double-cost run are saved in `results/cost_sensitivity.csv`. For the primary crypto DCA, ending value was $10,013.91 with zero costs, $9,998.90 in the base case and $9,983.94 with doubled costs. The difference is economically visible but much smaller than the effect of asset allocation and drawdown regime in this low-turnover DCA sample.

## Start-date sensitivity

The following windows use the same monthly $100 rule and common end date. Starts in 2020, 2021 and 2022 contain 72, 60 and 48 deposits respectively, so absolute ending values are not directly comparable without considering the different contribution counts.

|Portfolio|Start window|Contributions|Final value|Return|Max drawdown|
|---|---:|---:|---:|---:|---:|
|A_Crypto_DCA_start2020|2020|$7,200.00|$13,678.34|89.98%|-76.60%|
|B_S&P500_VOO_start2020|2020|$7,200.00|$12,103.07|68.10%|-24.48%|
|F_VOO_BTC_ETH_start2020|2020|$7,200.00|$12,532.52|74.06%|-55.62%|
|G_VT_BTC_start2020|2020|$7,200.00|$12,355.22|71.60%|-41.15%|
|A_Crypto_DCA_start2021|2021|$6,000.00|$9,998.90|66.65%|-75.42%|
|B_S&P500_VOO_start2021|2021|$6,000.00|$9,536.57|58.94%|-24.46%|
|F_VOO_BTC_ETH_start2021|2021|$6,000.00|$9,537.25|58.95%|-46.07%|
|G_VT_BTC_start2021|2021|$6,000.00|$9,783.60|63.06%|-37.10%|
|A_Crypto_DCA_start2022|2022|$4,800.00|$7,626.87|58.89%|-57.41%|
|B_S&P500_VOO_start2022|2022|$4,800.00|$7,238.15|50.79%|-18.73%|
|F_VOO_BTC_ETH_start2022|2022|$4,800.00|$7,272.93|51.52%|-31.00%|
|G_VT_BTC_start2022|2022|$4,800.00|$7,458.61|55.39%|-19.81%|


These overlapping windows are sensitivity tests, not independent observations and not a guarantee of future performance.

## Independent SMA signals for BTC and ETH

The main crypto SMA rows use one composite 60/40 portfolio signal. The following separate experiment instead applies the SMA independently to BTC and ETH. Each asset has its own USDT reserve; a bearish BTC signal cannot fund an ETH purchase.

|Strategy|Final value|Return|XIRR|Max drawdown|Trades|Costs|BTC cash|ETH cash|
|---|---:|---:|---:|---:|---:|---:|---:|---:|
|A_Crypto_DCA_independent_SMA150|$12,103.91|101.73%|28.52%|-36.36%|128|$275.62|$-0.00|$-0.00|
|A_Crypto_DCA_independent_SMA200|$10,595.19|76.59%|22.95%|-37.26%|119|$239.62|$-0.00|$-0.00|


Independent SMA150 finished below the composite SMA150 but had a materially smaller drawdown. Independent SMA200 finished above the composite SMA200 and also reduced drawdown. This confirms that the signal definition itself is economically important.

## Grid variants during flat periods

During a flat period, all future monthly deposits for the relevant asset are sent to the active grid. The 100% variant transfers the full current asset subportfolio to the grid; the 50% variant transfers half and leaves the other half under SMA150. The grid uses the previous 30 completed candles, 10 fixed levels, and separate BTC/ETH bots. A bullish SMA150 signal closes the grid and returns the capital to the standard asset strategy.

|Variant|Grid allocation at entry|Final value|Return|XIRR|Max drawdown|Grid trades|Costs|BTC grid days|ETH grid days|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|A_Crypto_SMA150_grid100|100.00%|$11,281.36|88.02%|25.56%|-37.16%|195|$299.51|360|378|
|A_Crypto_SMA150_grid50|50.00%|$11,689.35|94.82%|27.05%|-36.76%|195|$287.70|360|378|


The grid reduced drawdown relative to independent SMA150, but in this five-year sample it also reduced terminal value. This result is sensitive to the range, number of levels, fill assumptions and the treatment of a breakout.

## Files and reproducibility

- `backtest_market.py` — downloader, simulator, metrics and CSV export.
- `make_outputs.py` — Matplotlib/Seaborn PNGs and GIF.
- `tests/test_market_extension.py` — nine automated checks; latest run: **9 passed**.
- `data/` — downloaded stock/ETF OHLC and the used market files.
- `results/market_comparison_summary.csv` — machine-readable main table.
- `results/period_start_comparison.csv` — start-date robustness.
- `results/equity_*.csv`, `trades_*.csv`, `dividends_*.csv` — daily valuations and journals.
- `results/figures/` — PNGs and `portfolio_growth.gif`.

## Limitations

The crypto daily candle is UTC-based while US exchanges close in US Eastern Time. The model synchronizes to the last common US session, but the two markets are not observed at an identical instant. Yahoo Finance was attempted but timed out in the execution environment; the fallback is documented Nasdaq OHLC/dividend data plus DividendSmart ETF distributions. ETF distribution-source corrections should be independently audited before publication. The model assumes fractional shares, immediate dividend reinvestment, no tax and cash/USDT at $1.

## Article concept for @jestfi

Suggested titles:

- **The boring $100 portfolio vs Bitcoin: what five years of identical deposits actually bought**
- **Crypto, VOO, or both? One cash-flow schedule, seven portfolios, very different drawdowns**
- **The best portfolio was not the one with the highest return**

Recommended narrative: open with the identical $100/month rule, show the ending-capital chart, then reveal drawdowns. Explain that VOO/BTC annual rebalancing produced a strong middle ground in this sample, while pure crypto delivered much larger swings and selected NVDA was a hindsight outlier. Finish with a practical framework: crypto for maximum volatility and upside exposure, broad ETFs for lower drawdown and simpler implementation, and mixed portfolios for an explicit risk/return compromise. Avoid guarantees and label every result as historical simulation.
