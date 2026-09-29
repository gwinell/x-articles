# Market extension: crypto, US equities and mixed DCA portfolios

This subproject is intentionally separate from the original BTC/ETH outputs.

```bash
python -m venv .venv
.venv/bin/pip install -r market_extension/requirements.txt
.venv/bin/python market_extension/backtest_market.py
.venv/bin/python market_extension/make_outputs.py
.venv/bin/python market_extension/make_report.py
.venv/bin/pytest -q market_extension/tests
```

The backtest saves downloaded prices under `market_extension/data/`, journals and daily values under `market_extension/results/`, and publication figures under `market_extension/results/figures/`. It reuses the existing parent BTC/ETH CSV files and does not overwrite the earlier research outputs.

The fallback data path uses Nasdaq's public JSON endpoints for stock/ETF OHLC and dividends for individual stocks, plus DividendSmart's historical ETF distribution pages. See `results/market_metadata.json` and `market_report.md` for the exact data caveats.

The separate `futures_leverage_backtest.py` uses Binance USDⓈ-M perpetual klines and funding rates to test 5x isolated long SMA150 variants. The BTC/SOL/INJ futures comparison starts on 2022-08-17 because the INJUSDT perpetual did not exist for the full 2021 start date.
