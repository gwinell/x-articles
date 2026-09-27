from __future__ import annotations
import json, math, time
from pathlib import Path
from datetime import datetime, timezone
import requests
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import brentq

ROOT = Path(__file__).resolve().parent
DATA, OUT = ROOT/'data', ROOT/'results'
FIG = OUT/'figures'
START, END = pd.Timestamp('2021-09-27', tz='UTC'), pd.Timestamp('2026-09-26', tz='UTC')
WARMUP = pd.Timestamp('2020-01-01', tz='UTC')
SYMBOLS = {'BTC':'BTCUSDT','ETH':'ETHUSDT'}
DEPOSIT_DATES = pd.date_range('2021-09-01', '2026-08-01', freq='MS', tz='UTC') + pd.Timedelta(days=26)
DEPOSIT_DATES = pd.DatetimeIndex([d for d in DEPOSIT_DATES if d <= END])
FUNDING = {'BTC':60.0,'ETH':40.0}

def fetch_symbol(symbol, start=WARMUP, end=END + pd.Timedelta(days=1)):
    path=DATA/f'{symbol.lower()}usdt_1d.csv'
    if path.exists(): return pd.read_csv(path, parse_dates=['open_time'], index_col='open_time')
    DATA.mkdir(exist_ok=True)
    url='https://api.binance.com/api/v3/klines'; rows=[]; cur=int(start.timestamp()*1000); stop=int(end.timestamp()*1000)
    while cur < stop:
        p={'symbol':SYMBOLS[symbol],'interval':'1d','startTime':cur,'endTime':stop-1,'limit':1000}
        r=requests.get(url, params=p, timeout=30); r.raise_for_status(); batch=r.json()
        if not batch: break
        rows += batch; nxt=batch[-1][0]+86400000
        if nxt <= cur: break
        cur=nxt; time.sleep(0.05)
    cols=['open_time','open','high','low','close','volume','close_time','quote_volume','trades','tb_base','tb_quote','ignore']
    df=pd.DataFrame(rows,columns=cols)
    df['open_time']=pd.to_datetime(df.open_time,unit='ms',utc=True)
    for c in ['open','high','low','close','volume']: df[c]=pd.to_numeric(df[c])
    df=df.set_index('open_time')[['open','high','low','close','volume']].sort_index()
    df=df[~df.index.duplicated(keep='first')]
    df.to_csv(path)
    return df

def indicators(df):
    x=df.copy(); close=x.close
    x['sma50']=close.rolling(50).mean(); x['sma200']=close.rolling(200).mean()
    x['mom90']=close.shift(90)
    x['don_high20']=x.high.shift(1).rolling(20).max(); x['don_low10']=x.low.shift(1).rolling(10).min()
    delta=close.diff(); gain=delta.clip(lower=0).ewm(alpha=1/14,adjust=False,min_periods=14).mean(); loss=(-delta.clip(upper=0)).ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    x['rsi14']=100-100/(1+gain/loss.replace(0,np.nan)); x['rsi14']=x['rsi14'].fillna(100)
    x['bbmid']=close.rolling(20).mean(); x['bbstd']=close.rolling(20).std(ddof=0); x['bblow']=x.bbmid-2*x.bbstd
    return x

def state_series(x, strat):
    state=[]; holding=False
    for _,r in x.iterrows():
        if strat=='SMA200':
            if pd.notna(r.sma200): holding=bool(r.close>r.sma200)
        elif strat=='SMA50_200':
            if pd.notna(r.sma200): holding=bool(r.sma50>r.sma200)
        elif strat=='Momentum90':
            if pd.notna(r.mom90): holding=bool(r.close>r.mom90)
        elif strat=='Donchian20_10':
            if pd.notna(r.don_high20) and r.close>r.don_high20: holding=True
            elif pd.notna(r.don_low10) and r.close<r.don_low10: holding=False
        elif strat=='RSI14':
            if r.rsi14<30: holding=True
            elif r.rsi14>70: holding=False
        elif strat=='Bollinger20_2':
            if pd.notna(r.bblow) and r.close<r.bblow: holding=True
            elif pd.notna(r.bbmid) and r.close>r.bbmid: holding=False
        state.append(holding)
    return pd.Series(state,index=x.index,dtype=bool)

def xirr(cfs):
    if len(cfs)<2: return np.nan
    t0=cfs[0][0]
    def f(rate): return sum(v/(1+rate)**(((d-t0).days)/365.0) for d,v in cfs)
    try: return brentq(f,-0.9999,100.0)
    except ValueError: return np.nan

