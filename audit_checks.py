import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
import run_backtest as rb

OUT=rb.OUT

def deposits(start,end):
    return pd.date_range(start.replace(day=1), end.replace(day=1)-pd.offsets.MonthBegin(1), freq='MS', tz='UTC')+pd.Timedelta(days=26)

def run_period(data, start, end):
    old=(rb.START,rb.END,rb.DEPOSIT_DATES)
    rb.START,rb.END,rb.DEPOSIT_DATES=start,end,deposits(start,end)
    out=[]
    for s in ['DCA','SMA200','DCA_SMA200_EXIT','DCA_REBALANCE_SMA200_EXIT']:
        if s in ('DCA','SMA200'):
            vals=[rb.simulate(a,data[a],s)[2]['final_value'] for a in ['BTC','ETH']]
            final=sum(vals)
        else:
            final=rb.simulate_dca_variants(data,s)[2]['final_value']
        out.append({'period_start':start.date(),'period_end':end.date(),'strategy':s,'contributions':len(rb.DEPOSIT_DATES)*100,'final_value':final})
    rb.START,rb.END,rb.DEPOSIT_DATES=old
    return out

def main():
    data={a:rb.indicators(rb.fetch_symbol(a)) for a in ['BTC','ETH']}
    # 1) Every combined-strategy buy must follow a bullish own-asset SMA200 signal.
    t=pd.read_csv(OUT/'trades_DCA_REBALANCE_SMA200_EXIT_TOTAL.csv',parse_dates=['date'])
    checks=[]
    for _,r in t[t.side=='BUY'].iterrows():
        dt=r.date.tz_localize('UTC') if r.date.tz is None else r.date
        x=data[r.asset]; pos=x.index.get_loc(dt); prev=x.iloc[pos-1]
        checks.append({'date':dt,'asset':r.asset,'buy_signal_bullish':bool(prev.close>prev.sma200),'prev_close':prev.close,'prev_sma200':prev.sma200})
    checks=pd.DataFrame(checks); checks.to_csv(OUT/'audit_signal_checks.csv',index=False)
    # 2) Compare signal-only strategy and DCA+SMA200 trade dates; then show
    #    expected differences introduced by monthly rebalance.
    rows=[]
    for a in ['BTC','ETH']:
        s=pd.read_csv(OUT/f'trades_SMA200_{a}.csv',parse_dates=['date']); v=pd.read_csv(OUT/'trades_DCA_SMA200_EXIT_TOTAL.csv',parse_dates=['date']); v=v[v.asset==a].copy(); c=t[t.asset==a].copy()
        for side in ['BUY','SELL']:
            sd=list(s.loc[s.side==side,'date'].astype(str)); vd=list(v.loc[v.side==side,'date'].astype(str))
            cd=list(c.loc[c.side==side,'date'].astype(str))
            rows.append({'asset':a,'side':side,'sma200_count':len(sd),'dca_sma200_count':len(vd),'same_signal_dates':sd==vd,'rebalance_exit_count':len(cd),'only_sma200_vs_dca':','.join(sorted(set(sd)-set(vd))),'only_dca_vs_sma200':','.join(sorted(set(vd)-set(sd)))})
    pd.DataFrame(rows).to_csv(OUT/'audit_trade_comparison.csv',index=False)
    # Position divergence: reconstruct units by asset from combined trades and compare to SMA200 equity ledgers.
    div=[]
    for a in ['BTC','ETH']:
        std=pd.read_csv(OUT/f'equity_SMA200_{a}.csv',parse_dates=['date']).set_index('date')
        tr=t[t.asset==a].sort_values('date'); u=0.; mp={}
        for dt in std.index:
            for _,z in tr[tr.date==dt].iterrows(): u += z.units if z.side=='BUY' else -z.units
            mp[dt]=u
        comb=pd.Series(mp); diff=(std.units-comb).abs()
        for dt in diff[diff>1e-10].index[:20]: div.append({'asset':a,'first_divergence_date':dt,'sma200_units':std.loc[dt,'units'],'combined_units':comb.loc[dt]})
    pd.DataFrame(div).to_csv(OUT/'audit_position_divergence.csv',index=False)
    # 3) Other start dates and a separate 2020-2025 five-year period.
    periods=[(pd.Timestamp('2020-09-27',tz='UTC'),pd.Timestamp('2025-09-26',tz='UTC')),(pd.Timestamp('2021-09-27',tz='UTC'),pd.Timestamp('2026-09-26',tz='UTC')),(pd.Timestamp('2022-09-27',tz='UTC'),pd.Timestamp('2026-09-26',tz='UTC'))]
    pd.DataFrame([z for p in periods for z in run_period(data,*p)]).to_csv(OUT/'robustness_periods.csv',index=False)
    print('BUY_SIGNAL_VIOLATIONS', int((~checks.buy_signal_bullish).sum()))
    print('TRADE_COMPARISON'); print(pd.DataFrame(rows).to_string(index=False))
    print('FIRST_POSITION_DIVERGENCES'); print(pd.DataFrame(div).groupby('asset').first().to_string() if div else 'none')
    print('ROBUSTNESS'); print(pd.read_csv(OUT/'robustness_periods.csv').to_string(index=False))

if __name__=='__main__': main()
