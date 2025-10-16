import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np

# === Load data ===
file_path = 'csv_-29.815268_30.946439_fixed_23_0_PT5M.csv'
df = pd.read_csv(file_path, parse_dates=['period_end'])

# === Set datetime index ===
df['period_end'] = pd.to_datetime(df['period_end'])
df.set_index('period_end', inplace=True)

# Restrict to 2024 and above
df = df[df.index.year >= 2024]

# Extract numeric columns only
numeric_df = df.select_dtypes(include=['float64', 'int64'])

# Compute correlation matrix
corr_matrix = numeric_df.corr()

# === Plot heatmap ===
fig, ax = plt.subplots(figsize=(12, 8), facecolor='#f9f9f9')
ax.set_facecolor('#f9f9f9')

sns.set(font='Garamond', font_scale=1.2, style='white')

# Mask strictly upper triangle
mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)

sns.heatmap(
    corr_matrix,
    annot=True,
    cmap='coolwarm',
    vmin=-1,
    vmax=1,
    linewidths=0.5,
    fmt=".2f",
    ax=ax,
    mask=mask,
    annot_kws={
        "size": 13.5,
        "weight": "bold",
        "ha": "center",
        "va": "center",
        "color": "black"
    }
)

plt.xticks(fontsize=13.5, rotation=35, ha='right')
plt.yticks(fontsize=13.5, rotation=0)
plt.tight_layout()

# Save with high quality
plt.savefig("Correlation_Heatmap_SMARTGRID_Solcast.csv.pdf", format="pdf", dpi=900, bbox_inches='tight')
plt.show()
