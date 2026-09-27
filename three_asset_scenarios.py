from pathlib import Path
from datetime import datetime, timezone
import time, requests
import numpy as np
import pandas as pd
from scipy.optimize import brentq

ROOT=Path(__file__).resolve().parent; DATA=ROOT/'data'; OUT=ROOT/'results'
START=pd.Timestamp('2021-01-27',tz='UTC'); END=pd.Timestamp('2026-09-26',tz='UTC'); WARM=pd.Timestamp('2020-01-01',tz='UTC')
ASSETS={'BTC':'BTCUSDT','SOL':'SOLUSDT','INJ':'INJUSDT'}; WEIGHTS={'BTC':.5,'SOL':.3,'INJ':.2}; DEPOSIT=100.; FEE=.001; SLIP=.0005
SCENARIOS={
 'no_yield':{'sol_staking':0.,'inj_staking':0.,'usdt_lending':0.},
 'conservative':{'sol_staking':.04,'inj_staking':.08,'usdt_lending':.02},
 'base':{'sol_staking':.0697,'inj_staking':.16,'usdt_lending':.0411},
 'high_yield':{'sol_staking':.08,'inj_staking':.20,'usdt_lending':.06},
 'staking_only':{'sol_staking':.0697,'inj_staking':.16,'usdt_lending':0.},
 'lending_only':{'sol_staking':0.,'inj_staking':0.,'usdt_lending':.0411},
}

def deposits():
    return pd.date_range('2021-01-01','2026-08-01',freq='MS',tz='UTC')+pd.Timedelta(days=26)

def fetch(asset):
    path=DATA/f'{asset.lower()}usdt_1d.csv'
    if path.exists(): return pd.read_csv(path,parse_dates=['open_time'],index_col='open_time')
    DATA.mkdir(exist_ok=True); rows=[]; cur=int(WARM.timestamp()*1000); stop=int((END+pd.Timedelta(days=1)).timestamp()*1000); url='https://api.binance.com/api/v3/klines'
    while cur<stop:
        r=requests.get(url,params={'symbol':ASSETS[asset],'interval':'1d','startTime':cur,'endTime':stop-1,'limit':1000},timeout=30); r.raise_for_status(); b=r.json()
        if not b: break
        rows+=b; nxt=b[-1][0]+86400000
        if nxt<=cur: break
        cur=nxt; time.sleep(.05)
    cols=['open_time','open','high','low','close','volume','close_time','quote_volume','trades','tb_base','tb_quote','ignore']; x=pd.DataFrame(rows,columns=cols)
    x['open_time']=pd.to_datetime(x.open_time,unit='ms',utc=True)
    for c in ['open','high','low','close','volume']: x[c]=pd.to_numeric(x[c])
    x=x.set_index('open_time')[['open','high','low','close','volume']].sort_index(); x=x[~x.index.duplicated()]; x.to_csv(path); return x

def xirr(cfs):
    t0=cfs[0][0]
    def f(r): return sum(v/(1+r)**((d-t0).days/365.0) for d,v in cfs)
    try:return brentq(f,-.9999,100)
    except ValueError:return np.nan

