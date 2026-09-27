import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
import run_backtest as rb

OUT=rb.OUT; FEE=.001; SLIP=.0005

def deposits(start,end):
    return pd.date_range(start.replace(day=1), end.replace(day=1)-pd.offsets.MonthBegin(1), freq='MS', tz='UTC')+pd.Timedelta(days=26)

def asset_run(x, asset, start, end, mode, window=None):
    depdates=deposits(start,end); research=x.loc[start:end]; cash=0.; units=0.; position=False; rows=[]; fees=slips=trades=0.; prev=0.; tw=1.; peak=1.
    sma=x.close.rolling(window).mean() if mode=='sma' else None
    for dt,r in research.iterrows():
        dep=rb.FUNDING[asset] if dt in depdates else 0.; cash+=dep
        pos=x.index.get_loc(dt); prevdt=x.index[pos-1] if pos>0 else None
        bullish=bool(x.loc[prevdt,'close']>sma.loc[prevdt]) if mode=='sma' and prevdt is not None and pd.notna(sma.loc[prevdt]) else (mode=='dca')
        if bullish and not position and cash>0:
            ep=r.open*(1+SLIP); q=cash/(ep*(1+FEE)); n=q*ep; f=n*FEE; cash-=n+f; units+=q; position=True; trades+=1; fees+=f; slips+=q*r.open*SLIP
        elif bullish and position and dep>0:
            ep=r.open*(1+SLIP); q=cash/(ep*(1+FEE)); n=q*ep; f=n*FEE; cash-=n+f; units+=q; trades+=1; fees+=f; slips+=q*r.open*SLIP
        elif not bullish and position:
            ep=r.open*(1-SLIP); n=units*ep; f=n*FEE; cash+=n-f; trades+=1; fees+=f; slips+=units*r.open*SLIP; units=0.; position=False
        equity=cash+units*r.close; ret=(equity-dep)/prev-1 if prev>0 else 0.; tw*=1+ret; peak=max(peak,tw)
        rows.append([dt,equity,dep,tw,tw/peak-1]); prev=equity
    return pd.DataFrame(rows,columns=['date','equity','deposit','twr','drawdown']).set_index('date'), fees, slips, trades, units, cash

def xirr_for(d):
    cf=[(dt,-100.) for dt in d.index[d.deposit>0]]+[(d.index[-1],d.equity.iloc[-1])]
    return rb.xirr(cf)

def run_period(data,start,end,window):
    ds=[]; ss=[]; fee=slip=trades=0
    for a in ['BTC','ETH']:
        d,*m=asset_run(data[a],a,start,end,'dca'); ds.append(d); fee+=m[0]; slip+=m[1]; trades+=m[2]
    dca=pd.DataFrame(index=ds[0].index); dca['equity']=ds[0].equity+ds[1].equity; dca['deposit']=ds[0].deposit+ds[1].deposit; dca['ret']=(dca.equity-dca.deposit)/dca.equity.shift(1)-1; dca.iloc[0,dca.columns.get_loc('ret')]=0; dca['twr']=(1+dca.ret).cumprod(); dca['drawdown']=dca.twr/dca.twr.cummax()-1
    dsa=[]; fee2=slip2=trades2=0
    for a in ['BTC','ETH']:
        d,*m=asset_run(data[a],a,start,end,'sma',window); dsa.append(d); fee2+=m[0]; slip2+=m[1]; trades2+=m[2]
    sma=pd.DataFrame(index=dsa[0].index); sma['equity']=dsa[0].equity+dsa[1].equity; sma['deposit']=dsa[0].deposit+dsa[1].deposit; sma['ret']=(sma.equity-sma.deposit)/sma.equity.shift(1)-1; sma.iloc[0,sma.columns.get_loc('ret')]=0; sma['twr']=(1+sma.ret).cumprod(); sma['drawdown']=sma.twr/sma.twr.cummax()-1
    return {'period_start':start.date(),'period_end':end.date(),'window':window,'contributions':dca.deposit.sum(),'dca_final':dca.equity.iloc[-1],'sma_final':sma.equity.iloc[-1],'difference_usd':sma.equity.iloc[-1]-dca.equity.iloc[-1],'difference_pct':sma.equity.iloc[-1]/dca.equity.iloc[-1]-1,'dca_xirr':xirr_for(dca),'sma_xirr':xirr_for(sma),'dca_max_dd':dca.drawdown.min(),'sma_max_dd':sma.drawdown.min(),'dca_trades':trades,'sma_trades':trades2,'sma_fees':fee2,'sma_slippage':slip2}

def main():
    data={a:rb.fetch_symbol(a) for a in ['BTC','ETH']}
    periods=[('early_5y',pd.Timestamp('2020-09-27',tz='UTC'),pd.Timestamp('2025-09-26',tz='UTC')),('main_5y',pd.Timestamp('2021-09-27',tz='UTC'),pd.Timestamp('2026-09-26',tz='UTC')),('late_4y',pd.Timestamp('2022-09-27',tz='UTC'),pd.Timestamp('2026-09-26',tz='UTC')),('oos_1y',pd.Timestamp('2025-09-27',tz='UTC'),pd.Timestamp('2026-09-26',tz='UTC'))]
    rows=[dict(period=label,**run_period(data,start,end,w)) for label,start,end in periods for w in [100,150,200,250,300]]
    out=pd.DataFrame(rows); out.to_csv(OUT/'sma_window_robustness.csv',index=False)
    print(out.to_string(index=False))

if __name__=='__main__': main()
