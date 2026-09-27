from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

ROOT=Path(__file__).resolve().parent
R=ROOT/'results'
OUT=R/'figures'
sns.set_theme(style='white',context='talk')
df=pd.read_csv(R/'three_asset_scenarios.csv')
names={'no_yield':'No yield','conservative':'Conservative','base':'Base','high_yield':'High yield','staking_only':'Staking only','lending_only':'Lending only'}
rows=[]
for _,r in df.iterrows():
    rows.append([names[r.scenario],f"{r.sol_staking:.2%}",f"{r.inj_staking:.2%}",f"{r.usdt_lending:.2%}",f"${r.final_value:,.2f}",f"${r.profit:,.2f}",f"{r.xirr:.2%}",f"{r.max_drawdown:.2%}",f"${r.fees+r.slippage:,.2f}"])
cols=['Scenario','SOL stake','INJ stake','USDT lend','Final value','Profit','XIRR','Max DD','Fees + slippage']
fig,ax=plt.subplots(figsize=(19,5.8))
ax.axis('off')
table=ax.table(cellText=rows,colLabels=cols,cellLoc='center',colLoc='center',loc='center',colWidths=[.18,.09,.09,.10,.14,.13,.09,.10,.14])
table.auto_set_font_size(False)
table.set_fontsize(13)
table.scale(1,2.2)
for (row,col),cell in table.get_celld().items():
    cell.set_edgecolor('#D9E2F3')
    if row==0:
        cell.set_facecolor('#1F4E78')
        cell.set_text_props(color='white',weight='bold')
    else:
        cell.set_facecolor('#F5F8FC' if row%2 else 'white')
ax.set_title('BTC / SOL / INJ — Staking & Lending Scenarios\nJanuary 2021 – September 2026 | $6,800 contributed',weight='bold',pad=20)
fig.tight_layout()
fig.savefig(OUT/'three_asset_scenarios_table.png',dpi=220,bbox_inches='tight')
plt.close(fig)
print(OUT/'three_asset_scenarios_table.png')
