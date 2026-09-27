from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

ROOT=Path(__file__).resolve().parent; R=ROOT/'results'; OUT=R/'figures'; OUT.mkdir(exist_ok=True)
sns.set_theme(style='whitegrid',context='talk',palette='colorblind')
labels={'no_yield':'No yield','conservative':'Conservative','base':'Base','high_yield':'High yield','staking_only':'Staking only','lending_only':'Lending only'}
fig,ax=plt.subplots(figsize=(16,9))
for name,label in labels.items():
    q=pd.read_csv(R/f'equity_3asset_{name}.csv',parse_dates=['date'])
    ax.plot(q.date,q.equity,label=label,lw=2.4 if name=='base' else 1.8)
base=pd.read_csv(R/'equity_3asset_base.csv',parse_dates=['date'])
ax.plot(base.date,base.deposit.cumsum(),color='black',ls='--',lw=2.2,label='Cumulative contributions')
ax.set_title('BTC / SOL / INJ Portfolio Value vs. Contributions',weight='bold')
ax.set_xlabel('Date'); ax.set_ylabel('Portfolio value (USDT)')
ax.legend(ncol=2,fontsize=11)
fig.tight_layout(); fig.savefig(OUT/'three_asset_scenarios_vs_contributions.png',dpi=220,bbox_inches='tight'); plt.close(fig)
print(OUT/'three_asset_scenarios_vs_contributions.png')