def simulate(asset, x, strat, fee=0.001, slip=0.0005, annual_rebalance=False):
    x=x.loc[:END].copy(); research=x.loc[START:END]; state=state_series(x,strat) if strat not in ('DCA','DCA_rebalanced') else pd.Series(True,index=x.index)
    cash=0.; units=0.; position=False; deals=[]; daily=[]; cf=[]; prev_equity=0.; tw=1.0; peak=1.0
    for i,(dt,r) in enumerate(research.iterrows()):
        dep=FUNDING[asset] if dt in DEPOSIT_DATES else 0.0; cash += dep; cf.append((dt, -dep)) if dep else None
        target=bool(state.loc[x.index[x.index.get_loc(dt)-1]]) if x.index.get_loc(dt)>0 else False
        if strat in ('DCA','DCA_rebalanced') and dep:
            target=True
        if target and not position:
            exec_price=r.open*(1+slip); qty=cash/(exec_price*(1+fee)); notional=qty*exec_price; total=notional*(1+fee); cash-=total; units+=qty; position=True
            deals.append([dt,'BUY',qty,exec_price,notional,notional*fee,qty*r.open*slip])
        elif not target and position:
            exec_price=r.open*(1-slip); notional=units*exec_price; proceeds=notional*(1-fee); cash+=proceeds
            deals.append([dt,'SELL',units,exec_price,notional,notional*fee,units*r.open*slip]); units=0.; position=False
        elif target and position and dep:
            exec_price=r.open*(1+slip); qty=cash/(exec_price*(1+fee)); notional=qty*exec_price; total=notional*(1+fee); cash-=total; units+=qty
            deals.append([dt,'BUY',qty,exec_price,notional,notional*fee,qty*r.open*slip])
        if annual_rebalance and dt.month==12 and dt.day==31:
            equity=cash+units*r.close; target_value=equity*(0.6 if asset=='BTC' else 0.4) # handled across assets only in separate not used
        equity=cash+units*r.close; net=equity-dep
        ret=(net/prev_equity-1) if prev_equity>0 else 0.0; tw*=1+ret; peak=max(peak,tw)
        daily.append([dt,cash,units,r.close,equity,dep,ret,tw,tw/peak-1]); prev_equity=equity
    if research.empty: raise RuntimeError('No research rows')
    final=daily[-1][4]; cf.append((research.index[-1],final))
    d=pd.DataFrame(daily,columns=['date','cash','units','price','equity','deposit','return','twr_index','drawdown']).set_index('date')
    tr=pd.DataFrame(deals,columns=['date','side','units','price','gross_value','fee','slippage'])
    buy_sell=len(tr); time_market=float((d.units>0).mean());
    return d,tr,{'asset':asset,'strategy':strat,'contributions':float(d.deposit.sum()),'final_value':final,'cash':d.cash.iloc[-1],'units':d.units.iloc[-1],'profit':final-d.deposit.sum(),'return_pct':final/d.deposit.sum()-1,'xirr':xirr(cf),'max_drawdown':d.drawdown.min(),'trades':buy_sell,'fees':tr.fee.sum() if len(tr) else 0.,'slippage':tr.slippage.sum() if len(tr) else 0.,'market_time':time_market,'usdt_time':1-time_market}

