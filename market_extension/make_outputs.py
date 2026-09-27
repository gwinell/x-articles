from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.animation import FuncAnimation, PillowWriter

ROOT=Path(__file__).resolve().parent
RES=ROOT/'results'; FIG=RES/'figures'; FIG.mkdir(exist_ok=True)
plt.style.use('dark_background'); sns.set_theme(style='darkgrid',context='talk')
BG='#101318'; GRID='#303640'
plt.rcParams.update({'figure.facecolor':BG,'axes.facecolor':BG,'axes.edgecolor':'#AAB2BF','axes.labelcolor':'#F3F4F6','xtick.color':'#F3F4F6','ytick.color':'#F3F4F6','text.color':'#F3F4F6','grid.color':GRID})

def load_equity(label):
    return pd.read_csv(RES/f'equity_{label}.csv',parse_dates=['date']).set_index('date')
def save(fig,name):
    fig.patch.set_facecolor(BG); fig.savefig(FIG/name,dpi=220,bbox_inches='tight',facecolor=BG); plt.close(fig)

summary=pd.read_csv(RES/'market_comparison_summary.csv')
primary={r.portfolio:load_equity(r.portfolio) for r in summary.itertuples()}
independent={l:load_equity(l) for l in ['A_Crypto_DCA_independent_SMA150','A_Crypto_DCA_independent_SMA200']}

groups=[('Crypto vs trend',['A_Crypto_DCA','A_Crypto_DCA_SMA150','A_Crypto_DCA_SMA200','A_Crypto_DCA_independent_SMA150','A_Crypto_DCA_independent_SMA200']),('ETF portfolios',['B_S&P500_VOO','C_Total_US_VTI','D_Global_VT']),('Mixed portfolios',['A_Crypto_DCA','E_VOO_BTC','E_VOO_BTC_annual_rebalance','F_VOO_BTC_ETH','G_VT_BTC'])]
for title,labels in groups:
    fig,ax=plt.subplots(figsize=(11,6)); ax.set_facecolor(BG)
    for l in labels:
        x=primary[l] if l in primary else independent[l]
        ax.plot(x.index,x.equity,label=l.replace('_',' '),lw=2.4)
    ax.axhline(6000,color='#777',lw=1,ls='--',label='Contributions ($6,000)')
    ax.set_title(title,loc='left',weight='bold'); ax.set_ylabel('Portfolio value, USD'); ax.legend(fontsize=9,ncol=2); ax.grid(alpha=.25,color=GRID); fig.autofmt_xdate(); save(fig,title.lower().replace(' ','_')+'.png')

fig,axes=plt.subplots(1,2,figsize=(15,6)); fig.patch.set_facecolor(BG)
s=summary.sort_values('final_value'); axes[0].barh(s.portfolio,s.final_value,color='#4ea1ff'); axes[0].axvline(6000,color='#777',ls='--'); axes[0].set_title('Ending capital'); axes[0].set_xlabel('USD')
s2=summary.sort_values('max_drawdown'); axes[1].barh(s2.portfolio,s2.max_drawdown*100,color='#ff5c77'); axes[1].set_title('Maximum drawdown'); axes[1].set_xlabel('%')
for ax in axes: ax.grid(alpha=.2,color=GRID,axis='x'); ax.tick_params(axis='y',labelsize=8)
save(fig,'ending_capital_and_drawdown.png')

assets=['BTC','ETH','VOO','VTI','VT','AAPL','MSFT','NVDA','GOOGL']; curves=[]
for a in assets:
    p=ROOT/'data'/f'{a}_daily.csv' if a not in ['BTC','ETH'] else ROOT.parent/'data'/f'{a.lower()}usdt_1d.csv'
    key='date' if a not in ['BTC','ETH'] else 'open_time'; x=pd.read_csv(p,parse_dates=[key]).set_index(key); close=x['close']; start=close.index[close.index>=pd.Timestamp('2021-09-27',tz='UTC')][0]; curves.append((a,close/close.loc[start]*100))
fig,ax=plt.subplots(figsize=(11,6))
for a,c in curves: ax.plot(c.index,c,label=a,lw=2)
ax.axhline(100,color='#777',ls='--'); ax.set_title('Asset price / total-return proxy index (start = 100)',loc='left',weight='bold'); ax.set_ylabel('Index'); ax.legend(ncol=3,fontsize=9); ax.grid(alpha=.25,color=GRID); fig.autofmt_xdate(); save(fig,'asset_returns.png')

core=['A_Crypto_DCA','B_S&P500_VOO','C_Total_US_VTI','D_Global_VT','E_VOO_BTC','F_VOO_BTC_ETH','G_VT_BTC']; annual={}
for l in core:
    x=primary[l]; annual[l]=x.groupby(x.index.year).twr.last().div(x.groupby(x.index.year).twr.first()).sub(1)*100
heat=pd.DataFrame(annual).T; heat.to_csv(RES/'annual_twr_heatmap.csv')
fig,ax=plt.subplots(figsize=(11,5.5)); sns.heatmap(heat,annot=True,fmt='.1f',center=0,cmap='RdYlGn',linewidths=.5,ax=ax,cbar_kws={'label':'TWR %'}); ax.set_title('Calendar-year time-weighted returns',loc='left',weight='bold'); ax.set_xlabel('Year'); ax.set_ylabel('Portfolio'); save(fig,'annual_twr_heatmap.png')

period=pd.read_csv(RES/'period_start_comparison.csv'); fig,ax=plt.subplots(figsize=(11,5.5)); sns.barplot(data=period,x='portfolio',y='return_pct',hue='portfolio',legend=False,ax=ax,palette='viridis'); ax.set_title('Return sensitivity to start date',loc='left',weight='bold'); ax.set_ylabel('Return on contributions'); ax.set_xlabel('Portfolio / start window'); ax.tick_params(axis='x',rotation=75,labelsize=8); ax.yaxis.set_major_formatter(lambda x,pos:f'{x:.0%}'); ax.grid(alpha=.2,color=GRID,axis='y'); save(fig,'start_date_sensitivity.png')

anim_labels=['A_Crypto_DCA','B_S&P500_VOO','F_VOO_BTC_ETH']; series=pd.concat([primary[l].equity.rename(l) for l in anim_labels],axis=1).dropna().iloc[::3]
fig,ax=plt.subplots(figsize=(10,5.5)); fig.patch.set_facecolor(BG)
def frame(i):
    ax.clear(); ax.set_facecolor(BG)
    for l in anim_labels: ax.plot(series.index[:i+1],series[l].iloc[:i+1],label=l.replace('_',' '),lw=2.5)
    ax.axhline(6000,color='#777',ls='--'); ax.set_xlim(series.index.min(),series.index.max()); ax.set_ylim(0,max(series.max())*1.05); ax.set_title(f'DCA comparison — {series.index[i].date()}',loc='left',weight='bold'); ax.set_ylabel('USD'); ax.grid(alpha=.2,color=GRID); ax.legend(fontsize=9)
ani=FuncAnimation(fig,frame,frames=len(series),interval=35,repeat=False); ani.save(FIG/'portfolio_growth.gif',writer=PillowWriter(fps=24)); plt.close(fig)
print('created',len(list(FIG.glob('*.png'))),'PNGs and portfolio_growth.gif')
