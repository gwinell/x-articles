from pathlib import Path
import json, shutil
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import yfinance as yf
import requests
from io import StringIO
from scipy.optimize import brentq

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'; RESULTS=ROOT/'results'; FIG=RESULTS/'figures'
DATA.mkdir(exist_ok=True); RESULTS.mkdir(exist_ok=True); FIG.mkdir(exist_ok=True)
START=pd.Timestamp('2021-09-27',tz='UTC'); REQUESTED_END=pd.Timestamp('2026-09-26',tz='UTC'); WARM=pd.Timestamp('2020-01-01',tz='UTC')
FUNDING=100.; FEE_STOCK=.0; SLIP_STOCK=.0005; FEE_CRYPTO=.001; SLIP_CRYPTO=.0005
TICKERS=['VOO','VTI','VT','AAPL','MSFT','NVDA','GOOGL']
PORTFOLIOS={
 'A_Crypto_DCA':{'BTC':.6,'ETH':.4}, 'B_S&P500_VOO':{'VOO':1.}, 'C_Total_US_VTI':{'VTI':1.}, 'D_Global_VT':{'VT':1.},
 'E_VOO_BTC':{'VOO':.8,'BTC':.2}, 'F_VOO_BTC_ETH':{'VOO':.6,'BTC':.2,'ETH':.2}, 'G_VT_BTC':{'VT':.8,'BTC':.2},
 'AAPL_only':{'AAPL':1.}, 'MSFT_only':{'MSFT':1.}, 'NVDA_only':{'NVDA':1.}, 'GOOGL_only':{'GOOGL':1.}
}

def load_crypto(asset):
    p=ROOT.parent/'data'/f'{asset.lower()}usdt_1d.csv'; x=pd.read_csv(p,parse_dates=['open_time']).set_index('open_time')
    return pd.DataFrame({'open':x.open,'close':x.close,'dividends':0.,'splits':0.},index=x.index)

def load_stock(ticker):
    p=DATA/f'{ticker}_daily.csv'
    if not p.exists():
        # Yahoo was unavailable from this environment, so use Nasdaq's public
        # historical endpoint for OHLC and dividend records.  ETF distributions
        # are sourced from DividendSmart's split-adjusted history pages.
        kind='etf' if ticker in {'VOO','VTI','VT'} else 'stocks'
        h=requests.get(f'https://api.nasdaq.com/api/quote/{ticker}/historical',params={'assetclass':kind,'fromdate':'2020-01-01','todate':REQUESTED_END.strftime('%Y-%m-%d'),'limit':5000},headers={'User-Agent':'Mozilla/5.0'},timeout=30)
        h.raise_for_status(); rows=h.json()['data']['tradesTable']['rows']
        x=pd.DataFrame(rows).rename(columns={'date':'date','open':'open','close':'close'})[['date','open','close']]
        for c in ['open','close']:
            x[c]=pd.to_numeric(x[c].astype(str).str.replace(',','',regex=False).str.replace('$','',regex=False),errors='coerce')
        x['date']=pd.to_datetime(x.date,format='%m/%d/%Y',utc=True); x=x.set_index('date').sort_index()
        x['dividends']=0.; x['splits']=0.
        if kind=='stocks':
            j=requests.get(f'https://api.nasdaq.com/api/quote/{ticker}/dividends',params={'assetclass':'stocks','limit':5000},headers={'User-Agent':'Mozilla/5.0'},timeout=30).json()
            rows=j.get('data',{}).get('dividends',{}).get('rows') or []
            for r in rows:
                if r.get('type')!='Cash': continue
                d=pd.Timestamp(r['exOrEffDate'],tz='UTC')
                if d in x.index: x.loc[d,'dividends']=float(str(r['amount']).replace('$','').replace(',',''))
        else:
            htm=requests.get(f'https://dividendsmart.com/{ticker.lower()}-dividend-history',headers={'User-Agent':'Mozilla/5.0'},timeout=30).text
            tables=pd.read_html(StringIO(htm)); div=tables[-1]
            for _,r in div.iterrows():
                d=pd.to_datetime(r['Ex-dividend date'],format='%b %d, %Y',utc=True)
                if d in x.index: x.loc[d,'dividends']=float(str(r['Amount / share']).replace('$','').replace(',',''))
        x.to_csv(p)
    x=pd.read_csv(p,parse_dates=['date']).set_index('date')
    return x.rename(columns={'Open':'open','Close':'close','Dividends':'dividends','Stock Splits':'splits'})[['open','close','dividends','splits']]

