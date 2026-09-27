from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

ROOT=Path(__file__).resolve().parent
R=ROOT/'results'; OUT=R/'figures'
OUT.mkdir(exist_ok=True)
sns.set_theme(style='whitegrid', context='talk', palette='colorblind')

strategies=['DCA','SMA200','SMA50_200','Momentum90','Donchian20_10','RSI14','Bollinger20_2','DCA_REBALANCE','DCA_SMA200_EXIT','DCA_REBALANCE_SMA200_EXIT']
labels={'DCA':'DCA','SMA200':'SMA 200','SMA50_200':'SMA 50/200','Momentum90':'Momentum 90','Donchian20_10':'Donchian 20/10','RSI14':'RSI 14','Bollinger20_2':'Bollinger 20/2','DCA_REBALANCE':'DCA + Rebalance','DCA_SMA200_EXIT':'DCA + SMA 200 Exit','DCA_REBALANCE_SMA200_EXIT':'DCA + Rebalance + SMA 200 Exit'}
colors=sns.color_palette('tab10',len(strategies))

fig,ax=plt.subplots(figsize=(16,9))
for s,c in zip(strategies,colors):
    q=pd.read_csv(R/f'equity_{s}_TOTAL.csv',parse_dates=['date'])
    ax.plot(q.date,q.equity,label=labels[s],color=c,lw=2 if s in ['DCA','SMA200'] else 1.25,alpha=.95)
q=pd.read_csv(R/'equity_DCA_TOTAL.csv',parse_dates=['date'])
ax.plot(q.date,q.deposit.cumsum(),color='black',ls='--',lw=1.8,label='Cumulative deposits')
ax.set_title('BTC/ETH Portfolio Value — $100 Monthly Contributions',weight='bold')
ax.set_xlabel('Date'); ax.set_ylabel('Portfolio value (USDT)'); ax.legend(ncol=2,fontsize=10,frameon=True)
fig.tight_layout(); fig.savefig(OUT/'article_portfolio_growth.png',dpi=220,bbox_inches='tight'); plt.close(fig)

fig,ax=plt.subplots(figsize=(16,9))
for s,c in zip(strategies,colors):
    q=pd.read_csv(R/f'equity_{s}_TOTAL.csv',parse_dates=['date'])
    ax.plot(q.date,q.drawdown,label=labels[s],color=c,lw=2 if s in ['DCA','SMA200'] else 1.25)
ax.set_title('Drawdown Profile — External Contributions Removed',weight='bold')
ax.set_xlabel('Date'); ax.set_ylabel('Drawdown')
ax.yaxis.set_major_formatter(lambda x,pos:f'{x:.0%}')
ax.legend(ncol=2,fontsize=10)
fig.tight_layout(); fig.savefig(OUT/'article_drawdowns.png',dpi=220,bbox_inches='tight'); plt.close(fig)

roll=pd.read_csv(R/'rolling_5y_results.csv')
p=roll.pivot(index='start',columns='window',values='difference_pct').sort_index()
fig,ax=plt.subplots(figsize=(16,9))
sns.heatmap(p.T*100,center=0,cmap='RdYlGn',annot=True,fmt='.1f',linewidths=.4,cbar_kws={'label':'SMA advantage vs DCA (%)'},ax=ax)
ax.set_title('Rolling 5-Year SMA Performance vs DCA',weight='bold')
ax.set_xlabel('Window start date'); ax.set_ylabel('SMA length')
fig.tight_layout(); fig.savefig(OUT/'article_rolling_heatmap.png',dpi=220,bbox_inches='tight'); plt.close(fig)

summ=pd.read_csv(R/'rolling_5y_summary.csv')
fig,ax=plt.subplots(figsize=(12,7))
sns.barplot(data=summ,x='window',y='win_rate',color='#2878B5',ax=ax)
ax.axhline(.5,color='black',ls='--',lw=1.5,label='50% of windows')
for i,row in summ.iterrows(): ax.text(i,row.win_rate+.025,f"{row.win_rate:.1%}",ha='center',weight='bold')
ax.set_title('Share of Rolling 5-Year Windows Beating DCA',weight='bold')
ax.set_xlabel('SMA length'); ax.set_ylabel('Winning windows')
ax.yaxis.set_major_formatter(lambda x,pos:f'{x:.0%}'); ax.legend()
fig.tight_layout(); fig.savefig(OUT/'article_sma_win_rate.png',dpi=220,bbox_inches='tight'); plt.close(fig)

print('Created:', ', '.join(p.name for p in OUT.glob('article_*.png')))
