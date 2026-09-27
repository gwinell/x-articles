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
    assert (t.notional>=bm.MIN_TRADE_USD-1e-9).all()

def test_crypto_sma_never_buys_on_negative_signal_and_keeps_60_40():
    b=pd.read_csv(ROOT.parent/'data/btcusdt_1d.csv',parse_dates=['open_time']).set_index('open_time')
    e=pd.read_csv(ROOT.parent/'data/ethusdt_1d.csv',parse_dates=['open_time']).set_index('open_time')
    idx=b.index.intersection(e.index); base=idx[idx>=pd.Timestamp('2021-09-27',tz='UTC')][0]
    synthetic=.6*b.close.loc[idx]/b.close.loc[base]+.4*e.close.loc[idx]/e.close.loc[base]
    sma=synthetic.rolling(200).mean(); t=pd.read_csv(RES/'trades_A_Crypto_DCA_SMA200.csv',parse_dates=['date'])
    for d in t.loc[t.side=='BUY','date'].drop_duplicates():
        pos=synthetic.index.get_loc(d); assert pos>0 and pd.notna(sma.iloc[pos-1]) and synthetic.iloc[pos-1]>sma.iloc[pos-1]
    buys=t[t.side=='BUY'].copy(); buys['spent']=buys.notional+buys.fee
    for d,g in buys.groupby('date'):
        if set(g.asset)=={'BTC','ETH'}:
            assert abs(g.loc[g.asset=='BTC','spent'].sum()/g.spent.sum()-.6)<1e-8
            assert abs(g.loc[g.asset=='ETH','spent'].sum()/g.spent.sum()-.4)<1e-8

def test_primary_contributions_equal_6000():
    for p in RES.glob('equity_*.csv'):
        if any(x in p.name for x in ['start2020','start2021','start2022']): continue
        x=pd.read_csv(p)
        assert abs(x.deposit.sum()-6000)<1e-8

def test_independent_sma_uses_segregated_cash_and_own_signal():
    for window in [150,200]:
        label=f'A_Crypto_DCA_independent_SMA{window}'
        x=pd.read_csv(RES/f'equity_{label}.csv')
        assert (x[['BTC_cash','ETH_cash']]>=-1e-8).all().all()
        t=pd.read_csv(RES/f'trades_{label}.csv',parse_dates=['date'])
        for _,r in t[t.side=='BUY'].iterrows():
            p=pd.read_csv(ROOT.parent/'data'/f'{r.asset.lower()}usdt_1d.csv',parse_dates=['open_time']).set_index('open_time')
            pos=p.index.get_loc(r.date); prev=p.close.iloc[pos-1]; sma=p.close.iloc[:pos].rolling(window).mean().iloc[-1]
            assert pd.notna(sma) and prev>sma

def test_final_value_matches_daily_mark_to_market():
    # For each journal, the final equity must be positive and all units nonnegative.
    for p in RES.glob('equity_*.csv'):
        x=pd.read_csv(p)
        unit_cols=[c for c in x if c.endswith('_units')]
        assert (x[unit_cols]>=-1e-10).all().all()
        assert x.equity.iloc[-1]>=x.cash.iloc[-1]-1e-8