def xirr(cfs):
    t0=cfs[0][0]
    def f(r): return sum(v/(1+r)**((d-t0).days/365.) for d,v in cfs)
    try:return brentq(f,-.9999,100.)
    except ValueError:return np.nan

def trading_calendar(data,start_date=START,end_date=REQUESTED_END):
    stock_idx=data['VOO'].index
    last=min(end_date,stock_idx.max(),data['BTC'].index.max(),data['ETH'].index.max())
    return stock_idx[(stock_idx>=start_date)&(stock_idx<=last)],last

def execution_deposit_dates(cal,start_date=START,end_date=REQUESTED_END):
    first=pd.Timestamp(start_date).replace(day=1); last_month=pd.Timestamp(end_date).replace(day=1)-pd.offsets.MonthBegin(0)
    scheduled=pd.date_range(first,last_month,freq='MS',tz='UTC')+pd.Timedelta(days=26)
    return [(d,next((x for x in cal if x>=d),None)) for d in scheduled if next((x for x in cal if x>=d),None) is not None]

def prev_signal(asset,dt,data,window):
    x=data[asset]; idx=x.index; pos=idx.get_loc(dt); 
    if pos==0:return False
    p=idx[pos-1]; sma=x.close.rolling(window).mean().loc[p]
    return bool(pd.notna(sma) and x.close.loc[p]>sma)

def trade_buy(dt,a,amount,data,units,cash,deals):
    price=float(data[a].loc[dt,'open']); slip=SLIP_CRYPTO if a in ('BTC','ETH') else SLIP_STOCK; fee=FEE_CRYPTO if a in ('BTC','ETH') else FEE_STOCK
    ep=price*(1+slip); q=amount/(ep*(1+fee)); notional=q*ep; f=notional*fee; cash-=notional+f; units[a]+=q; deals.append([dt,a,'BUY',q,ep,notional,f,q*price*slip,'trade']); return cash

def trade_sell(dt,a,q,data,units,cash,deals):
    price=float(data[a].loc[dt,'open']); slip=SLIP_CRYPTO if a in ('BTC','ETH') else SLIP_STOCK; fee=FEE_CRYPTO if a in ('BTC','ETH') else FEE_STOCK
    ep=price*(1-slip); notional=q*ep; f=notional*fee; cash+=notional-f; units[a]-=q; deals.append([dt,a,'SELL',q,ep,notional,f,q*price*slip,'trade']); return cash

