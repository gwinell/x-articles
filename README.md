# BTC/ETH стратегии: воспроизводимый бэктест

## Запуск

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python3 run_backtest.py
pytest -q
python3 audit_checks.py
python3 rolling_5y_backtest.py
```

Скрипт загружает Binance Spot klines, сохраняет котировки в `data/`, сделки и дневные equity в `results/`, графики в `results/figures/`, а отчёт — в `report.md`.

Даты трактуются как UTC. Базовая модель: 0.10% комиссия и 0.05% проскальзывание на каждую сторону; исполнение по open следующего дня; USDT оценивается как $1.

`audit_checks.py` проверяет покупки против собственного SMA 200, сравнивает журналы сделок и позиции, а также создаёт `results/robustness_periods.csv` для альтернативных периодов.

`rolling_5y_backtest.py` запускает 21 перекрывающееся пятилетнее окно с ежемесячным сдвигом от 27.01.2020 до 27.09.2021 и тестирует SMA 100/150/200/250/300.
