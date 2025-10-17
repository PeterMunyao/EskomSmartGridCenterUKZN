# === PLOT AC POWER (kW) ONLY - SIMPLER VERSION ===
plt.rcParams["font.family"] = "Garamond"
fig, ax = plt.subplots(figsize=(11, 15), facecolor='#f0f0f0')
ax.set_facecolor('#f0f0f0')

# Plot AC Power from both models
ax.plot(df.index, df["AC_Power_kW_pvlib_total"], 
        color="orange", label="PVLIB AC Power", linewidth=2.0)
ax.plot(df.index, df["AC_Power_kW_osm_total"], 
        color="green", label="OSM-MEPS AC Power", linewidth=2.0)

ax.set_xlabel("Date", fontsize=18, fontweight='bold')
ax.set_ylabel("AC Power (kW) at 5 Minutes ", fontsize=18, fontweight='bold')


ax.grid(True, linestyle='--', alpha=0.5)

# Format ticks
ax.tick_params(axis='x', labelsize=19)
ax.tick_params(axis='y', labelsize=16)
for label in ax.get_xticklabels() + ax.get_yticklabels():
    label.set_fontweight('bold')

# Calculate statistics
pvlib_max = df['AC_Power_kW_pvlib_total'].max()
pvlib_avg = df['AC_Power_kW_pvlib_total'].mean()
pvlib_min = df['AC_Power_kW_pvlib_total'].min()

osm_max = df['AC_Power_kW_osm_total'].max()
osm_avg = df['AC_Power_kW_osm_total'].mean()
osm_min = df['AC_Power_kW_osm_total'].min()

# Create custom legend
from matplotlib.patches import Patch

legend_elements = [
    # Power lines
    plt.Line2D([0], [0], color='orange', lw=4, label='PVLIB AC Power'),
    plt.Line2D([0], [0], color='green', lw=4, label='OSM-MEPS AC Power'),
    Patch(facecolor='none', edgecolor='none', label=''),
    
    # Statistics
    Patch(facecolor='none', edgecolor='none', label='AC POWER STATISTICS'),
    Patch(facecolor='none', edgecolor='none', label=''),
    Patch(facecolor='none', edgecolor='none', label=f'PVLIB: Max={pvlib_max:.1f} kW  Avg={pvlib_avg:.1f} kW  Min={pvlib_min:.1f} kW'),
    Patch(facecolor='none', edgecolor='none', label=f'OSM:   Max={osm_max:.1f} kW  Avg={osm_avg:.1f} kW  Min={osm_min:.1f} kW'),
]

# Place legend below the graph
legend = ax.legend(handles=legend_elements, 
                  loc='upper center', 
                  bbox_to_anchor=(0.5, -0.25),
                  ncol=1,
                  fontsize=13,
                  frameon=True,
                  fancybox=True,
                  shadow=True,
                  facecolor='white',
                  framealpha=0.9)

# Format the legend text
for text in legend.get_texts():
    if 'STATISTICS' in text.get_text():
        text.set_fontweight('bold')
        text.set_fontsize(18)

plt.tight_layout(rect=[0, 0.10, 1, 0.75])
plt.savefig("SMARTGRID_AC_Power_kW_5min.pdf", format='pdf', bbox_inches='tight', dpi=700)
plt.show()

# Print to console
print("\n" + "="*50)
print("AC POWER STATISTICS")
print("="*50)
print(f"PVLIB Model:  Max={pvlib_max:.2f} kW, Avg={pvlib_avg:.2f} kW, Min={pvlib_min:.2f} kW")
print(f"OSM-MEPS Model: Max={osm_max:.2f} kW, Avg={osm_avg:.2f} kW, Min={osm_min:.2f} kW")
print("="*50)
