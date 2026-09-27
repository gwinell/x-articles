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
