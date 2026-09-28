from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parent
RES=ROOT/'results'
s=pd.read_csv(RES/'market_comparison_summary.csv')

def money(x): return f'${x:,.2f}'
def pct(x): return f'{x:.2%}'
def row(r):
    return f"|{r.portfolio}|{money(r.contributions)}|{money(r.final_value)}|{money(r.profit)}|{pct(r.return_pct)}|{pct(r.xirr)}|{pct(r.max_drawdown)}|{money(r.fees)}|{money(r.slippage)}|{int(r.trades)}|{money(r.dividends)}|{money(r.final_cash)}|\n"

table='|Portfolio|Contributions|Final value|Profit|Return|XIRR|Max drawdown|Fees|Slippage|Trades|Dividends|Final cash|\n|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n'
for _,r in s.iterrows(): table+=row(r)

period=pd.read_csv(RES/'period_start_comparison.csv')
ind=pd.read_csv(RES/'independent_crypto_sma_summary.csv')
grid=pd.read_csv(RES/'crypto_sma_grid_summary.csv')
ptable='|Portfolio|Start window|Contributions|Final value|Return|Max drawdown|\n|---|---:|---:|---:|---:|---:|\n'
for _,r in period.iterrows(): ptable+=f'|{r.portfolio}|{r.portfolio[-4:]}|{money(r.contributions)}|{money(r.final_value)}|{pct(r.return_pct)}|{pct(r.max_drawdown)}|\n'
itable='|Strategy|Final value|Return|XIRR|Max drawdown|Trades|Costs|BTC cash|ETH cash|\n|---|---:|---:|---:|---:|---:|---:|---:|---:|\n'
for _,r in ind.iterrows(): itable+=f'|{r.portfolio}|{money(r.final_value)}|{pct(r.return_pct)}|{pct(r.xirr)}|{pct(r.max_drawdown)}|{int(r.trades)}|{money(r.fees+r.slippage)}|{money(r.BTC_final_cash)}|{money(r.ETH_final_cash)}|\n'
gtable='|Variant|Grid allocation at entry|Final value|Return|XIRR|Max drawdown|Grid trades|Costs|BTC grid days|ETH grid days|\n|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n'
for _,r in grid.iterrows(): gtable+=f'|{r.portfolio}|{pct(r.grid_fraction)}|{money(r.final_value)}|{pct(r.return_pct)}|{pct(r.xirr)}|{pct(r.max_drawdown)}|{int(r.grid_trades)}|{money(r.fees+r.slippage)}|{int(r.BTC_grid_days)}|{int(r.ETH_grid_days)}|\n'

def get(name,col): return s.loc[s.portfolio==name,col].iloc[0]

report=f'''# BTC/ETH, US stocks, ETFs and mixed portfolios: DCA extension

## Executive summary

This is a reproducible extension of the earlier BTC/ETH research. The primary simulation uses 60 monthly contributions of $100 from 27 September 2021 through 27 August 2026, evaluated on the last common available session, 25 September 2026 UTC. Total contributions are $6,000 and every portfolio receives the same cash-flow schedule.

Among diversified portfolios, VOO 80% / BTC 20% with annual rebalancing finished at **{money(get('E_VOO_BTC_annual_rebalance','final_value'))}**, followed by VT 80% / BTC 20% with annual rebalancing at **{money(get('G_VT_BTC_annual_rebalance','final_value'))}**. Crypto DCA finished at {money(get('A_Crypto_DCA','final_value'))}; VOO DCA at {money(get('B_S&P500_VOO','final_value'))}.

The strongest result overall was the pre-selected single-stock experiment, NVDA at {money(get('NVDA_only','final_value'))}. This is not a representative random-stock result: the ticker was selected after observing its historical prominence.

The principal risk distinction is drawdown. Crypto DCA reached {pct(get('A_Crypto_DCA','max_drawdown'))}; VOO DCA reached {pct(get('B_S&P500_VOO','max_drawdown'))}; VOO/BTC annual rebalancing reached {pct(get('E_VOO_BTC_annual_rebalance','max_drawdown'))}. Diversification reduced observed drawdown but did not remove it.

## Main comparison table

{table}

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

{ptable}

These overlapping windows are sensitivity tests, not independent observations and not a guarantee of future performance.

## Independent SMA signals for BTC and ETH

The main crypto SMA rows use one composite 60/40 portfolio signal. The following separate experiment instead applies the SMA independently to BTC and ETH. Each asset has its own USDT reserve; a bearish BTC signal cannot fund an ETH purchase.

{itable}

Independent SMA150 finished below the composite SMA150 but had a materially smaller drawdown. Independent SMA200 finished above the composite SMA200 and also reduced drawdown. This confirms that the signal definition itself is economically important.

## Grid variants during flat periods

During a flat period, all future monthly deposits for the relevant asset are sent to the active grid. The 100% variant transfers the full current asset subportfolio to the grid; the 50% variant transfers half and leaves the other half under SMA150. The grid uses the previous 30 completed candles, 10 fixed levels, and separate BTC/ETH bots. A bullish SMA150 signal closes the grid and returns the capital to the standard asset strategy.

{gtable}

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
'''
(ROOT/'market_report.md').write_text(report)
print(ROOT/'market_report.md')
