from pathlib import Path
from datetime import datetime, timezone
import requests
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent; DATA=ROOT/'data'/'futures'; RES=ROOT/'results'; DATA.mkdir(parents=True,exist_ok=True)
END=pd.Timestamp('2026-09-26',tz='UTC'); START=pd.Timestamp('2021-09-27',tz='UTC'); LEV=5.; FEE=.001; SLIP=.0005; MMR=.005; FUNDING_LIMIT=1000

def get_klines(symbol,start):
    p=DATA/f'{symbol}_1d.csv'
    if p.exists(): return pd.read_csv(p,parse_dates=['date']).set_index('date')
    out=[]; cursor=int(start.timestamp()*1000); end=int((END+pd.Timedelta(days=1)).timestamp()*1000)
    while cursor<end:
        j=requests.get('https://fapi.binance.com/fapi/v1/klines',params={'symbol':symbol,'interval':'1d','startTime':cursor,'endTime':end,'limit':1500},timeout=30).json()
        if not j: break
        out.extend(j); cursor=j[-1][0]+86400000
        if len(j)<1500: break
    x=pd.DataFrame(out,columns=['open_time','open','high','low','close','volume','close_time','quote_volume','trades','taker_base','taker_quote','ignore'])
    x['date']=pd.to_datetime(x.open_time,unit='ms',utc=True); x=x.set_index('date')
    for c in ['open','high','low','close']: x[c]=pd.to_numeric(x[c])
    x=x[['open','high','low','close']].loc[:END]; x.to_csv(p); return x

def get_funding(symbol,start):
    p=DATA/f'{symbol}_funding.csv'
    if p.exists():
        x=pd.read_csv(p); x['time']=pd.to_datetime(x['time'],utc=True,format='mixed'); return x.set_index('time')
    out=[]; cursor=int(start.timestamp()*1000); end=int((END+pd.Timedelta(days=1)).timestamp()*1000)
    while cursor<end:
        j=requests.get('https://fapi.binance.com/fapi/v1/fundingRate',params={'symbol':symbol,'startTime':cursor,'endTime':end,'limit':FUNDING_LIMIT},timeout=30).json()
        if not j: break
        out.extend(j); cursor=j[-1]['fundingTime']+1
        if len(j)<FUNDING_LIMIT: break
    x=pd.DataFrame(out); x['time']=pd.to_datetime(x.fundingTime,unit='ms',utc=True); x['fundingRate']=pd.to_numeric(x.fundingRate); x=x[['time','fundingRate']].set_index('time'); x.to_csv(p); return x

def month_dates(cal):
    first=cal.min().replace(day=1); last=cal.max().replace(day=1)
    sched=pd.date_range(first,last,freq='MS',tz='UTC')+pd.Timedelta(days=26)
    return {next((d for d in cal if d>=s),None):s for s in sched if next((d for d in cal if d>=s),None) is not None}