def simulate(name,weights,data,rebalance=False,sma_window=None,start_date=START,end_date=REQUESTED_END):
    cal,last=trading_calendar(data,start_date,end_date); scheduled=execution_deposit_dates(cal,start_date,end_date); due={x[1]:x[0] for x in scheduled}; units={a:0. for a in weights}; cash=0.; deals=[]; dividends=[]; daily=[]; contributions=[]; prev=0.; tw=1.; peak=1.; next_reb=[]
    for y in range(2022,2027):
        d=pd.Timestamp(f'{y}-12-31',tz='UTC'); next_reb.append(next((x for x in cal if x>=d),None))
    is_portfolio_sma=sma_window is not None and len(weights)>1
    synthetic=[]
    if is_portfolio_sma:
        # Equal-date benchmark series for crypto portfolio signal only.
        base_btc=data['BTC'].index[data['BTC'].index>=start_date][0]; base_eth=data['ETH'].index[data['ETH'].index>=start_date][0]
        for dt in data['BTC'].index.intersection(data['ETH'].index): synthetic.append((dt,.6*data['BTC'].close.loc[dt]/data['BTC'].close.loc[base_btc]+.4*data['ETH'].close.loc[dt]/data['ETH'].close.loc[base_eth]))
        syn=pd.Series(dict(synthetic)).sort_index(); syn_sma=syn.rolling(sma_window).mean()
    else:syn=syn_sma=None
    for dt in cal:
        # Cash dividends are reinvested at the close without reusing adjusted close.
        for a in weights:
            div=float(data[a].loc[dt,'dividends']) if dt in data[a].index else 0.
            if div>0 and units[a]>0:
                amount=units[a]*div; units[a]+=amount/float(data[a].loc[dt,'close']); dividends.append([dt,a,units[a]*0+amount,amount/float(data[a].loc[dt,'close'])])
        if dt in due:
            cash+=FUNDING; contributions.append((due[dt],FUNDING))
            for a,w in weights.items():
                bull=True
                if sma_window and not is_portfolio_sma: bull=prev_signal(a,dt,data,sma_window)
                if bull: cash=trade_buy(dt,a,FUNDING*w,data,units,cash,deals)
        if sma_window:
            if is_portfolio_sma:
                pos=syn.index.get_loc(dt) if dt in syn.index else None; bull=bool(pos is not None and pos>0 and pd.notna(syn_sma.iloc[pos-1]) and syn.iloc[pos-1]>syn_sma.iloc[pos-1])
                if not bull and sum(units.values())>0:
                    for a in list(weights): cash=trade_sell(dt,a,units[a],data,units,cash,deals)
                elif bull and cash>0:
                    for a,w in weights.items(): cash=trade_buy(dt,a,cash*w,data,units,cash,deals)
            else:
                for a in weights:
                    bull=prev_signal(a,dt,data,sma_window)
                    if not bull and units[a]>0: cash=trade_sell(dt,a,units[a],data,units,cash,deals)
                    elif bull and units[a]==0 and cash>0: cash=trade_buy(dt,a,cash,data,units,cash,deals)
        if rebalance and dt in next_reb:
            # Rebalance at the session open.  The target must not use the
            # close that is only known after the order would have filled.
            total=cash+sum(units[a]*float(data[a].loc[dt,'open']) for a in weights)
            for a,w in weights.items():
                value=units[a]*float(data[a].loc[dt,'open']); target=total*w
                if value>target: cash=trade_sell(dt,a,min(units[a],(value-target)/float(data[a].loc[dt,'open'])),data,units,cash,deals)
            for a,w in weights.items():
                value=units[a]*float(data[a].loc[dt,'open']); need=max(0,total*w-value)
                if need>0 and cash>0: cash=trade_buy(dt,a,min(need,cash),data,units,cash,deals)
        equity=cash+sum(units[a]*float(data[a].loc[dt,'close']) for a in weights); dep=FUNDING if dt in due else 0.; ret=(equity-dep)/prev-1 if prev>0 else 0.; tw*=1+ret; peak=max(peak,tw)
        daily.append([dt,equity,dep,tw,tw/peak-1,cash,*[units[a] for a in weights]]); prev=equity
    cols=['date','equity','deposit','twr','drawdown','cash']+[f'{a}_units' for a in weights]; d=pd.DataFrame(daily,columns=cols).set_index('date'); t=pd.DataFrame(deals,columns=['date','asset','side','units','price','notional','fee','slippage','kind']); dv=pd.DataFrame(dividends,columns=['date','asset','cash_dividend','reinvested_units']); cfs=[(x,-FUNDING) for x,_ in scheduled]+[(last,d.equity.iloc[-1])]
    m={'portfolio':name,'contributions':d.deposit.sum(),'final_value':d.equity.iloc[-1],'final_cash':d.cash.iloc[-1],'profit':d.equity.iloc[-1]-d.deposit.sum(),'return_pct':d.equity.iloc[-1]/d.deposit.sum()-1,'xirr':xirr(cfs),'max_drawdown':d.drawdown.min(),'fees':t.fee.sum(),'slippage':t.slippage.sum(),'trades':len(t),'dividends':dv.cash_dividend.sum() if len(dv) else 0.,'last_date':last.date(),**{f'{a}_final_units':d[f'{a}_units'].iloc[-1] for a in weights}}
    return d,t,dv,m