def simulate_dca_variants(data, kind, fee=0.001, slip=0.0005):
    """Joint BTC/ETH simulation for monthly rebalance and SMA200 exits."""
    idx=data['BTC'].loc[START:END].index; cash={'BTC':0.,'ETH':0.}; units={'BTC':0.,'ETH':0.}; deals=[]; daily=[]; prev=0.; tw=1.; peak=1.
    for i,dt in enumerate(idx):
        prices={a:float(data[a].loc[dt,'open']) for a in ['BTC','ETH']}; closes={a:float(data[a].loc[dt,'close']) for a in ['BTC','ETH']}
        dep={'BTC':FUNDING['BTC'] if dt in DEPOSIT_DATES else 0.,'ETH':FUNDING['ETH'] if dt in DEPOSIT_DATES else 0.}
        for a in cash: cash[a]+=dep[a]
        prevsig={}
        for a in ['BTC','ETH']:
            pos=data[a].index.get_loc(dt); prevdt=data[a].index[pos-1] if pos>0 else None
            prevsig[a]=bool(data[a].loc[prevdt,'close']>data[a].loc[prevdt,'sma200']) if prevdt is not None and pd.notna(data[a].loc[prevdt,'sma200']) else False
        # Exit each asset independently when its own SMA200 regime turns bearish.
        if kind in ('DCA_SMA200_EXIT','DCA_REBALANCE_SMA200_EXIT'):
            for a in ['BTC','ETH']:
                if not prevsig[a] and units[a]>0:
                    ep=prices[a]*(1-slip); notional=units[a]*ep; f=notional*fee; cash[a]+=notional-f; deals.append([dt,a,'SELL',units[a],ep,notional,f,units[a]*prices[a]*slip]); units[a]=0.
        if kind=='DCA_SMA200_EXIT':
            for a in ['BTC','ETH']:
                if prevsig[a] and cash[a]>0:
                    ep=prices[a]*(1+slip); q=cash[a]/(ep*(1+fee)); n=q*ep; f=n*fee; cash[a]-=n+f; units[a]+=q; deals.append([dt,a,'BUY',q,ep,n,f,q*prices[a]*slip])
        if dt in DEPOSIT_DATES and kind in ('DCA_REBALANCE','DCA_REBALANCE_SMA200_EXIT'):
            active={a:(prevsig[a] if kind=='DCA_REBALANCE_SMA200_EXIT' else True) for a in ['BTC','ETH']}
            # Sell first; target weights are 60/40 among active assets, with bearish assets at zero.
            total=sum(cash[a]+units[a]*prices[a] for a in ['BTC','ETH']); weights={'BTC':.6,'ETH':.4}
            targets={a:(total*weights[a] if active[a] else 0.) for a in ['BTC','ETH']}
            for a in ['BTC','ETH']:
                value=units[a]*prices[a]
                if value>targets[a] and units[a]>0:
                    q=(value-targets[a])/prices[a]; q=min(q,units[a]); ep=prices[a]*(1-slip); n=q*ep; f=n*fee; cash[a]+=n-f; units[a]-=q; deals.append([dt,a,'SELL',q,ep,n,f,q*prices[a]*slip])
            # Rebalance purchases can use proceeds from the other leg, as standard portfolio rebalancing.
            pool=sum(cash.values())
            for a in ['BTC','ETH']:
                value=units[a]*prices[a]
                need=max(0.,targets[a]-value)
                if need>0 and pool>0:
                    ep=prices[a]*(1+slip); q=min(need/(ep*(1+fee)),pool/(ep*(1+fee))); n=q*ep; f=n*fee; pool-=n+f; units[a]+=q; deals.append([dt,a,'BUY',q,ep,n,f,q*prices[a]*slip])
            cash={'BTC':pool,'ETH':0.} # common USDT pool created by the rebalance
        equity=sum(cash[a]+units[a]*closes[a] for a in ['BTC','ETH']); contribution=sum(dep.values()); ret=(equity-contribution)/prev-1 if prev>0 else 0.; tw*=1+ret; peak=max(peak,tw)
        daily.append([dt,equity,contribution,tw,tw/peak-1,cash['BTC'],cash['ETH'],units['BTC'],units['ETH']]); prev=equity
    d=pd.DataFrame(daily,columns=['date','equity','deposit','twr_index','drawdown','cash_btc','cash_eth','btc_units','eth_units']).set_index('date'); tr=pd.DataFrame(deals,columns=['date','asset','side','units','price','notional','fee','slippage']); final=d.equity.iloc[-1]; cfs=[(x,-100.) for x in DEPOSIT_DATES]+[(d.index[-1],final)]
    m={'asset':'TOTAL','strategy':kind,'contributions':d.deposit.sum(),'final_value':final,'cash':d.cash_btc.iloc[-1]+d.cash_eth.iloc[-1],'units':np.nan,'profit':final-d.deposit.sum(),'return_pct':final/d.deposit.sum()-1,'xirr':xirr(cfs),'max_drawdown':d.drawdown.min(),'trades':len(tr),'fees':tr.fee.sum(),'slippage':tr.slippage.sum(),'market_time':np.nan,'usdt_time':np.nan}
    return d,tr,m