def run(name,symbols,weights,start):
    prices={s:get_klines(s,start) for s in symbols}; funding={s:get_funding(s,start) for s in symbols}; cal=prices[symbols[0]].index
    for s in symbols: cal=cal.intersection(prices[s].index)
    cal=cal[(cal>=start)&(cal<=END)]; due=month_dates(cal); state={s:{'qty':0.,'entry':0.,'margin':0.,'liquidations':0} for s in symbols}; rows=[]; trades=[]; funding_cash=0.; slippage_cash=0.; prev=0.; tw=1.; peak=1.
    for dt in cal:
        for s in symbols:
            p=prices[s]; pos=p.index.get_loc(dt); sma=p.close.rolling(150).mean().iloc[pos-1] if pos>0 else np.nan; bull=bool(pos>0 and pd.notna(sma) and p.close.iloc[pos-1]>sma)
            z=state[s]
            if dt in due: z['margin']+=100*weights[s]
            # Funding is applied once per daily bar using the average of the
            # real 8-hour funding prints that occurred during that UTC day.
            fr=funding[s].loc[(funding[s].index>=dt)&(funding[s].index<dt+pd.Timedelta(days=1))].fundingRate
            if z['qty']>0 and len(fr):
                funding_flow=z['qty']*float(p.close.loc[dt])*fr.sum(); z['margin']-=funding_flow; funding_cash+=funding_flow
            if z['qty']>0 and z['margin']+z['qty']*(float(p.low.loc[dt])-z['entry']) <= z['qty']*float(p.low.loc[dt])*MMR:
                liq=(z['qty']*z['entry']-z['margin'])/(z['qty']*(1-MMR)); liq=max(0.,liq); trades.append([dt,s,'LIQUIDATION',z['qty'],liq,0.,0.,'liquidation']); z['qty']=0.; z['entry']=0.; z['margin']=0.; z['liquidations']+=1
            if bull and z['margin']>0 and z['qty']==0:
                px=float(p.open.loc[dt])*(1+SLIP); margin=z['margin']; notional=margin*LEV; fee=notional*FEE; q=notional/px; z['margin']-=fee; z['qty']=q; z['entry']=px; slippage_cash+=q*float(p.open.loc[dt])*SLIP; trades.append([dt,s,'OPEN',q,px,notional,fee,'sma'])
            elif bull and z['margin']>0 and z['qty']>0 and dt in due:
                px=float(p.open.loc[dt])*(1+SLIP); margin=z['margin']; notional=margin*LEV; fee=notional*FEE; q=notional/px; z['margin']-=fee; old=z['qty']; z['qty']+=q; z['entry']=(old*z['entry']+q*px)/z['qty']; slippage_cash+=q*float(p.open.loc[dt])*SLIP; trades.append([dt,s,'ADD',q,px,notional,fee,'sma'])
            elif not bull and z['qty']>0:
                px=float(p.open.loc[dt])*(1-SLIP); pnl=z['qty']*(px-z['entry']); notional=z['qty']*px; fee=notional*FEE; z['margin']+=pnl-fee; slippage_cash+=z['qty']*float(p.open.loc[dt])*SLIP; trades.append([dt,s,'CLOSE',z['qty'],px,notional,fee,'sma']); z['qty']=0.; z['entry']=0.
        equity=sum(state[s]['margin']+state[s]['qty']*(prices[s].close.loc[dt]-state[s]['entry']) for s in symbols); dep=100. if dt in due else 0.; ret=(equity-dep)/prev-1 if prev>0 else 0.; tw*=1+ret; peak=max(peak,tw); rows.append([dt,equity,dep,tw,tw/peak-1,sum(state[s]['margin'] for s in symbols)]); prev=equity
    d=pd.DataFrame(rows,columns=['date','equity','deposit','twr','drawdown','margin']).set_index('date'); t=pd.DataFrame(trades,columns=['date','asset','side','qty','price','notional','fee','kind']); m={'portfolio':name,'start':start.date(),'end':cal[-1].date(),'contributions':d.deposit.sum(),'final_value':d.equity.iloc[-1],'return_pct':d.equity.iloc[-1]/d.deposit.sum()-1,'max_drawdown':d.drawdown.min(),'fees':t.fee.sum(),'slippage':slippage_cash,'funding_cashflow':funding_cash,'trades':len(t),'liquidations':int(t.side.eq('LIQUIDATION').sum()),'btc_eth_note':'5x isolated; funding aggregated from 8-hour prints to daily bars'}
    return d,t,m

def main():
    rows=[]
    specs=[('BTC_ETH_5x_SMA150',['BTCUSDT','ETHUSDT'],{'BTCUSDT':.6,'ETHUSDT':.4},START),('BTC_SOL_INJ_5x_SMA150',['BTCUSDT','SOLUSDT','INJUSDT'],{'BTCUSDT':.5,'SOLUSDT':.3,'INJUSDT':.2},pd.Timestamp('2022-08-17',tz='UTC'))]
    for name,symbols,w,start in specs:
        d,t,m=run(name,symbols,w,start); d.to_csv(RES/f'futures_equity_{name}.csv'); t.to_csv(RES/f'futures_trades_{name}.csv',index=False); rows.append(m)
    out=pd.DataFrame(rows); out.to_csv(RES/'futures_leverage_summary.csv',index=False); (RES/'futures_leverage_metadata.json').write_text(__import__('json').dumps({'generated_utc':datetime.now(timezone.utc).isoformat(),'leverage':LEV,'fee':FEE,'slippage':SLIP,'maintenance_margin_rate':MMR,'funding_source':'Binance USD-M futures fundingRate endpoint, aggregated by UTC day','liquidation':'simplified isolated-margin liquidation when low-price equity falls below maintenance margin','inj_contract_start':'2022-08-17; BTC/SOL/INJ cannot be tested from 2021 without a spot proxy'},indent=2)); print(out.to_string(index=False))
if __name__=='__main__': main()
