# DCA vs. Trading Strategies on Bitcoin and Ethereum: What a Five-Year Backtest Actually Shows

Can a simple trend filter improve a monthly DCA strategy on BTC and ETH?

I tested that question using Binance Spot daily candles, identical cash contributions, identical execution rules, and realistic transaction costs.

## The setup

The main test covers 27 September 2021 through 26 September 2026.

- $100 contributed every month;
- 60% allocated to BTC and 40% to ETH;
- 60 contributions, $6,000 in total;
- signals calculated only after a completed daily candle;
- trades executed at the next day's open;
- 0.10% fee per side;
- 0.05% slippage per side;
- spot-only, no leverage and no short selling.

The benchmark was ordinary DCA. It was compared with SMA 200, SMA 50/200, Momentum 90, Donchian 20/10, RSI 14, Bollinger Bands 20/2, monthly-rebalanced DCA, and DCA with an SMA 200 exit filter.

## Main results

| Strategy | Final value | Return | XIRR | Max drawdown |
|---|---:|---:|---:|---:|
| DCA | $10,041 | 67.36% | 20.71% | -76.52% |
| SMA 200 | $11,365 | 89.42% | 25.85% | -35.56% |
| SMA 50/200 | $7,334 | 22.24% | 7.96% | -47.04% |
| Momentum 90 | $9,898 | 64.96% | 20.11% | -56.36% |
| Donchian 20/10 | $6,420 | 7.00% | 2.67% | -44.70% |
| RSI 14 | $6,134 | 2.23% | 0.87% | -46.40% |
| Bollinger 20/2 | $5,268 | -12.20% | -5.10% | -50.70% |

On this particular five-year window, SMA 200 finished $1,324 above DCA, or 13.19%. Its maximum drawdown was also materially lower.

That sounds like a strong result. It is not yet proof of a universal advantage.

## The date of entry matters

SMA 200 did not outperform DCA on every historical period:

- 27.09.2020–26.09.2025: SMA 200 underperformed DCA by 6.83%;
- 27.09.2021–26.09.2026: SMA 200 outperformed by 13.19%;
- 27.09.2022–26.09.2026: SMA 200 outperformed by only 2.21%.

The September 2020 start was especially favorable to DCA: it came after the initial COVID crash but before much of the 2020–2021 crypto rally. A DCA investor still had most of the upside ahead.

The September 2021 start was different: it began after a long rally, immediately before the 2022 bear market. That is exactly the type of regime in which a trend filter can help.

## SMA 200 is not necessarily the best window

I also tested SMA 100, 150, 200, 250, and 300.

On the main period, SMA 150 produced the highest final value, not SMA 200. But selecting SMA 150 after looking at the full sample would itself be a form of overfitting.

To reduce dependence on one start date, I ran 21 overlapping five-year windows with monthly start-date shifts. The available data begins in January 2020, so windows beginning in 2018–2019 could not be tested.

| SMA | Windows beating DCA | Median advantage vs. DCA |
|---:|---:|---:|
| 100 | 38.1% | -4.50% |
| 150 | 76.2% | +15.33% |
| 200 | 57.1% | +3.91% |
| 250 | 19.0% | -11.02% |
| 300 | 23.8% | -11.73% |

SMA 150 was the most consistent in this available sample. That does not mean it should automatically be adopted: the windows overlap, so they are not independent observations.

## Why the combined rebalance strategy failed

The strategy combining monthly rebalancing with SMA 200 exits finished near $7,842, much below the standalone SMA 200 strategy.

The reason was not a signal violation. The audit found zero purchases against the asset's own SMA 200 signal.

The difference came from the portfolio rule. If BTC was bullish and ETH was bearish, ETH was moved to USDT, but BTC still retained a 60% target weight. The remaining capital stayed in USDT instead of being fully reallocated to BTC.

That rule reduces market exposure and can create a large opportunity cost during recoveries.

## Conclusion

The evidence supports a cautious conclusion:

> A long-term trend filter may improve the drawdown profile of a BTC/ETH DCA portfolio, but its advantage depends heavily on the market regime, start date, and moving-average length.

SMA 200 was strong on the main five-year period, but it was not universally superior. The broader rolling analysis points toward a useful range of long-term trend filters rather than a uniquely optimal parameter.

All results, source code, raw candles, trade logs, tests, and charts are available in the accompanying repository.

This is historical research, not investment advice. USDT was valued at $1 and the model does not include taxes, withdrawal costs, or market-impact effects beyond the specified slippage assumption.
