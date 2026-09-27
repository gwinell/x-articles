import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
import run_backtest as rb
from sma_window_robustness import asset_run

OUT=rb.OUT

def aggregate(data, start, end, mode, window=None):
    legs=[]; fees=slips=trades=0
    for a in ['BTC','ETH']:
        d,f,s,t,_,_=asset_run(data[a],a,start,end,mode,window); legs.append(d); fees+=f; slips+=s; trades+=t
    z=pd.DataFrame(index=legs[0].index); z['equity']=legs[0].equity+legs[1].equity; z['deposit']=legs[0].deposit+legs[1].deposit
    z['ret']=(z.equity-z.deposit)/z.equity.shift(1)-1; z.iloc[0,z.columns.get_loc('ret')]=0.; z['twr']=(1+z.ret).cumprod(); z['drawdown']=z.twr/z.twr.cummax()-1
    cfs=[(dt,-100.) for dt in z.index[z.deposit>0]]+[(z.index[-1],z.equity.iloc[-1])]
    return {'final_value':z.equity.iloc[-1],'xirr':rb.xirr(cfs),'max_drawdown':z.drawdown.min(),'trades':trades,'fees':fees,'slippage':slips,'contributions':z.deposit.sum()}

def main():
    data={a:rb.fetch_symbol(a) for a in ['BTC','ETH']}
    first=pd.Timestamp('2020-01-27',tz='UTC'); last=pd.Timestamp('2021-09-27',tz='UTC')
    starts=pd.date_range('2020-01-01','2021-09-01',freq='MS',tz='UTC')+pd.Timedelta(days=26)
    rows=[]
    for start in starts:
        end=start+pd.DateOffset(months=60)-pd.Timedelta(days=1)
        dca=aggregate(data,start,end,'dca')
        for w in [100,150,200,250,300]:
            sma=aggregate(data,start,end,'sma',w)
            rows.append({'start':start.date(),'end':end.date(),'window':w,'dca_final':dca['final_value'],'sma_final':sma['final_value'],'difference_usd':sma['final_value']-dca['final_value'],'difference_pct':sma['final_value']/dca['final_value']-1,'dca_xirr':dca['xirr'],'sma_xirr':sma['xirr'],'dca_max_dd':dca['max_drawdown'],'sma_max_dd':sma['max_drawdown'],'sma_trades':sma['trades'],'sma_fees':sma['fees'],'sma_slippage':sma['slippage']})
    out=pd.DataFrame(rows); out.to_csv(OUT/'rolling_5y_results.csv',index=False)
    summary=out.groupby('window').agg(windows=('difference_pct','size'),win_rate=('difference_pct',lambda x:(x>0).mean()),median_difference_pct=('difference_pct','median'),mean_difference_pct=('difference_pct','mean'),median_max_dd=('sma_max_dd','median'),mean_max_dd=('sma_max_dd','mean'),median_trades=('sma_trades','median')).reset_index()
    summary.to_csv(OUT/'rolling_5y_summary.csv',index=False)
    pre=out[out.end<=pd.Timestamp('2025-09-26').date()]
    pre_summary=pre.groupby('window').agg(train_windows=('difference_pct','size'),train_win_rate=('difference_pct',lambda x:(x>0).mean()),train_median_difference_pct=('difference_pct','median'),train_mean_difference_pct=('difference_pct','mean')).reset_index()
    pre_summary.to_csv(OUT/'rolling_5y_pre_oos_summary.csv',index=False)
    print('WINDOW SUMMARY'); print(summary.to_string(index=False)); print('\nPRE-OOS END <= 2025-09-26'); print(pre_summary.to_string(index=False)); print('\nTOTAL WINDOWS',len(starts),'FIRST',starts[0].date(),'LAST',starts[-1].date())

if __name__=='__main__': main()