def run_all():
    DATA.mkdir(exist_ok=True); OUT.mkdir(exist_ok=True); FIG.mkdir(exist_ok=True)
    raw={a:fetch_symbol(a) for a in SYMBOLS}; data={a:indicators(v) for a,v in raw.items()}
    strategies=['DCA','SMA200','SMA50_200','Momentum90','Donchian20_10','RSI14','Bollinger20_2']
    rows=[]; daily_all=[]
    for s in strategies:
        total=None
        for a in ['BTC','ETH']:
            d,t,m=simulate(a,data[a],s); rows.append(m); t.to_csv(OUT/f'trades_{s}_{a}.csv',index=False); d.to_csv(OUT/f'equity_{s}_{a}.csv'); d2=d[['equity','deposit','drawdown']].rename(columns={'equity':f'{s}_{a}_equity','deposit':f'{s}_{a}_deposit','drawdown':f'{s}_{a}_drawdown'}); daily_all.append(d2)
        # aggregate exact portfolio metrics from daily subportfolios
        b=pd.read_csv(OUT/f'equity_{s}_BTC.csv',parse_dates=['date'],index_col='date'); e=pd.read_csv(OUT/f'equity_{s}_ETH.csv',parse_dates=['date'],index_col='date'); q=pd.DataFrame(index=b.index); q['equity']=b.equity+e.equity; q['deposit']=b.deposit+e.deposit; q['return']=(q.equity-q.deposit)/q.equity.shift(1)-1; q.iloc[0,q.columns.get_loc('return')]=0; q['twr']=(1+q['return']).cumprod(); q['drawdown']=q.twr/q.twr.cummax()-1; q.to_csv(OUT/f'equity_{s}_TOTAL.csv');
        cfs=[(d,-100.) for d in DEPOSIT_DATES]+[(q.index[-1],q.equity.iloc[-1])]; trb=pd.read_csv(OUT/f'trades_{s}_BTC.csv'); tre=pd.read_csv(OUT/f'trades_{s}_ETH.csv');
        rows.append({'asset':'TOTAL','strategy':s,'contributions':q.deposit.sum(),'final_value':q.equity.iloc[-1],'cash':b.cash.iloc[-1]+e.cash.iloc[-1],'units':np.nan,'profit':q.equity.iloc[-1]-q.deposit.sum(),'return_pct':q.equity.iloc[-1]/q.deposit.sum()-1,'xirr':xirr(cfs),'max_drawdown':q.drawdown.min(),'trades':len(trb)+len(tre),'fees':trb.fee.sum()+tre.fee.sum(),'slippage':trb.slippage.sum()+tre.slippage.sum(),'market_time':np.nan,'usdt_time':np.nan})
    variant_names=['DCA_REBALANCE','DCA_SMA200_EXIT','DCA_REBALANCE_SMA200_EXIT']
    for s in variant_names:
        d,t,m=simulate_dca_variants(data,s); d.to_csv(OUT/f'equity_{s}_TOTAL.csv'); t.to_csv(OUT/f'trades_{s}_TOTAL.csv',index=False); rows.append(m)
    res=pd.DataFrame(rows); res.to_csv(OUT/'summary.csv',index=False)
    # plots
    plt.figure(figsize=(13,7))
    for s in strategies+variant_names: plt.plot(pd.read_csv(OUT/f'equity_{s}_TOTAL.csv',parse_dates=['date']).set_index('date').equity,label=s)
    q=pd.read_csv(OUT/'equity_DCA_TOTAL.csv',parse_dates=['date']); plt.plot(q.date,q.deposit.cumsum(),label='Накопленные взносы',ls='--',c='black'); plt.legend(); plt.grid(alpha=.2); plt.title('BTC/ETH: стоимость портфеля'); plt.savefig(FIG/'portfolio_values.png',dpi=160); plt.close()
    plt.figure(figsize=(13,7))
    for s in strategies+variant_names: 
        q=pd.read_csv(OUT/f'equity_{s}_TOTAL.csv',parse_dates=['date']); plt.plot(q.date,q.drawdown,label=s)
    plt.legend(); plt.grid(alpha=.2); plt.title('Просадки (без искажения внешними взносами)'); plt.savefig(FIG/'drawdowns.png',dpi=160); plt.close()
    base=res[(res.strategy=='DCA')&(res.asset=='TOTAL')].iloc[0].final_value; cmp=res[res.asset=='TOTAL'].copy(); cmp['vs_dca_usd']=cmp.final_value-base; cmp['vs_dca_pct']=cmp.final_value/base-1; cmp.to_csv(OUT/'comparison_vs_dca.csv',index=False)
    sens=[]
    for label,fee,slip in [('zero_costs',0,0),('baseline',.001,.0005),('double_costs',.002,.001)]:
        for s in strategies:
            vals=[]
            for a in ['BTC','ETH']:
                _,_,m=simulate(a,data[a],s,fee,slip); vals.append(m['final_value'])
            sens.append({'scenario':label,'strategy':s,'fee':fee,'slippage':slip,'final_total':sum(vals)})
    pd.DataFrame(sens).to_csv(OUT/'sensitivity_costs.csv',index=False)
    # annual table from total TWR index
    annual=[]
    for s in strategies:
        q=pd.read_csv(OUT/f'equity_{s}_TOTAL.csv',parse_dates=['date']).set_index('date'); q['year']=q.index.year
        for y,g in q.groupby('year'):
            annual.append({'strategy':s,'year':y,'return_twr':g.twr.iloc[-1]/(q.twr[q.index<g.index[0]].iloc[-1] if (q.index<g.index[0]).any() else 1)-1,'ending_value':g.equity.iloc[-1]})
    pd.DataFrame(annual).to_csv(OUT/'annual_results.csv',index=False)
    meta={'downloaded_utc':datetime.now(timezone.utc).isoformat(),'source':'Binance Spot REST /api/v3/klines','symbols':SYMBOLS,'warmup_start':str(WARMUP),'research_start':str(START),'research_end':str(END),'deposits':len(DEPOSIT_DATES),'deposit_dates':[str(x.date()) for x in DEPOSIT_DATES]}; (OUT/'metadata.json').write_text(json.dumps(meta,indent=2,ensure_ascii=False))
    make_report(res,cmp)