def simulate(data, rates):
    idx=data['BTC'].loc[START:END].index; ddates=deposits(); cash=0.; u={a:0. for a in ASSETS}; deals=[]; daily=[]; prev=0.; tw=1.; peak=1.; sma={a:data[a].close.rolling(200).mean() for a in ASSETS}
    for i,dt in enumerate(idx):
        prices={a:float(data[a].loc[dt,'open']) for a in ASSETS}; close={a:float(data[a].loc[dt,'close']) for a in ASSETS}
        # Lending return on the USDT reserve; staking return on currently held coins.
        cash*= (1+rates['usdt_lending'])**(1/365)
        for a in ['SOL','INJ']: u[a]*=(1+rates[a.lower()+'_staking'])**(1/365)
        dep=DEPOSIT if dt in ddates else 0.; cash+=dep
        pos=data['BTC'].index.get_loc(dt); prevdt=data['BTC'].index[pos-1] if pos>0 else None
        bull={a:(prevdt is not None and pd.notna(sma[a].loc[prevdt]) and data[a].loc[prevdt,'close']>sma[a].loc[prevdt]) for a in ASSETS}
        # Exit bearish assets at next open.
        for a in ASSETS:
            if not bull[a] and u[a]>0:
                ep=prices[a]*(1-SLIP); n=u[a]*ep; fee=n*FEE; cash+=n-fee; deals.append([dt,a,'SELL',u[a],ep,n,fee,u[a]*prices[a]*SLIP]); u[a]=0.
        # Monthly purchase/rebalance. Bearish assets target 0%; remaining target weights stay nominal,
        # so unallocated weight remains in USDT rather than being silently reallocated.
        if dt in ddates:
            total=cash+sum(u[a]*prices[a] for a in ASSETS); target={a:(total*WEIGHTS[a] if bull[a] else 0.) for a in ASSETS}
            for a in ASSETS:
                val=u[a]*prices[a]
                if val>target[a]:
                    q=min(u[a],(val-target[a])/prices[a]); ep=prices[a]*(1-SLIP); n=q*ep; fee=n*FEE; cash+=n-fee; u[a]-=q; deals.append([dt,a,'SELL',q,ep,n,fee,q*prices[a]*SLIP])
            for a in ASSETS:
                need=max(0.,target[a]-u[a]*prices[a])
                if need>0 and cash>0:
                    ep=prices[a]*(1+SLIP); q=min(need/(ep*(1+FEE)),cash/(ep*(1+FEE))); n=q*ep; fee=n*FEE; cash-=n+fee; u[a]+=q; deals.append([dt,a,'BUY',q,ep,n,fee,q*prices[a]*SLIP])
        equity=cash+sum(u[a]*close[a] for a in ASSETS); ret=(equity-dep)/prev-1 if prev>0 else 0.; tw*=1+ret; peak=max(peak,tw); daily.append([dt,equity,dep,tw,tw/peak-1,cash,*[u[a] for a in ASSETS]]); prev=equity
    cols=['date','equity','deposit','twr','drawdown','usdt']+[f'{a}_units' for a in ASSETS]; d=pd.DataFrame(daily,columns=cols).set_index('date'); t=pd.DataFrame(deals,columns=['date','asset','side','units','price','notional','fee','slippage']); cfs=[(x,-DEPOSIT) for x in ddates]+[(d.index[-1],d.equity.iloc[-1])]
    m={'contributions':d.deposit.sum(),'final_value':d.equity.iloc[-1],'profit':d.equity.iloc[-1]-d.deposit.sum(),'return_pct':d.equity.iloc[-1]/d.deposit.sum()-1,'xirr':xirr(cfs),'max_drawdown':d.drawdown.min(),'trades':len(t),'fees':t.fee.sum(),'slippage':t.slippage.sum(),'usdt_final':d.usdt.iloc[-1],**{f'{a}_units':d[f'{a}_units'].iloc[-1] for a in ASSETS}}
    return d,t,m

def main():
    data={a:fetch(a) for a in ASSETS}; rows=[]
    for name,rates in SCENARIOS.items():
        d,t,m=simulate(data,rates); m.update({'scenario':name,**rates}); rows.append(m); d.to_csv(OUT/f'equity_3asset_{name}.csv'); t.to_csv(OUT/f'trades_3asset_{name}.csv',index=False)
    out=pd.DataFrame(rows); out.to_csv(OUT/'three_asset_scenarios.csv',index=False); (OUT/'three_asset_metadata.json').write_text(__import__('json').dumps({'downloaded_utc':datetime.now(timezone.utc).isoformat(),'period_start':str(START),'period_end':str(END),'assets':ASSETS,'weights':WEIGHTS,'monthly_contributions':len(deposits()),'fee':FEE,'slippage':SLIP,'staking_assumption':'SOL and INJ rewards accrue daily and compound; no validator commission or unbonding delay modeled in this first scenario pass','lending_assumption':'USDT reserve compounds daily at scenario rate'},indent=2))
    print(out[['scenario','final_value','return_pct','xirr','max_drawdown','trades','fees','slippage','usdt_final']].to_string(index=False))

if __name__=='__main__':main()