def main():
    data={'BTC':load_crypto('BTC'),'ETH':load_crypto('ETH')}; data.update({x:load_stock(x) for x in TICKERS}); cal,last=trading_calendar(data)
    rows=[]
    for name,w in PORTFOLIOS.items():
        for reb in [False,True] if len(w)>1 else [False]:
            label=name+('_annual_rebalance' if reb else '')
            d,t,dv,m=simulate(label,w,data,rebalance=reb); d.to_csv(RESULTS/f'equity_{label}.csv'); t.to_csv(RESULTS/f'trades_{label}.csv',index=False); dv.to_csv(RESULTS/f'dividends_{label}.csv',index=False); rows.append(m)
    # SMA tests requested for VOO, VTI and crypto portfolio.
    for a in ['B_S&P500_VOO','C_Total_US_VTI']:
        w=PORTFOLIOS[a]
        for window in [150,200]:
            label=a+f'_SMA{window}'; d,t,dv,m=simulate(label,w,data,sma_window=window); d.to_csv(RESULTS/f'equity_{label}.csv'); t.to_csv(RESULTS/f'trades_{label}.csv',index=False); dv.to_csv(RESULTS/f'dividends_{label}.csv',index=False); rows.append(m)
    w=PORTFOLIOS['A_Crypto_DCA']
    for window in [150,200]:
        label=f'A_Crypto_DCA_SMA{window}'; d,t,dv,m=simulate(label,w,data,sma_window=window); d.to_csv(RESULTS/f'equity_{label}.csv'); t.to_csv(RESULTS/f'trades_{label}.csv',index=False); dv.to_csv(RESULTS/f'dividends_{label}.csv',index=False); rows.append(m)
    # Start-date robustness: same contribution rule, common end date, and no
    # parameter selection from these comparisons.  Absolute values are not
    # compared across windows without reporting their different contribution
    # counts; the CSV is primarily for return/drawdown sensitivity.
    period_rows=[]
    for tag,sd in {'2020':pd.Timestamp('2020-09-27',tz='UTC'),'2021':START,'2022':pd.Timestamp('2022-09-27',tz='UTC')}.items():
        for key in ['A_Crypto_DCA','B_S&P500_VOO','F_VOO_BTC_ETH','G_VT_BTC']:
            label=f'{key}_start{tag}'; d,t,dv,m=simulate(label,PORTFOLIOS[key],data,start_date=sd); d.to_csv(RESULTS/f'equity_{label}.csv'); t.to_csv(RESULTS/f'trades_{label}.csv',index=False); dv.to_csv(RESULTS/f'dividends_{label}.csv',index=False); period_rows.append(m)
    pd.DataFrame(period_rows).to_csv(RESULTS/'period_start_comparison.csv',index=False)
    # Explicit cost sensitivity for representative portfolios.
    global FEE_STOCK, SLIP_STOCK, FEE_CRYPTO, SLIP_CRYPTO
    cost_rows=[]; base=(FEE_STOCK,SLIP_STOCK,FEE_CRYPTO,SLIP_CRYPTO)
    for scen,vals in {'zero_costs':(0.,0.,0.,0.),'base':base,'double_costs':(0.,.001,.002,.001)}.items():
        FEE_STOCK,SLIP_STOCK,FEE_CRYPTO,SLIP_CRYPTO=vals
        for key in ['A_Crypto_DCA','B_S&P500_VOO','E_VOO_BTC','F_VOO_BTC_ETH','G_VT_BTC']:
            _,_,_,m=simulate(f'{key}_{scen}',PORTFOLIOS[key],data)
            cost_rows.append({'scenario':scen,'portfolio':key,**m})
    FEE_STOCK,SLIP_STOCK,FEE_CRYPTO,SLIP_CRYPTO=base
    pd.DataFrame(cost_rows).to_csv(RESULTS/'cost_sensitivity.csv',index=False)
    out=pd.DataFrame(rows); out.to_csv(RESULTS/'market_comparison_summary.csv',index=False)
    meta={'generated_utc':datetime.now(timezone.utc).isoformat(),'requested_start':str(START),'requested_end':str(REQUESTED_END),'common_last_date':str(last),'source_stocks':'Nasdaq public historical JSON endpoint; Yahoo Finance/yfinance timed out in this environment','source_etf_distributions':'DividendSmart split-adjusted historical distribution pages for VOO, VTI and VT','source_crypto':'existing Binance Spot CSV files from parent research','stock_total_return':'raw Close + explicit dividend cash reinvestment; adjusted close not used','stock_fee':FEE_STOCK,'stock_slippage':SLIP_STOCK,'crypto_fee':FEE_CRYPTO,'crypto_slippage':SLIP_CRYPTO,'fractional_shares':True,'dividend_reinvestment':'same asset at close on ex-dividend date','limitations':'US market timestamps are not identical to UTC crypto daily close; no taxes, funding, borrow, or jurisdiction-specific fees'}
    (RESULTS/'market_metadata.json').write_text(json.dumps(meta,indent=2,default=str))
    print(out[['portfolio','final_value','profit','return_pct','xirr','max_drawdown','trades','fees','slippage','dividends']].to_string(index=False)); print('common_last_date',last)

if __name__=='__main__':main()