def make_report(res,cmp):
    def fmt(x): return '' if pd.isna(x) else f'{x:,.2f}'
    lines=['# Исследование BTC/ETH, 27.09.2021–26.09.2026','',f'Отчёт сгенерирован: {datetime.now(timezone.utc).isoformat()} UTC.','', '## Методология','', 'Источник: Binance Spot REST endpoint `/api/v3/klines` (документация: https://developers.binance.com/docs/binance-spot-api-docs/rest-api/market-data-endpoints), символы `BTCUSDT` и `ETHUSDT`, дневные свечи UTC, с прогревом с 2020-01-01. Исследование включает 60 пополнений по $100 на 27-е число месяца: BTC $60, ETH $40. Сигнал считается после закрытия дня и исполняется на open следующего дня. Комиссия 0,10%, проскальзывание 0,05% на сторону. Резерв — USDT, условно оценённый как $1; это не учитывает отклонение USDT от USD и комиссии/спред вывода.','', '## Результаты','', '| Стратегия | Субпортфель | Внесено | Итог | Прибыль | Доходность | XIRR | Max DD | Сделок | Комиссии | Проскальзывание |', '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in res.iterrows(): lines.append(f"| {r.strategy} | {r.asset} | {fmt(r.contributions)} | {fmt(r.final_value)} | {fmt(r.profit)} | {r.return_pct:.2%} | {r.xirr:.2%} | {r.max_drawdown:.2%} | {int(r.trades)} | {fmt(r.fees)} | {fmt(r.slippage)} |" )
    lines += ['', 'Графики: `results/figures/portfolio_values.png`, `results/figures/drawdowns.png`. Полные дневные ряды, сделки, годовые срезы и metadata находятся в `results/`.','', '## Сравнение с DCA','', '| Стратегия | Итог | Разница к DCA, $ | Разница к DCA, % |','|---|---:|---:|---:|']
    for _,r in cmp.iterrows(): lines.append(f"| {r.strategy} | {r.final_value:,.2f} | {r.vs_dca_usd:,.2f} | {r.vs_dca_pct:.2%} |")
    sens=pd.read_csv(OUT/'sensitivity_costs.csv')
    lines += ['', '## Чувствительность к издержкам', '', '| Сценарий | Стратегия | Итог |', '|---|---|---:|']
    for _,r in sens.iterrows(): lines.append(f"| {r.scenario} | {r.strategy} | {r.final_total:,.2f} |")
    lines += ['', '## Ограничения и sanity checks','', '- На момент запуска запрашиваются фактические свечи Binance; при сетевой ошибке скрипт завершается, результаты не подменяются.','- Спот-модель без плеча и шортов; сделки по одной цене open, без моделирования bid/ask и частичных исполнений.','- MDD рассчитан по time-weighted индексу: в день взноса из результата исключается внешний cash flow. XIRR использует реальные даты взносов и финальную ликвидационную стоимость.','- Параметры стратегий заданы заранее и не оптимизируются по исследуемому периоду.','- Тесты проверяют даты/число взносов, комиссии, отсутствие отрицательного cash, оценку equity и отсутствие покупок при ложном сигнале.']
    (ROOT/'report.md').write_text('\n'.join(lines),encoding='utf-8')

if __name__=='__main__': run_all()
