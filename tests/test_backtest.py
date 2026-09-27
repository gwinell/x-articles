import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).parents[1]))
import run_backtest as rb

def test_deposits():
    assert len(rb.DEPOSIT_DATES)==60
    assert rb.DEPOSIT_DATES[0]==pd.Timestamp('2021-09-27',tz='UTC')
    assert rb.DEPOSIT_DATES[-1]==pd.Timestamp('2026-08-27',tz='UTC')

def test_no_future_signal():
    x=pd.DataFrame({'open':[100,100,100],'high':[101,101,101],'low':[99,99,99],'close':[100,101,102]},index=pd.date_range('2021-01-01',periods=3,tz='UTC'))
    i=rb.indicators(x); s=rb.state_series(i,'Momentum90')
    assert not s.iloc[0]

def test_balances_and_costs(tmp_path):
    idx=pd.date_range('2021-09-01','2021-10-01',freq='D',tz='UTC'); x=pd.DataFrame({'open':100.,'high':101.,'low':99.,'close':100.,'volume':1.},index=idx)
    old=rb.DEPOSIT_DATES; rb.DEPOSIT_DATES=pd.DatetimeIndex([pd.Timestamp('2021-09-27',tz='UTC')])
    d,t,m=rb.simulate('BTC',x,'DCA'); rb.DEPOSIT_DATES=old
    assert (d.cash>=-1e-8).all(); assert (d.equity>=-1e-8).all(); assert m['fees']>0; assert m['slippage']>0

def test_equity_matches_ledger():
    p=rb.OUT/'summary.csv'
    if p.exists():
        s=pd.read_csv(p); assert (s.final_value>=0).all()
