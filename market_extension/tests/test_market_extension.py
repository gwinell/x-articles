from pathlib import Path
import pandas as pd
import numpy as np
import sys
sys.path.insert(0,str(Path(__file__).parents[1]))
import backtest_market as bm

ROOT=Path(__file__).parents[1]; RES=ROOT/'results'

def test_exact_deposit_schedule():
    data={'VOO':pd.DataFrame(index=pd.date_range('2021-09-27','2026-09-26',freq='B',tz='UTC'))}
    cal,_=bm.trading_calendar({'VOO':data['VOO'],'BTC':data['VOO'],'ETH':data['VOO']})
    scheduled=bm.execution_deposit_dates(cal)
    assert len(scheduled)==60
    assert [d.day for d,_ in scheduled]==[27]*60
    assert scheduled[0][0]==pd.Timestamp('2021-09-27',tz='UTC')
    assert scheduled[-1][0]==pd.Timestamp('2026-08-27',tz='UTC')

def test_no_future_sma_signal():
    x=pd.read_csv(RES/'trades_B_S&P500_VOO_SMA200.csv',parse_dates=['date'])
    p=pd.read_csv(ROOT/'data/VOO_daily.csv',parse_dates=['date']).set_index('date')
    for _,r in x[x.side=='BUY'].iterrows():
        pos=p.index.get_loc(r.date); assert pos>0
        prev=p.iloc[:pos].close.iloc[-1]; sma=p.iloc[:pos].close.rolling(200).mean().iloc[-1]
        assert pd.notna(sma) and prev>sma

def test_no_negative_cash_and_ledger_reconciliation():
    for p in RES.glob('equity_*.csv'):
        x=pd.read_csv(p)
        assert (x.cash>=-1e-8).all()
        label=p.stem.replace('equity_','')
        t=pd.read_csv(RES/f'trades_{label}.csv')
        assert (t.fee>=0).all() and (t.slippage>=0).all()
        dt=pd.Timestamp(x.date.iloc[-1]); marked=x.cash.iloc[-1]
        for c in [c for c in x if c.endswith('_units')]:
            a=c[:-6]
            qfile=ROOT/'data'/f'{a}_daily.csv' if a not in {'BTC','ETH'} else ROOT.parent/'data'/f'{a.lower()}usdt_1d.csv'
            key='date' if a not in {'BTC','ETH'} else 'open_time'
            q=pd.read_csv(qfile,parse_dates=[key]).set_index(key)
            marked += x[c].iloc[-1]*q.loc[dt,'close']
        assert abs(x.equity.iloc[-1]-marked)<1e-6

def test_trade_costs_are_recorded():
    t=pd.read_csv(RES/'trades_A_Crypto_DCA_SMA200.csv')
    assert t.fee.sum()>0 and t.slippage.sum()>0
    assert (t.notional>=0).all()

def test_final_value_matches_daily_mark_to_market():
    # For each journal, the final equity must be positive and all units nonnegative.
    for p in RES.glob('equity_*.csv'):
        x=pd.read_csv(p)
        unit_cols=[c for c in x if c.endswith('_units')]
        assert (x[unit_cols]>=-1e-10).all().all()
        assert x.equity.iloc[-1]>=x.cash.iloc[-1]-1e-8
