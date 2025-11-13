import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np

# === LOAD WEATHER DATA - SHIFT CSV TIME BY +2 HOURS ===
file_path = 'csv_-29.815268_30.946439_fixed_23_0_PT5M.csv'
df = pd.read_csv(file_path)
df['period_end'] = pd.to_datetime(df['period_end'])  # Load with original timezone
df.set_index('period_end', inplace=True)
df = df[(df.index >= '2024-01-01') & (df.index < '2025-01-01')]

# Shift time by +2 hours
df.index = df.index + pd.Timedelta(hours=2)

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

#----------------------------------------------------------------------------

import pandas as pd
import matplotlib.pyplot as plt
import calendar
import numpy as np

plt.rcParams['xtick.labelsize'] = 18
plt.rcParams['ytick.labelsize'] = 18
plt.rcParams['xtick.color'] = 'black'
plt.rcParams['ytick.color'] = 'black'

# === LOAD WEATHER DATA - SHIFT CSV TIME BY +2 HOURS ===
file_path = 'csv_-29.815268_30.946439_fixed_23_0_PT5M.csv'
df = pd.read_csv(file_path)
df['period_end'] = pd.to_datetime(df['period_end'])  # Load with original timezone
df.set_index('period_end', inplace=True)
df = df[(df.index >= '2024-01-01') & (df.index < '2025-01-01')]

# Shift time by +2 hours
df.index = df.index + pd.Timedelta(hours=2)
df = df[df.index.year >= 2024]

# Columns to plot
columns_to_plot = ['ghi', 'relative_humidity', 'cloud_opacity', 'air_temp']

# Fill missing columns
for col in columns_to_plot:
    if col not in df.columns:
        print(f"Warning: {col} not found in CSV, filling with NaN.")
        df[col] = float('nan')

# Font setup
plt.rcParams["font.family"] = "Garamond"
plt.rcParams["axes.titlesize"] = 14
plt.rcParams["axes.labelsize"] = 16

# === Adjusted Figure ===
# Very light gray background
fig, axes = plt.subplots(6, 2, figsize=(10.5, 14.0), facecolor='#fafafa')  # Slightly taller to accommodate lower legend
axes = axes.flatten()

# Color mapping
color_dict = {
    'ghi': 'orange',
    'air_temp': '#e41a1c',
    'relative_humidity': '#984ea3',
    'cloud_opacity': '#4daf4a'
}

# Collect all handles for combined legend
all_lines, all_labels = [], []

# Loop through each month
for month in range(1, 13):
    ax = axes[month-1]
    # Set very light gray background for each subplot
    ax.set_facecolor('#fafafa')
    
    df_month = df[df.index.month == month].copy()
    df_month['hour'] = df_month.index.hour
    df_hourly = df_month.groupby('hour')[columns_to_plot].mean()

    # Plot DNI on primary y-axis
    line_dni, = ax.plot(df_hourly.index, df_hourly['ghi'], label='GHI', 
                        color=color_dict['ghi'], linewidth=1.8)
    ax.set_ylabel('GHI (W/m²)', fontsize=15, fontweight='bold')
    ax.set_ylim(0, df_hourly['ghi'].max() * 1.1)
    ax.set_xticks(range(0, 24, 3))
    
    # Make x and y tick labels bold
    ax.tick_params(axis='x', which='major', labelsize=16, width=1.5, labelcolor='black')
    ax.tick_params(axis='y', which='major', labelsize=16, width=1.5, labelcolor='black')
    
    # Set bold font for tick labels
    for label in ax.get_xticklabels():
        label.set_fontweight('bold')
    for label in ax.get_yticklabels():
        label.set_fontweight('bold')
    
    ax.grid(True, linestyle=':', linewidth=0.4, color='gray')

    # Plot secondary y-axis
    ax2 = ax.twinx()
    # Set very light gray background for secondary axis as well
    ax2.set_facecolor('#fafafa')
    
    line_rh, = ax2.plot(df_hourly.index, df_hourly['relative_humidity'], 
                        label='Relative Humidity (%)', color=color_dict['relative_humidity'],
                        linestyle='--', linewidth=1.5)
    line_cloud, = ax2.plot(df_hourly.index, df_hourly['cloud_opacity'], 
                           label='Cloud Opacity (%)', color=color_dict['cloud_opacity'],
                           linestyle='-', linewidth=1.5)
    line_temp, = ax2.plot(df_hourly.index, df_hourly['air_temp'], 
                          label='Air Temp (°C)', color=color_dict['air_temp'],
                          linestyle='-.', linewidth=1.5)
    ax2.set_ylim(0, 100)
    ax2.set_ylabel('Humidity / Temp (%)', fontsize=15, fontweight='bold')
    
    # Make secondary y-axis tick labels bold
    ax2.tick_params(axis='y', which='major', labelsize=16, width=1.5, labelcolor='black')
    for label in ax2.get_yticklabels():
        label.set_fontweight('bold')

    if month == 1:
        all_lines.extend([line_dni, line_rh, line_cloud, line_temp])
        all_labels.extend(['GHI (W/m²)', 'Relative Humidity (%)', 
                           'Cloud Opacity (%)', 'Air Temp (°C)'])

    # Month title
    ax.set_title(calendar.month_abbr[month], fontsize=12, fontweight='bold')
    if month > 10:
        ax.set_xlabel('Hour of Day', fontsize=16)

# === Layout Adjustments ===
plt.subplots_adjust(
    left=0.07, right=0.93, top=0.95, bottom=0.12,  # Increased bottom margin from 0.08 to 0.12 to push legend down
    hspace=0.47, wspace=0.40
)

# Combined legend below all plots with very light gray background - positioned lower
fig.legend(all_lines, all_labels, loc='lower center', ncol=4, 
           frameon=True, facecolor='#fafafa', edgecolor='#fafafa',
           bbox_to_anchor=(0.5, 0.02),  # Lowered bbox_to_anchor from default (0.5, 0.0)
           prop={'weight': 'bold', 'size': 16})  # Font size and weight in prop

# Save final figure
plt.savefig(
    "SMART_GRID_24h_DNI_CLOUDOPACITY_2024_final.pdf",
    format='pdf',
    bbox_inches='tight',
    facecolor=fig.get_facecolor()
)
plt.show()

#--------------------------------------------------------------------------------------------------------------------------

# === IMPORT LIBRARIES ===
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import pvlib
from pvlib.irradiance import get_total_irradiance
from pvlib.temperature import sapm_cell

# === LOAD WEATHER DATA - SHIFT CSV TIME BY +2 HOURS ===
file_path = 'csv_-29.815268_30.946439_fixed_23_0_PT5M.csv'
df = pd.read_csv(file_path)
df['period_end'] = pd.to_datetime(df['period_end'])  # Load with original timezone
df.set_index('period_end', inplace=True)
df = df[(df.index >= '2024-01-01') & (df.index < '2025-01-01')]

# Shift time by +2 hours
df.index = df.index + pd.Timedelta(hours=2)

# === FILTER DATA FOR YEAR 2024 ONLY ===
df = df[(df.index >= '2024-01-01') & (df.index < '2025-01-01')]

# === ENSURE REQUIRED METEOROLOGICAL COLUMNS EXIST ===
required_columns = ['dni', 'ghi', 'dhi', 'air_temp', 'albedo', 'zenith', 'azimuth',
                    'cloud_opacity', 'relative_humidity', 'wind_speed_10m']
for col in required_columns:
    if col not in df.columns:
        print(f"Warning: Column '{col}' is missing. Filling with zeros.")
        df[col] = 0

# === PV SYSTEM PARAMETERS ===
latitude = -29.815268
longitude = 30.946439
panel_power_max = 600      # W
inverter_efficiency = 0.95
temp_coeff = -0.0045
stc_irradiance = 1000       # W/m^2
losses = 1

# === SOLAR POSITION ===
solar_position = pvlib.solarposition.get_solarposition(df.index, latitude, longitude)

# === DEFINE ROOFTOP FIELD SEGMENTS ===
field_segments = [
    {"tilt": 5.6, "azimuth": 319.88214, "num_modules": 32},
    {"tilt": 2.8, "azimuth": 146.61220, "num_modules": 32},
    {"tilt": 5.0, "azimuth": 326.42346, "num_modules": 32},
    {"tilt": 3.0, "azimuth": 315.20587, "num_modules": 32},
    {"tilt": 3.0, "azimuth": 134.65346, "num_modules": 64},
]

# === INITIALIZE TOTAL POWER COLUMNS ===
df["AC_Power_kW_pvlib_total"] = 0
df["AC_Power_kW_osm_total"] = 0

# === LOOP OVER SEGMENTS ===
for seg in field_segments:
    tilt = seg["tilt"]
    azimuth = seg["azimuth"]
    num_panels = seg["num_modules"]

    # --- PVLIB MODEL ---
    poa = get_total_irradiance(
        surface_tilt=tilt,
        surface_azimuth=azimuth,
        dni=df["dni"],
        ghi=df["ghi"],
        dhi=df["dhi"],
        solar_zenith=solar_position["apparent_zenith"],
        solar_azimuth=solar_position["azimuth"]
    )
    poa_irradiance = poa["poa_global"]

    temp_cell = sapm_cell(poa_irradiance, df["air_temp"], df["wind_speed_10m"], -3.47, -0.0594, 3)
    dc_power_pvlib = poa_irradiance / stc_irradiance * num_panels * panel_power_max * \
                     (1 + temp_coeff * (temp_cell - 25))
    ac_power = dc_power_pvlib * inverter_efficiency * losses
    df["AC_Power_kW_pvlib_total"] += ac_power / 1000  # kW

    # --- OSM-MEPS MODEL ---
    tilt_rad = np.radians(tilt)
    az_rad = np.radians(azimuth)
    zen_rad = np.radians(df['zenith'])
    sun_az_rad = np.radians(df['azimuth'])

    aoi = np.degrees(np.arccos(
        np.cos(zen_rad) * np.cos(tilt_rad) +
        np.sin(zen_rad) * np.sin(tilt_rad) * np.cos(sun_az_rad - az_rad)
    ))
    aoi = np.clip(aoi, 0, 90)

    poa_direct = df['dni'] * np.cos(np.radians(aoi)) * (1 - df['cloud_opacity'] / 100)
    poa_direct = poa_direct.clip(lower=0)
    poa_diffuse = df['dhi'] * (1 + np.cos(tilt_rad)) / 2
    poa_reflected = df['ghi'] * df['albedo'] * (1 - np.cos(tilt_rad)) / 2
    poa_total = poa_direct + poa_diffuse + poa_reflected

    module_temp = 45 + poa_total / 1000 * (28 - df['air_temp'])
    dc_power_osm = panel_power_max * (1 + temp_coeff * (module_temp - 45))
    dc_power_osm *= poa_total / stc_irradiance
    dc_power_osm *= (1 - 0.002 * df['relative_humidity'])
    ac_power_osm = dc_power_osm * inverter_efficiency
    scaled_power = ac_power_osm * num_panels
    actual_power = scaled_power * (1 - 0.01)
    df["AC_Power_kW_osm_total"] += actual_power / 1000  # kW

# === 5-MINUTE ENERGY CALCULATION ===
# Energy (kWh) per 5-minute interval
df["Energy_kWh_pvlib_5min"] = df["AC_Power_kW_pvlib_total"] * (5/60)
df["Energy_kWh_osm_5min"] = df["AC_Power_kW_osm_total"] * (5/60)

# === PLOT ENERGY AT 5-MINUTE INTERVALS ===
plt.rcParams["font.family"] = "Garamond"
fig, ax = plt.subplots(figsize=(10, 5), facecolor='#fafafa')
ax.set_facecolor('#fafafa')

ax.plot(df.index, df["Energy_kWh_pvlib_5min"], label="PVLIB Energy", color='orange', linewidth=0.7)
ax.plot(df.index, df["Energy_kWh_osm_5min"], label="OSM-MEPS Energy", color='green', linewidth=0.7)

ax.set_xlabel("Date", fontsize=18)
ax.set_ylabel("Energy per 5 min (kWh)", fontsize=20)

ax.legend(fontsize=14)
ax.grid(True, linestyle='--', alpha=0.5)

ax.tick_params(axis='x', labelsize=18)
ax.tick_params(axis='y', labelsize=18)

plt.tight_layout()
plt.savefig("SMART-GRID_11_Energy_5min_PETER.pdf", format='pdf')
plt.show()


# ===== Load your processed DataFrame =====
# If you've already run the earlier scripts and have df in memory, skip the read step.
# Otherwise, replace with your CSV path:
# df = pd.read_csv("processed_pv_results.csv", parse_dates=['period_end'], index_col='period_end')

# Ensure the index is datetime and sorted
df = df.sort_index()

# --- Calculate time difference in seconds (should be 300 s for 5-minute steps) ---
time_diff_s = df.index.to_series().diff().dt.total_seconds().fillna(0)

# --- Compute ramp rates in W/s ---
df["Ramp_W_per_s_pvlib"] = df["AC_Power_kW_pvlib_total"].diff() * 1000 / time_diff_s
df["Ramp_W_per_s_osm"]   = df["AC_Power_kW_osm_total"].diff()   * 1000 / time_diff_s

# ===== Plot Ramp Rate (W/s) =====
plt.rcParams["font.family"] = "Garamond"
fig, ax = plt.subplots(figsize=(10, 5), facecolor='#fafafa')
ax.set_facecolor('#fafafa')

ax.plot(df.index, df["Ramp_W_per_s_pvlib"],
        color="orange", label="PVLIB Ramp Rate (W/s)", linewidth=0.4)
ax.plot(df.index, df["Ramp_W_per_s_osm"],
        color="green", label="OSM-MEPS Ramp Rate (W/s)", linewidth=0.4)

ax.set_xlabel("Time", fontsize=18, fontweight='bold')
ax.set_ylabel("Ramp Rate (W/s)", fontsize=20)

ax.legend(fontsize=14)
ax.grid(True, linestyle="--", alpha=0.85)

plt.tight_layout()
plt.savefig("RampRate_W_per_s_SMARTG_PETER.pdf", format="pdf")
plt.show()

#-----------------------------------------------------------------------------------

# === OSM-MEPS MODEL ANALYSIS FOR MAX RAMP DAY ===
print("=== OSM-MEPS MODEL BATTERY SIZING ANALYSIS ===")

# Calculate ramp rates for OSM-MEPS model
time_diff_s = df.index.to_series().diff().dt.total_seconds().fillna(0)
df["Ramp_W_per_s_osm"] = df["AC_Power_kW_osm_total"].diff() * 1000 / time_diff_s

# Calculate power swings for OSM-MEPS model
max_power_swing_5min_osm = df['AC_Power_kW_osm_total'].diff().abs().max()
max_swing_time_5min_osm = df['AC_Power_kW_osm_total'].diff().abs().idxmax()

print(f"OSM-MEPS 5-min power swing: {max_power_swing_5min_osm:.1f} kW at {max_swing_time_5min_osm}")

# Battery sizing based on OSM-MEPS model
battery_power_rating_osm = max_power_swing_5min_osm * 1.2  # 20% margin
recommended_energy_osm = battery_power_rating_osm * 2.0    # 2-hour duration

print(f"Battery Requirements (OSM-MEPS): {battery_power_rating_osm:.1f} kW / {recommended_energy_osm:.1f} kWh")

# Select day with maximum power changes
analysis_date_osm = max_swing_time_5min_osm.date()
day_data_osm = df[df.index.date == analysis_date_osm]

print(f"\n=== OSM-MEPS ANALYSIS FOR {analysis_date_osm} ===")
print(f"Maximum 5-min swing: {day_data_osm['AC_Power_kW_osm_total'].diff().abs().max():.1f} kW")
print(f"Maximum ramp rate: {day_data_osm['Ramp_W_per_s_osm'].abs().max():.1f} W/s")

# === PROFESSIONAL GRAPH STYLING ===
plt.rcParams["font.family"] = "Garamond"
plt.rcParams["font.size"] = 17  # Increased by 3 steps from 14
plt.rcParams["font.weight"] = "bold"
plt.rcParams["axes.labelweight"] = "bold"
plt.rcParams['xtick.labelsize'] = 17  # Increased by 3 steps from 14
plt.rcParams['ytick.labelsize'] = 17  # Increased by 3 steps from 14
plt.rcParams["axes.titleweight"] = "bold"
plt.rcParams["legend.fontsize"] = 15  # Increased by 3 steps from 12

# === CREATE COMBINED GRAPH ===
fig = plt.figure(figsize=(11, 12), facecolor='#fafafa')
# Reduced hspace to bring plots closer together
gs = plt.GridSpec(2, 1, figure=fig, hspace=0.15)  # Reduced from 0.3
ax1 = fig.add_subplot(gs[0])
ax2 = fig.add_subplot(gs[1])

# Set professional background and grid - REMOVED fafafa background
for ax in [ax1, ax2]:
    ax.set_facecolor('white')  # Changed from #fafafa to white
    
    # Major grid (hourly)
    ax.grid(True, linestyle='-', alpha=0.2, linewidth=0.8, which='major')
    
    # Minor grid (sub-hourly - every 15 minutes)
    ax.grid(True, linestyle=':', alpha=0.1, linewidth=0.5, which='minor')
    
    # Set minor locator for sub-hourly grids
    ax.xaxis.set_minor_locator(plt.matplotlib.dates.MinuteLocator(interval=15))
    
    # Black frames
    ax.spines['top'].set_visible(True)
    ax.spines['top'].set_color('black')
    ax.spines['top'].set_linewidth(1.2)
    ax.spines['right'].set_visible(True)
    ax.spines['right'].set_color('black')
    ax.spines['right'].set_linewidth(1.2)
    ax.spines['left'].set_linewidth(1.2)
    ax.spines['bottom'].set_linewidth(1.2)

# === GRAPH 1: IRRADIANCE, METEOROLOGICAL DATA AND POWER OUTPUT ===
# Primary axis - Irradiance
color_ghi = 'brown'  
color_dni = '#ff7f0e'  # Orange
color_dhi = 'blue'  

ax1.plot(day_data_osm.index, day_data_osm['ghi'], color=color_ghi, linewidth=1.8, label='GHI', alpha=0.9)
ax1.plot(day_data_osm.index, day_data_osm['dni'], color=color_dni, linewidth=1.8, linestyle='--', label='DNI', alpha=0.8)
ax1.plot(day_data_osm.index, day_data_osm['dhi'], color=color_dhi, linewidth=1.8, linestyle=':', label='DHI', alpha=0.8)

ax1.set_ylabel('Irradiance (W/m²)', fontsize=19, fontweight='bold', color='#333333')  # Increased by 3 steps from 16
ax1.set_ylim(bottom=0)

# Secondary axis - Meteorological data
ax1_twin = ax1.twinx()
ax1_twin.set_facecolor('white')  # Changed from #fafafa to white
color_cloud = 'indigo'
color_humidity = '#8c564b'

cloud_opacity_scaled = day_data_osm['cloud_opacity']
humidity_scaled = day_data_osm['relative_humidity']

ax1_twin.plot(day_data_osm.index, cloud_opacity_scaled, color=color_cloud, linewidth=1.8, alpha=0.7, label='Cloud Opacity')
ax1_twin.plot(day_data_osm.index, humidity_scaled, color=color_humidity, linewidth=1.8, alpha=0.7, linestyle='--', label='Relative Humidity')
ax1_twin.set_ylabel('Cloud Opacity / Humidity (%)', fontsize=19, fontweight='bold', color='black')  # Increased by 3 steps from 16
ax1_twin.set_ylim(0, 100)

# Add grids to twin axes
ax1_twin.grid(True, linestyle='-', alpha=0.2, linewidth=0.8, which='major')
ax1_twin.grid(True, linestyle=':', alpha=0.1, linewidth=0.5, which='minor')
ax1_twin.xaxis.set_minor_locator(plt.matplotlib.dates.MinuteLocator(interval=15))

# Tertiary axis - PV Power
ax1_twin2 = ax1.twinx()
ax1_twin2.set_facecolor('white')  # Changed from #fafafa to white
ax1_twin2.spines['right'].set_position(('outward', 60))
color_power = 'green'

ax1_twin2.plot(day_data_osm.index, day_data_osm['AC_Power_kW_osm_total'], color=color_power, linewidth=2.0, label='PV Power (OSM-MEPS)')
ax1_twin2.set_ylabel('Power (kW)', fontsize=19, fontweight='bold')  # Increased by 3 steps from 16
ax1_twin2.set_ylim(bottom=0)

# Add grids to second twin axis
ax1_twin2.grid(True, linestyle='-', alpha=0.2, linewidth=0.8, which='major')
ax1_twin2.grid(True, linestyle=':', alpha=0.1, linewidth=0.5, which='minor')
ax1_twin2.xaxis.set_minor_locator(plt.matplotlib.dates.MinuteLocator(interval=15))

# Bold tick labels
for ax in [ax1, ax1_twin, ax1_twin2]:
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontweight('bold')

# === GRAPH 2: RAMP RATE ===
color_ramp = 'red'  
ax2.plot(day_data_osm.index, day_data_osm['Ramp_W_per_s_osm'], color=color_ramp, linewidth=1.9, label='Ramp Rate', alpha=0.9)
ax2.set_ylabel('Ramp Rate (W/s)', fontsize=19, fontweight='bold')  # Increased by 3 steps from 16
ax2.set_xlabel('Time of Day', fontsize=19, fontweight='bold')  # Increased by 3 steps from 16
ax2.axhline(y=0, color='black', linestyle='-', alpha=0.3, linewidth=1)

# Highlight maximum ramp event
max_ramp_time_osm = day_data_osm['Ramp_W_per_s_osm'].abs().idxmax()
max_ramp_value_osm = day_data_osm.loc[max_ramp_time_osm, 'Ramp_W_per_s_osm']

ax2.plot(max_ramp_time_osm, max_ramp_value_osm, 'o', markersize=8,
         markerfacecolor='red', markeredgecolor='darkred', markeredgewidth=2)

ax2.annotate(f'Max: {max_ramp_value_osm:.1f} W/s', xy=(max_ramp_time_osm, max_ramp_value_osm),
             xytext=(10, 20), textcoords='offset points',
             bbox=dict(boxstyle='round,pad=0.3', facecolor='orange', alpha=0.7),
             arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0', linewidth=1.2),
             fontweight='bold', fontsize=17)  # Increased by 3 steps from 14

# Bold tick labels
for label in ax2.get_xticklabels() + ax2.get_yticklabels():
    label.set_fontweight('bold')

# Combine legends for Graph 1
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax1_twin.get_legend_handles_labels()
lines3, labels3 = ax1_twin2.get_legend_handles_labels()

# Create combined legend below the plots
fig.legend(lines1 + lines2 + lines3, labels1 + labels2 + labels3,
           loc='lower center', bbox_to_anchor=(0.5, 0.08), ncol=3,
           framealpha=0.95, fancybox=True, shadow=True, fontsize=16, frameon=True)  # Increased by 3 steps from 13

# Add legend for ramp rate
ax2.legend(loc='upper right', framealpha=0.9, fancybox=True, shadow=True, fontsize=15)  # Increased by 3 steps from 12

# === STATISTICS BOX ===
stats_text = (
    f"OSM-MEPS MODEL STATISTICS\n\n"
    f"• Maximum Power: {day_data_osm['AC_Power_kW_osm_total'].max():.1f} kW\n"
    f"• Maximum GHI: {day_data_osm['ghi'].max():.1f} W/m²\n"
    f"• Maximum Ramp Rate: {day_data_osm['Ramp_W_per_s_osm'].abs().max():.1f} W/s\n"
    f"• Maximum 5-min Swing: {max_power_swing_5min_osm:.1f} kW\n"
    f"• Maximum Cloud Opacity: {day_data_osm['cloud_opacity'].max():.1f}%\n"
    f"• Recommended Battery: {battery_power_rating_osm:.1f} kW / {recommended_energy_osm:.1f} kWh"
)

# Position stats box LOWER to avoid covering the ramp plot
ax2.text(0.02, 0.50, stats_text, transform=ax2.transAxes, fontsize=14,  # Increased by 3 steps from 11
         bbox=dict(boxstyle="round,pad=0.6", facecolor="white", alpha=0.95, 
                  edgecolor='black', linewidth=1),
         verticalalignment='top', fontweight='bold', linespacing=1.4)

# Format x-axis for both plots
for ax in [ax1, ax2]:
    ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%H:%M'))
    ax.xaxis.set_major_locator(plt.matplotlib.dates.HourLocator(interval=2))
    # Remove rotation and use horizontal labels
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=0, ha='center')

# Remove x-label from top plot to avoid duplication
ax1.set_xlabel('')

# Adjust layout to accommodate legend
plt.subplots_adjust(top=0.95, bottom=0.18, hspace=0.15)  # Adjusted bottom margin for legend

# Save figure with proper background (figure background remains #fafafa, plot areas are white)
plt.savefig('OSM_MEPS_Max_Ramp_Analysis_PETER.pdf', dpi=300, bbox_inches='tight', 
            facecolor='#fafafa', edgecolor='none')
plt.show()

print(f"\n=== ANALYSIS COMPLETE ===")
print(f"Graph saved as: OSM_MEPS_Max_Ramp_Analysis_PETER.pdf")
print(f"Figure size: 9x10 inches")
print(f"Figure background color: #fafafa")
print(f"Plot area background color: white")
print(f"Sub-hourly grids: 15-minute intervals")
print(f"All font sizes increased by 3 steps")

#----------------------------------------------------------------------------------

# === BELL CURVE SMOOTHING ALGORITHM ===
def bell_curve_smoothing(power_data, battery_power_kw, battery_energy_kwh, 
                        target_ramp_rate=20.0, smoothing_aggression=0.8):
    """
    Advanced smoothing that preserves the natural PV bell curve shape
    while controlling ramp rates
    """
    smoothed_power = power_data.copy()
    battery_power = np.zeros(len(power_data))
    battery_soc = np.zeros(len(power_data))
    battery_soc[0] = battery_energy_kwh / 2  # Start at 50%
    
    # Calculate expected bell curve (clear sky pattern)
    daily_max = power_data.max()
    daily_min = power_data.min()
    
    # Create target bell curve using moving average with clear sky characteristics
    target_bell_curve = power_data.rolling('60min', center=True, min_periods=1).mean()
    
    # Enhance bell curve shape - preserve morning/afternoon symmetry
    morning_data = power_data.between_time('06:00', '12:00')
    afternoon_data = power_data.between_time('12:00', '18:00')
    
    if len(morning_data) > 0 and len(afternoon_data) > 0:
        morning_max = morning_data.max()
        afternoon_max = afternoon_data.max()
        # Adjust target to maintain natural symmetry
        
    max_ramp_kw_per_5min = target_ramp_rate * 300 / 1000
    
    for i in range(1, len(power_data)):
        current_power = power_data.iloc[i]
        previous_smoothed = smoothed_power.iloc[i-1]
        
        # Get time of day for bell curve weighting
        current_time = power_data.index[i]
        hour_decimal = current_time.hour + current_time.minute/60
        
        # Calculate target based on bell curve preservation
        if i > 6:  # Enough data for good moving average
            short_term_avg = power_data.iloc[max(0,i-3):i+1].mean()
            medium_term_avg = target_bell_curve.iloc[i]
            
            # Blend based on time of day - preserve peaks
            if 10 <= hour_decimal <= 14:  # Peak hours
                # Preserve peak shape more aggressively
                bell_weight = 0.7
                ramp_weight = 0.3
            else:  # Morning/afternoon ramps
                # Follow natural ramps more closely
                bell_weight = 0.4
                ramp_weight = 0.6
        else:
            short_term_avg = current_power
            medium_term_avg = current_power
            bell_weight = 0.5
            ramp_weight = 0.5
        
        # Calculate desired power considering bell curve
        bell_target = bell_weight * medium_term_avg + (1-bell_weight) * short_term_avg
        
        # Apply ramp rate limiting to the bell-shaped target
        ramp_limited_target = previous_smoothed + np.clip(
            bell_target - previous_smoothed, 
            -max_ramp_kw_per_5min, 
            max_ramp_kw_per_5min
        )
        
        # Final target blends bell curve and ramp limiting
        final_target = smoothing_aggression * ramp_limited_target + \
                     (1-smoothing_aggression) * bell_target
        
        # Calculate required battery power
        required_battery_power = final_target - current_power
        
        # Apply battery power limits with SOC management
        battery_power[i] = np.clip(required_battery_power, -battery_power_kw, battery_power_kw)
        
        # Update battery state of charge
        energy_change = battery_power[i] * (5/60)
        battery_soc[i] = battery_soc[i-1] - energy_change
        
        # SOC-based power adjustment to maintain charge throughout day
        soc_adjustment = 0
        if battery_soc[i] < battery_energy_kwh * 0.2:  # Too low
            # Reduce discharge or increase charging
            soc_adjustment = min(0, battery_power[i]) * 0.3  # Reduce discharge
        elif battery_soc[i] > battery_energy_kwh * 0.9:  # Too high
            # Reduce charging or increase discharge
            soc_adjustment = max(0, battery_power[i]) * 0.3  # Reduce charging
        
        battery_power[i] -= soc_adjustment
        battery_power[i] = np.clip(battery_power[i], -battery_power_kw, battery_power_kw)
        
        # Final smoothed power
        smoothed_power.iloc[i] = current_power + battery_power[i]
        
        # Ensure SOC stays within bounds
        battery_soc[i] = np.clip(battery_soc[i], 0, battery_energy_kwh)
    
    return smoothed_power, battery_power, battery_soc

# === ENHANCED BELL CURVE DETECTION ===
def detect_daily_pattern(power_data):
    """
    Detect and characterize the daily bell curve pattern
    """
    daily_stats = {
        'sunrise_time': None,
        'sunset_time': None, 
        'peak_time': None,
        'peak_power': power_data.max(),
        'ramp_up_rate': 0,
        'ramp_down_rate': 0
    }
    
    # Find sunrise (first significant power)
    morning_data = power_data.between_time('05:00', '12:00')
    if len(morning_data) > 0:
        sunrise_threshold = daily_stats['peak_power'] * 0.1
        sunrise_times = morning_data[morning_data > sunrise_threshold]
        if len(sunrise_times) > 0:
            daily_stats['sunrise_time'] = sunrise_times.index[0]
    
    # Find sunset (last significant power)  
    afternoon_data = power_data.between_time('12:00', '20:00')
    if len(afternoon_data) > 0:
        sunset_threshold = daily_stats['peak_power'] * 0.1
        sunset_times = afternoon_data[afternoon_data > sunset_threshold]
        if len(sunset_times) > 0:
            daily_stats['sunset_time'] = sunset_times.index[-1]
    
    # Find peak time
    daily_stats['peak_time'] = power_data.idxmax()
    
    return daily_stats

# === APPLY BELL CURVE SMOOTHING ===
print("=== STRATEGIC SMOOTHING ALGORITHM ===")

# Detect daily pattern
daily_pattern = detect_daily_pattern(day_data_osm['AC_Power_kW_osm_total'])
print(f"Detected daily pattern:")
print(f"  - Peak: {daily_pattern['peak_power']:.1f} kW at {daily_pattern['peak_time']}")
print(f"  - Sunrise: {daily_pattern['sunrise_time']}")
print(f"  - Sunset: {daily_pattern['sunset_time']}")

# Apply strategic smoothing
smoothed_bell, battery_bell, soc_bell = bell_curve_smoothing(
    day_data_osm['AC_Power_kW_osm_total'],
    battery_power_rating_osm,
    recommended_energy_osm,
    target_ramp_rate=40.0,  # Slightly more aggressive for natural shape
    smoothing_aggression=0.9  # Balance between smooth and natural
)

# === COMPARE SMOOTHING METHODS ===
# Basic smoothing for comparison
smoothing_window = '30min'
smoothed_basic = day_data_osm['AC_Power_kW_osm_total'].rolling(
    smoothing_window, center=True, min_periods=1).mean()
battery_basic = smoothed_basic - day_data_osm['AC_Power_kW_osm_total']
battery_basic = np.clip(battery_basic, -battery_power_rating_osm, battery_power_rating_osm)
smoothed_basic = day_data_osm['AC_Power_kW_osm_total'] + battery_basic

# === PLOT COMPARISON ===
plt.rcParams["font.family"] = "Garamond"
plt.rcParams["font.size"] = 19
plt.rcParams["font.weight"] = "bold"

fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(8, 13))

for ax in [ax1, ax2, ax3]:
    ax.set_facecolor('#fafafa')
    ax.grid(True, linestyle='--', alpha=0.7)
    # Add black frame all around
    for spine in ax.spines.values():
        spine.set_color('black')
        spine.set_linewidth(1.5)

# Plot 1: Power comparison
ax1.plot(day_data_osm.index, day_data_osm['AC_Power_kW_osm_total'],
         color='red', linewidth=2, label='Original PV Power', alpha=0.8)
ax1.plot(day_data_osm.index, smoothed_basic,
         color='blue', linewidth=2, label='Basic Smoothing', alpha=0.7)
ax1.plot(day_data_osm.index, smoothed_bell,
         color='maroon', linewidth=2.5, label='Strategic smoothing')

ax1.set_ylabel('Power (kW)', fontweight='bold')
ax1.legend(framealpha=0.9, fontsize=15)  # Increased legend font size


# Plot 2: Ramp rate comparison
original_ramp = day_data_osm['Ramp_W_per_s_osm']
basic_ramp = smoothed_basic.diff() * 1000 / 300
bell_ramp = smoothed_bell.diff() * 1000 / 300

ax2.plot(day_data_osm.index, original_ramp,
         color='red', linewidth=2, alpha=0.8, label='Original Ramp')  # Changed to black
ax2.plot(day_data_osm.index, basic_ramp,
         color='blue', linewidth=2, label='Basic Smoothing', alpha=0.7)
ax2.plot(day_data_osm.index, bell_ramp,
         color='maroon', linewidth=2, label='Strategic smoothing')

ax2.set_ylabel('Ramp Rate (W/s)', fontweight='bold')
ax2.legend(framealpha=0.9, fontsize=15)  # Increased legend font size

ax2.axhline(y=0, color='gray', linestyle='-', alpha=0.3)

# Plot 3: Battery usage - FIXED VERSION
ax3.plot(day_data_osm.index, battery_basic,
         color='blue', linewidth=2, label='Basic Smoothing Battery', alpha=0.7)
ax3.plot(day_data_osm.index, battery_bell,
         color='maroon', linewidth=2, label='Strategic smoothing Battery')

# FIX: Convert numpy arrays to pandas Series for fill_between
battery_bell_series = pd.Series(battery_bell, index=day_data_osm.index)
battery_basic_series = pd.Series(battery_basic, index=day_data_osm.index)

# Now use .where() on pandas Series
ax3.fill_between(day_data_osm.index, 0, battery_bell_series.where(battery_bell_series > 0),
                 alpha=0.3, color='green', label='Charging')
ax3.fill_between(day_data_osm.index, 0, battery_bell_series.where(battery_bell_series < 0),
                 alpha=0.3, color='magenta', label='Discharging')

ax3.set_ylabel('Battery Power (kW)', fontweight='bold')
ax3.set_xlabel('Time of Day', fontweight='bold')
ax3.legend(framealpha=0.9, fontsize=14)  # Increased legend font size

ax3.axhline(y=0, color='gray', linestyle='-', alpha=0.3)

# Format x-axis
for ax in [ax1, ax2, ax3]:
    ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%H:%M'))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=1, ha='right')

plt.tight_layout()

# === PERFORMANCE METRICS ===
print(f"\n=== PERFORMANCE COMPARISON ===")
print(f"Original System:")
print(f"  - Max Ramp: {original_ramp.abs().max():.1f} W/s")
print(f"  - Power Range: {day_data_osm['AC_Power_kW_osm_total'].max() - day_data_osm['AC_Power_kW_osm_total'].min():.1f} kW")

print(f"\nBasic Smoothing:")
print(f"  - Max Ramp: {basic_ramp.abs().max():.1f} W/s")
print(f"  - Ramp Reduction: {((original_ramp.abs().max() - basic_ramp.abs().max()) / original_ramp.abs().max() * 100):.1f}%")

print(f"\nStrategic Smoothing:")
print(f"  - Max Ramp: {bell_ramp.abs().max():.1f} W/s")
print(f"  - Ramp Reduction: {((original_ramp.abs().max() - bell_ramp.abs().max()) / original_ramp.abs().max() * 100):.1f}%")
print(f"  - Peak Preservation: {((smoothed_bell.max() - smoothed_basic.max()) / smoothed_basic.max() * 100):+.1f}% vs basic")

print(f"\nBattery Usage:")
print(f"  - Max Charge (Strategic): {battery_bell.max():.1f} kW")
print(f"  - Max Discharge (Strategic): {abs(battery_bell.min()):.1f} kW")
print(f"  - Battery Utilization: {max(abs(battery_bell.max()), abs(battery_bell.min())) / battery_power_rating_osm * 100:.1f}%")

# === ADDITIONAL BELL CURVE ANALYSIS ===
print(f"\n=== BELL CURVE PRESERVATION ANALYSIS ===")
# Calculate how well the bell curve shape is preserved
original_peak_time = day_data_osm['AC_Power_kW_osm_total'].idxmax()
bell_peak_time = smoothed_bell.idxmax()
basic_peak_time = smoothed_basic.idxmax()

print(f"Peak Time Alignment:")
print(f"  - Original: {original_peak_time}")
print(f"  - Strategic: {bell_peak_time}")
print(f"  - Basic: {basic_peak_time}")

# Calculate morning vs afternoon symmetry
morning_power = day_data_osm['AC_Power_kW_osm_total'].between_time('06:00', '12:00').mean()
afternoon_power = day_data_osm['AC_Power_kW_osm_total'].between_time('12:00', '18:00').mean()
symmetry_ratio = morning_power / afternoon_power

morning_bell = smoothed_bell.between_time('06:00', '12:00').mean()
afternoon_bell = smoothed_bell.between_time('12:00', '18:00').mean()
symmetry_bell = morning_bell / afternoon_bell

print(f"Morning-Afternoon Symmetry:")
print(f"  - Original: {symmetry_ratio:.3f}")
print(f"  - Strategic: {symmetry_bell:.3f}")
print(f"  - Closer to 1.0 = better symmetry preservation")

plt.savefig('Strategic_Smoothing_Comparison_PETER.pdf', dpi=300, bbox_inches='tight',
            facecolor='#fafafa', edgecolor='none')
plt.show()

#--------------------------------------------------------------------------------------------------------------

# --- Filter for first 4 days of August and December 2024 ---
df_aug = df[(df.index >= '2024-08-01') & (df.index < '2024-08-05')]
df_dec = df[(df.index >= '2024-12-01') & (df.index < '2024-12-05')]

# Function to plot all irradiance components, AC Power, and Ramp Rate
def plot_all_metrics(df_plot, month_name):
    plt.rcParams["font.family"] = "Garamond"
    
    # Create subplots: Irradiance, AC Power, Ramp Rate
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(13, 17), facecolor='#fafafa')
    
    for ax in [ax1, ax2, ax3]:
        ax.set_facecolor('#fafafa')
    
    # Top subplot: All Irradiance Components
    ax1.plot(df_plot.index, df_plot["dni"], color="red", 
             label="DNI (W/m²)", linewidth=2.0)
    ax1.plot(df_plot.index, df_plot["ghi"], color="blue", 
             label="GHI (W/m²)", linewidth=2.0)
    ax1.plot(df_plot.index, df_plot["dhi"], color="brown", 
             label="DHI (W/m²)", linewidth=2.75)
    ax1.set_ylabel("Irradiance (W/m²)", fontsize=19)
    ax1.legend(fontsize=16, loc='upper right')
    ax1.grid(True, linestyle="--", alpha=0.5)
   
    
    # Middle subplot: AC Power Output
    ax2.plot(df_plot.index, df_plot["AC_Power_kW_pvlib_total"],
             color="orange", label="PVLIB AC Power (kW)", linewidth=2.50)
    ax2.plot(df_plot.index, df_plot["AC_Power_kW_osm_total"],
             color="green", label="OSM-MEPS AC Power (kW)", linewidth=2.50)
    ax2.set_ylabel("AC Power (kW)", fontsize=19)
    ax2.legend(fontsize=16, loc='upper right', bbox_to_anchor=(1.0, 1.0))
    ax2.grid(True, linestyle="--", alpha=0.5)
   
    # Bottom subplot: Ramp Rate
    ax3.plot(df_plot.index, df_plot["Ramp_W_per_s_pvlib"],
            color="orange", label="PVLIB Ramp Rate (W/s)", linewidth=1.5)
    ax3.plot(df_plot.index, df_plot["Ramp_W_per_s_osm"],
            color="darkgreen", label="OSM-MEPS Ramp Rate (W/s)", linewidth=1.5)
    ax3.set_xlabel("Date", fontsize=19)
    ax3.set_ylabel("Ramp Rate (W/s)", fontsize=19)
    
    # Place ramp rate legend below the bottom plot
    ax3.legend(fontsize=16, loc='upper center', bbox_to_anchor=(0.5, -0.15),
              ncol=2, framealpha=1.0, fancybox=True, shadow=True)
    ax3.grid(True, linestyle="--", alpha=0.5)

    # PROPER DATE FORMATTING - One date at midnight for each day
    for ax in [ax1, ax2, ax3]:
        # Set major locator to show one tick per day at midnight
        ax.xaxis.set_major_locator(plt.matplotlib.dates.DayLocator(interval=1))
        
        # Format as "Month Day" (e.g., "Aug 01", "Aug 02")
        ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%b %d'))
        
        # Set minor locator to show hours for grid lines (optional)
        ax.xaxis.set_minor_locator(plt.matplotlib.dates.HourLocator(interval=6))
        
        # Bold tick labels
        ax.tick_params(axis='x', labelsize=19, rotation=0)  # No rotation for horizontal dates
        ax.tick_params(axis='y', labelsize=19)
        
        # Make all labels bold
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_fontweight('bold')

    # Adjust layout to accommodate legend below
    plt.tight_layout(rect=[0, 0.01, 1, 0.95])
    plt.savefig(f"Smart_grid_Complete_Analysis_{month_name}_1-4_PETER.pdf", format="pdf", bbox_inches='tight')
    plt.show()

# --- Plot August ---
plot_all_metrics(df_aug, "August")

# --- Plot December ---
plot_all_metrics(df_dec, "December")

#--------------------------------------------------------------------------------------------------------

# === IMPORT LIBRARIES ===
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import pvlib
from pvlib.irradiance import get_total_irradiance
from pvlib.temperature import sapm_cell

# === LOAD WEATHER DATA - SHIFT CSV TIME BY +2 HOURS ===
file_path = 'csv_-29.815268_30.946439_fixed_23_0_PT5M.csv'
df = pd.read_csv(file_path)
df['period_end'] = pd.to_datetime(df['period_end'])  # Load with original timezone
df.set_index('period_end', inplace=True)
df = df[(df.index >= '2024-01-01') & (df.index < '2025-01-01')]

# Shift time by +2 hours
df.index = df.index + pd.Timedelta(hours=2)

# === FILTER DATA FOR YEAR 2024 ONLY ===
df = df[(df.index >= '2024-01-01') & (df.index < '2025-01-01')]

# === ENSURE REQUIRED METEOROLOGICAL COLUMNS EXIST ===
required_columns = ['dni', 'ghi', 'dhi', 'air_temp', 'albedo', 'zenith', 'azimuth',
                    'cloud_opacity', 'relative_humidity', 'wind_speed_10m']
for col in required_columns:
    if col not in df.columns:
        print(f"Warning: Column '{col}' is missing. Filling with zeros.")
        df[col] = 0

# === PV SYSTEM PARAMETERS ===
latitude = -29.815268
longitude = 30.946439
panel_power_max = 600      # W
inverter_efficiency = 0.95
temp_coeff = -0.0045
stc_irradiance = 1000       # W/m^2
losses = 1

# Total panels across all segments
num_panels_total = 32+32+32+32+64  

# === SOLAR POSITION ===
solar_position = pvlib.solarposition.get_solarposition(df.index, latitude, longitude)

# === DEFINE ROOFTOP FIELD SEGMENTS ===
field_segments = [
    {"tilt": 5.6, "azimuth": 319.88214, "num_modules": 32},
    {"tilt": 2.8, "azimuth": 146.61220, "num_modules": 32},
    {"tilt": 5.0, "azimuth": 326.42346, "num_modules": 32},
    {"tilt": 3.0, "azimuth": 315.20587, "num_modules": 32},
    {"tilt": 3.0, "azimuth": 134.65346, "num_modules": 64},
]

# === INITIALIZE TOTAL POWER COLUMNS ===
df["AC_Power_kW_pvlib_total"] = 0
df["AC_Power_kW_osm_total"] = 0

# === LOOP OVER SEGMENTS ===
for seg in field_segments:
    tilt = seg["tilt"]
    azimuth = seg["azimuth"]
    num_panels = seg["num_modules"]

    # --- PVLIB MODEL ---
    poa = get_total_irradiance(
        surface_tilt=tilt,
        surface_azimuth=azimuth,
        dni=df["dni"],
        ghi=df["ghi"],
        dhi=df["dhi"],
        solar_zenith=solar_position["apparent_zenith"],
        solar_azimuth=solar_position["azimuth"]
    )
    poa_irradiance = poa["poa_global"]

    temp_cell = sapm_cell(poa_irradiance, df["air_temp"], df["wind_speed_10m"], -3.47, -0.0594, 3)

    dc_power_pvlib = poa_irradiance / stc_irradiance * num_panels * panel_power_max * \
                     (1 + temp_coeff * (temp_cell - 25))
    ac_power = dc_power_pvlib * inverter_efficiency * losses
    df["AC_Power_kW_pvlib_total"] += ac_power / 1000  # kW

    # --- OSM-MEPS MODEL ---
    tilt_rad = np.radians(tilt)
    az_rad = np.radians(azimuth)
    zen_rad = np.radians(df['zenith'])
    sun_az_rad = np.radians(df['azimuth'])

    aoi = np.degrees(np.arccos(
        np.cos(zen_rad) * np.cos(tilt_rad) +
        np.sin(zen_rad) * np.sin(tilt_rad) * np.cos(sun_az_rad - az_rad)
    ))
    aoi = np.clip(aoi, 0, 90)

    poa_direct = df['dni'] * np.cos(np.radians(aoi)) * (1 - df['cloud_opacity'] / 100)
    poa_direct = poa_direct.clip(lower=0)
    poa_diffuse = df['dhi'] * (1 + np.cos(tilt_rad)) / 2
    poa_reflected = df['ghi'] * df['albedo'] * (1 - np.cos(tilt_rad)) / 2
    poa_total = poa_direct + poa_diffuse + poa_reflected

    module_temp = 45 + poa_total / 1000 * (28 - df['air_temp'])
    dc_power_osm = panel_power_max * (1 + temp_coeff * (module_temp - 45))
    dc_power_osm *= poa_total / stc_irradiance
    dc_power_osm *= (1 - 0.001 * df['relative_humidity'])
    ac_power_osm = dc_power_osm * inverter_efficiency
    scaled_power = ac_power_osm * num_panels
    actual_power = scaled_power * (1 - 0.01)
    df["AC_Power_kW_osm_total"] += actual_power / 1000  # kW

# === ENERGY CALCULATION (5-min intervals to kWh) ===
df["Energy_kWh_pvlib"] = df["AC_Power_kW_pvlib_total"] * (5/60)
df["Energy_kWh_osm"] = df["AC_Power_kW_osm_total"] * (5/60)

# === RESAMPLE TO HOURLY ENERGY ===
hourly_energy_pvlib = df["Energy_kWh_pvlib"].resample('h').sum()
hourly_energy_osm = df["Energy_kWh_osm"].resample('h').sum()

# === PLOTTING HOURLY ENERGY ===
fig, ax = plt.subplots(figsize=(13, 6), facecolor='#f0f0f0')
ax.set_facecolor('#f0f0f0')
ax.plot(hourly_energy_pvlib.index, hourly_energy_pvlib, label="PVLIB", color='orange', linewidth=1.2)
ax.plot(hourly_energy_osm.index, hourly_energy_osm, label="OSM-MEPS", color='green', linewidth=1.2)
ax.set_xlabel("Date", fontsize=18)
ax.set_ylabel("Hourly Energy (kWh)", fontsize=18)

ax.legend(fontsize=14)
ax.grid(True, linestyle='--', alpha=0.5)
plt.tight_layout()
plt.savefig("Hourly_Energy.pdf", format='pdf')
plt.show()


#-------------------------------------------------------------------------------------------------------------------

# === PLOT AC POWER (kW) ONLY - SIMPLER VERSION ===
plt.rcParams["font.family"] = "Garamond"
fig, ax = plt.subplots(figsize=(8,6), facecolor='#fafafa')
ax.set_facecolor('#fafafa')

# Plot AC Power from both models with reduced linewidth
ax.plot(df.index, df["AC_Power_kW_pvlib_total"], 
        color="orange", label="PVLIB AC Power", linewidth=1.2)  # Reduced from 2.0
ax.plot(df.index, df["AC_Power_kW_osm_total"], 
        color="green", label="OSM-MEPS AC Power", linewidth=1.2)  # Reduced from 2.0

ax.set_xlabel("Date", fontsize=18, fontweight='bold')
ax.set_ylabel("AC Power (kW) at 5 Minutes ", fontsize=18, fontweight='bold')

ax.grid(True, linestyle='--', alpha=0.5)

# Format ticks
ax.tick_params(axis='x', labelsize=17)
ax.tick_params(axis='y', labelsize=17)
for label in ax.get_xticklabels() + ax.get_yticklabels():
    label.set_fontweight('bold')

# Calculate statistics
pvlib_max = df['AC_Power_kW_pvlib_total'].max()
pvlib_avg = df['AC_Power_kW_pvlib_total'].mean()
pvlib_min = df['AC_Power_kW_pvlib_total'].min()

osm_max = df['AC_Power_kW_osm_total'].max()
osm_avg = df['AC_Power_kW_osm_total'].mean()
osm_min = df['AC_Power_kW_osm_total'].min()

# Create two-column legend elements
from matplotlib.patches import Patch

legend_elements = [
    # Left column: Power lines
    plt.Line2D([0], [0], color='orange', lw=3, label='PVLIB AC Power'),
    plt.Line2D([0], [0], color='green', lw=3, label='OSM-MEPS AC Power'),

]

# Place legend below the graph with two columns
legend = ax.legend(handles=legend_elements, 
                  loc='upper center', 
                  bbox_to_anchor=(0.5, -0.17),  # Adjusted position
                  ncol=2,  # Two columns
                  fontsize=15,
                  frameon=True,
                  fancybox=True,
                  shadow=True,
                  facecolor='white',
                  framealpha=0.9,
                  columnspacing=2.0,  # Space between columns
                  handlelength=1.5)   # Adjust handle length

plt.tight_layout(rect=[0, 0.12, 1, 0.95])  # Adjusted for new legend position
plt.savefig("SMARTGRID_AC_Power_kW_5min_PETER.pdf", format='pdf', bbox_inches='tight', dpi=700)
plt.show()

# Print to console
print("\n" + "="*50)
print("AC POWER STATISTICS")
print("="*50)
print(f"PVLIB Model:  Max={pvlib_max:.2f} kW, Avg={pvlib_avg:.2f} kW, Min={pvlib_min:.2f} kW")
print(f"OSM-MEPS Model: Max={osm_max:.2f} kW, Avg={osm_avg:.2f} kW, Min={osm_min:.2f} kW")
print("="*50)

#-----------------------------------------------------------------------------------------------------

# === IMPORT LIBRARIES ===
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import pvlib
from pvlib.irradiance import get_total_irradiance
from pvlib.temperature import sapm_cell
from pvlib.pvsystem import pvwatts_dc
from scipy import stats
import scipy.stats as stats
from statsmodels.stats.multicomp import pairwise_tukeyhsd

# === LOAD AURORA 2021 DATA ===
aurora_csv = 'Aurora_Multi_Year_Averages_2021_2022.csv'
aurora_avg_df = pd.read_csv(aurora_csv)
aurora_dates = pd.date_range(start='2024-01-01', periods=365, freq='D')
aurora_energy_2021 = pd.Series(aurora_avg_df['Year_2021_kWh'].values, index=aurora_dates, name='Aurora_2021')

# === LOAD WEATHER DATA - SHIFT CSV TIME BY +2 HOURS ===
file_path = 'csv_-29.815268_30.946439_fixed_23_0_PT5M.csv'
df = pd.read_csv(file_path)
df['period_end'] = pd.to_datetime(df['period_end'])  # Load with original timezone
df.set_index('period_end', inplace=True)
df = df[(df.index >= '2024-01-01') & (df.index < '2025-01-01')]

# Shift time by +2 hours
df.index = df.index + pd.Timedelta(hours=2)

# === FILL MISSING COLUMNS ===
for col in ['dni','ghi','dhi','air_temp','albedo','zenith','azimuth','cloud_opacity','relative_humidity','wind_speed_10m']:
    if col not in df.columns:
        df[col] = 0

# === PV SYSTEM PARAMETERS ===
latitude = -29.815268
longitude = 30.946439
panel_power_max = 600      # W per module
inverter_efficiency = 0.95
temp_coeff = -0.0045
stc_irradiance = 1000
num_panels_total = 32+32+32+32+64
total_system_capacity_kw = num_panels_total * panel_power_max / 1000

print(f"System Configuration:")
print(f"Total panels: {num_panels_total}")
print(f"Panel power: {panel_power_max}W each")
print(f"Total DC capacity: {total_system_capacity_kw:.1f} kW")

# === SOLAR POSITION ===
solar_position = pvlib.solarposition.get_solarposition(df.index, latitude, longitude)

# === ROOFTOP SEGMENTS ===
field_segments = [
    {"tilt": 5.6, "azimuth": 319.88214, "num_modules": 32},
    {"tilt": 2.8, "azimuth": 146.61220, "num_modules": 32},
    {"tilt": 5.0, "azimuth": 326.42346, "num_modules": 32},
    {"tilt": 3.0, "azimuth": 315.20587, "num_modules": 32},
    {"tilt": 3.0, "azimuth": 134.65346, "num_modules": 64},
]

# === INITIALIZE TOTAL POWER COLUMNS ===
df["AC_Power_kW_pvlib_total"] = 0
df["AC_Power_kW_osm_total"] = 0
df["AC_Power_kW_pvwatts_total"] = 0

print("\n=== PROCESSING SEGMENTS ===")

# === LOOP OVER SEGMENTS ===
for i, seg in enumerate(field_segments):
    tilt = seg["tilt"]
    azimuth = seg["azimuth"]
    num_panels = seg["num_modules"]
    
    print(f"Segment {i+1}: {num_panels} panels, tilt={tilt}°, azimuth={azimuth}°")

    # --- PVLIB ---
    poa = get_total_irradiance(
        surface_tilt=tilt,
        surface_azimuth=azimuth,
        dni=df["dni"],
        ghi=df["ghi"],
        dhi=df["dhi"],
        solar_zenith=solar_position["apparent_zenith"],
        solar_azimuth=solar_position["azimuth"]
    )
    poa_irradiance = poa["poa_global"]
    temp_cell = sapm_cell(poa_irradiance, df["air_temp"], df["wind_speed_10m"], -2.98, -0.0471, 1)
    
    # UNIFORM SCALING: Apply panel count at the DC power level
    dc_power_pvlib = poa_irradiance / stc_irradiance * panel_power_max * num_panels * (1 + temp_coeff * (temp_cell - 25))
    ac_power_pvlib = dc_power_pvlib * inverter_efficiency
    df["AC_Power_kW_pvlib_total"] += ac_power_pvlib / 1000  # Convert to kW

    # --- OSM-MEPS ---
    tilt_rad = np.radians(tilt)
    az_rad = np.radians(azimuth)
    zen_rad = np.radians(df['zenith'])
    sun_az_rad = np.radians(df['azimuth'])
    aoi = np.degrees(np.arccos(np.cos(zen_rad)*np.cos(tilt_rad) + np.sin(zen_rad)*np.sin(tilt_rad)*np.cos(sun_az_rad - az_rad)))
    aoi = np.clip(aoi, 0, 90)
    poa_direct = df['dni']*np.cos(np.radians(aoi))*(1 - df['cloud_opacity']/100)
    poa_direct = poa_direct.clip(lower=0)
    poa_diffuse = df['dhi']*(1 + np.cos(tilt_rad))/2
    poa_reflected = df['ghi']*df['albedo']*(1 - np.cos(tilt_rad))/2
    poa_total = poa_direct + poa_diffuse + poa_reflected
    module_temp = 45 + poa_total/1000*(28 - df['air_temp'])
    
    # UNIFORM SCALING: Apply panel count at the DC power level
    dc_power_osm = panel_power_max * num_panels * (1 + temp_coeff*(module_temp - 45)) * poa_total/stc_irradiance * (1 - 0.002*df['relative_humidity'])
    ac_power_osm = dc_power_osm * inverter_efficiency
    df["AC_Power_kW_osm_total"] += ac_power_osm / 1000  # Convert to kW

    # --- PVWATTS (SAM-style AC) ---
    # UNIFORM SCALING: Apply panel count at the DC power level
    dc_power_pvwatts = pvwatts_dc(poa_irradiance, temp_cell, pdc0=panel_power_max * num_panels, gamma_pdc=temp_coeff, temp_ref=25)
    ac_power_pvwatts = dc_power_pvwatts * inverter_efficiency * (1 - 0.01)  # 1% system losses
    df["AC_Power_kW_pvwatts_total"] += ac_power_pvwatts / 1000  # Convert to kW

# === DAILY ENERGY CALCULATION ===
# Convert 5-minute power to energy (kWh)
time_interval_hours = 5/60  # 5 minutes in hours
df["Energy_kWh_pvlib"] = df["AC_Power_kW_pvlib_total"] * time_interval_hours
df["Energy_kWh_osm"] = df["AC_Power_kW_osm_total"] * time_interval_hours
df["Energy_kWh_pvwatts"] = df["AC_Power_kW_pvwatts_total"] * time_interval_hours

# Resample to daily sums
daily_energy_pvlib = df["Energy_kWh_pvlib"].resample('D').sum()
daily_energy_osm = df["Energy_kWh_osm"].resample('D').sum()
daily_energy_pvwatts = df["Energy_kWh_pvwatts"].resample('D').sum()

# Calculate annual totals
annual_energy_pvlib = daily_energy_pvlib.sum()
annual_energy_osm = daily_energy_osm.sum()
annual_energy_pvwatts = daily_energy_pvwatts.sum()
annual_energy_aurora = aurora_energy_2021.sum()

print(f"\n=== ANNUAL ENERGY RESULTS ===")
print(f"PVLIB: {annual_energy_pvlib:,.0f} kWh")
print(f"OSM-MEPS: {annual_energy_osm:,.0f} kWh")
print(f"PVWatts: {annual_energy_pvwatts:,.0f} kWh")
print(f"Aurora (2021): {annual_energy_aurora:,.0f} kWh")

# === STATISTICAL ANALYSIS ===
print(f"\n=== STATISTICAL ANALYSIS ===")

# Prepare data for ANOVA
models_data = {
    'PVLIB': daily_energy_pvlib.dropna(),
    'OSM-MEPS': daily_energy_osm.dropna(),
    'PVWatts': daily_energy_pvwatts.dropna(),
    'Aurora': aurora_energy_2021.dropna()
}

# Create arrays for ANOVA
all_data = []
all_labels = []
for model_name, data in models_data.items():
    all_data.extend(data.values)
    all_labels.extend([model_name] * len(data))

# Perform ANOVA
f_stat, p_value = stats.f_oneway(*[models_data[model] for model in models_data.keys()])

print(f"One-Way ANOVA Results:")
print(f"F-statistic: {f_stat:.4f}")
print(f"P-value: {p_value:.4f}")

if p_value < 0.05:
    print("Significant differences exist between models (p < 0.05)")
    
    # Post-hoc Tukey HSD test
    tukey_results = pairwise_tukeyhsd(all_data, all_labels, alpha=0.05)
    print(f"\nTukey HSD Post-hoc Test:")
    print(tukey_results)
else:
    print("No significant differences between models (p ≥ 0.05)")

# Descriptive statistics
print(f"\n=== DESCRIPTIVE STATISTICS ===")
for model_name, data in models_data.items():
    print(f"{model_name}:")
    print(f"  Mean: {data.mean():.1f} kWh/day")
    print(f"  Std: {data.std():.1f} kWh/day")
    print(f"  Min: {data.min():.1f} kWh/day")
    print(f"  Max: {data.max():.1f} kWh/day")
    print(f"  Annual: {data.sum():,.0f} kWh")

# === PLOTTING ===
plt.rcParams["font.family"] = "Garamond"
fig, ax = plt.subplots(figsize=(13, 8), facecolor='#f0f0f0')
ax.set_facecolor('#f0f0f0')

# Plot with updated legend labels
ax.plot(daily_energy_pvlib.index, daily_energy_pvlib, 
        label="PVLIB (2024)", 
        color='red', 
        linewidth=2.5,
        linestyle='--')

ax.plot(daily_energy_osm.index, daily_energy_osm, 
        label="OSM-MEPS (2024)", 
        color='green', 
        linewidth=2.5,
        linestyle='-')

ax.plot(daily_energy_pvwatts.index, daily_energy_pvwatts, 
        label="PVWatts (2024)", 
        color='orange', 
        linewidth=2.5,
        linestyle=':')

ax.plot(aurora_energy_2021.index, aurora_energy_2021, 
        label="Aurora Solar (2021)",  # Updated label
        color='blue', 
        linewidth=2.5, 
        alpha=0.8,
        linestyle='-.')

ax.set_xlabel("Date", fontsize=20, fontweight='bold')
ax.set_ylabel("Daily Energy (kWh)", fontsize=20, fontweight='bold')

ax.grid(True, linestyle='--', alpha=0.3)
ax.tick_params(axis='both', labelsize=20)

# Format x-axis to show months
ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%b'))
plt.xticks(rotation=0)

# Set consistent y-axis limits
y_max = max(daily_energy_pvlib.max(), daily_energy_osm.max(), 
            daily_energy_pvwatts.max(), aurora_energy_2021.max()) * 1.1
ax.set_ylim(0, y_max)

# Legend below the graph
ax.legend(fontsize=14, loc='upper center', bbox_to_anchor=(0.5, 1.0), ncol=2,
          frameon=True, fancybox=True, shadow=True, framealpha=0.9)

plt.tight_layout()
plt.savefig("Aurora_PVlib_Osmmeps_PVwatts.pdf", format="pdf", bbox_inches='tight', dpi=700)
plt.show()

# Print final statistics summary
print(f"\n=== FINAL SUMMARY ===")
print(f"System: {total_system_capacity_kw:.1f} kW DC, {num_panels_total} panels")
print(f"ANOVA p-value: {p_value:.4f}")
print(f"Annual Energy Comparison:")
for model_name, data in models_data.items():
    print(f"  {model_name}: {data.sum():,.0f} kWh")

#------------------------------------------------------------------------------------------------

# === OSM-MEPS WITH ORIGINAL VALIDATED PARAMETERS ===
for i, seg in enumerate(field_segments):
    tilt = seg["tilt"]
    azimuth = seg["azimuth"]
    num_panels = seg["num_modules"]
    
    print(f"Segment {i+1}: {num_panels} panels, tilt={tilt}°, azimuth={azimuth}°")

    # --- OSM-MEPS ORIGINAL VALIDATED MODEL ---
    tilt_rad = np.radians(tilt)
    az_rad = np.radians(azimuth)
    zen_rad = np.radians(df['zenith'])
    sun_az_rad = np.radians(df['azimuth'])
    aoi = np.degrees(np.arccos(np.cos(zen_rad)*np.cos(tilt_rad) + np.sin(zen_rad)*np.sin(tilt_rad)*np.cos(sun_az_rad - az_rad)))
    aoi = np.clip(aoi, 0, 90)
    poa_direct = df['dni']*np.cos(np.radians(aoi))*(1 - df['cloud_opacity']/100)
    poa_direct = poa_direct.clip(lower=0)
    poa_diffuse = df['dhi']*(1 + np.cos(tilt_rad))/2
    poa_reflected = df['ghi']*df['albedo']*(1 - np.cos(tilt_rad))/2
    poa_total = poa_direct + poa_diffuse + poa_reflected
    module_temp = 45 + poa_total/1000*(28 - df['air_temp'])
    
    # ORIGINAL VALIDATED OSM-MEPS DC POWER CALCULATION
    dc_power_osm = panel_power_max * num_panels * (1 + temp_coeff*(module_temp - 45)) * poa_total/stc_irradiance * (1 - 0.002*df['relative_humidity'])
    ac_power_osm = dc_power_osm * inverter_efficiency
    df["AC_Power_kW_osm_total"] += ac_power_osm / 1000  # Convert to kW

# === DEBUGGING OSM-MEPS CALCULATION ===
print(f"\n=== OSM-MEPS DEBUGGING ===")
print(f"Expected annual energy: 146,413 kWh")
print(f"Calculated annual energy: {annual_energy_osm:,.0f} kWh")
print(f"Difference: {146413 - annual_energy_osm:,.0f} kWh")

# Check key parameters that could cause discrepancy
print(f"\n=== DATA QUALITY CHECK ===")
print(f"Data coverage: {len(df)} timesteps")
print(f"Date range: {df.index.min()} to {df.index.max()}")
print(f"Missing values in key columns:")
for col in ['dni', 'ghi', 'dhi', 'air_temp', 'cloud_opacity', 'relative_humidity']:
    missing = df[col].isna().sum()
    print(f"  {col}: {missing} missing ({missing/len(df)*100:.1f}%)")

# Check if weather data has reasonable ranges
print(f"\n=== WEATHER DATA RANGES ===")
print(f"GHI: {df['ghi'].min():.1f} to {df['ghi'].max():.1f} W/m²")
print(f"DNI: {df['dni'].min():.1f} to {df['dni'].max():.1f} W/m²") 
print(f"DHI: {df['dhi'].min():.1f} to {df['dhi'].max():.1f} W/m²")
print(f"Air temp: {df['air_temp'].min():.1f} to {df['air_temp'].max():.1f} °C")
print(f"Cloud opacity: {df['cloud_opacity'].min():.1f} to {df['cloud_opacity'].max():.1f} %")
print(f"Relative humidity: {df['relative_humidity'].min():.1f} to {df['relative_humidity'].max():.1f} %")

# Check power outputs
print(f"\n=== POWER OUTPUT ANALYSIS ===")
print(f"Max OSM-MEPS power: {df['AC_Power_kW_osm_total'].max():.2f} kW")
print(f"System capacity: {total_system_capacity_kw:.1f} kW")
print(f"Capacity utilization: {df['AC_Power_kW_osm_total'].max()/total_system_capacity_kw*100:.1f}%")

# Check daily patterns
peak_day = df['AC_Power_kW_osm_total'].idxmax()
print(f"Peak power day: {peak_day}")
print(f"Peak day max power: {df.loc[peak_day, 'AC_Power_kW_osm_total']:.2f} kW")

# Check if timezone shift is causing issues
print(f"\n=== TIMEZONE VERIFICATION ===")
print(f"Data timezone: {df.index.tz}")
print(f"First few timestamps:")
print(df.index[:10])

# Check for negative power values (shouldn't exist)
negative_power = (df['AC_Power_kW_osm_total'] < 0).sum()
print(f"Negative power values: {negative_power}")

# Check energy calculation
print(f"\n=== ENERGY CALCULATION VERIFICATION ===")
print(f"Time interval: {time_interval_hours} hours")
print(f"Total timesteps: {len(df)}")
print(f"Total hours: {len(df) * time_interval_hours:.1f}")
print(f"Average OSM-MEPS power: {df['AC_Power_kW_osm_total'].mean():.2f} kW")
print(f"Estimated annual energy from avg power: {df['AC_Power_kW_osm_total'].mean() * 8760:.0f} kWh")

# Compare with your expected 146,413 kWh
expected_avg_power = 146413 / 8760
print(f"Required avg power for 146,413 kWh: {expected_avg_power:.2f} kW")
print(f"Current avg power ratio: {df['AC_Power_kW_osm_total'].mean() / expected_avg_power:.2f}")

#---------------------------------------------------------------------------------------------------------------


# === OSM-MEPS WITH ORIGINAL VALIDATED PARAMETERS ===
for i, seg in enumerate(field_segments):
    tilt = seg["tilt"]
    azimuth = seg["azimuth"]
    num_panels = seg["num_modules"]
    
    print(f"Segment {i+1}: {num_panels} panels, tilt={tilt}°, azimuth={azimuth}°")

    # --- OSM-MEPS ORIGINAL VALIDATED MODEL ---
    tilt_rad = np.radians(tilt)
    az_rad = np.radians(azimuth)
    zen_rad = np.radians(df['zenith'])
    sun_az_rad = np.radians(df['azimuth'])
    aoi = np.degrees(np.arccos(np.cos(zen_rad)*np.cos(tilt_rad) + np.sin(zen_rad)*np.sin(tilt_rad)*np.cos(sun_az_rad - az_rad)))
    aoi = np.clip(aoi, 0, 90)
    poa_direct = df['dni']*np.cos(np.radians(aoi))*(1 - df['cloud_opacity']/100)
    poa_direct = poa_direct.clip(lower=0)
    poa_diffuse = df['dhi']*(1 + np.cos(tilt_rad))/2
    poa_reflected = df['ghi']*df['albedo']*(1 - np.cos(tilt_rad))/2
    poa_total = poa_direct + poa_diffuse + poa_reflected
    module_temp = 45 + poa_total/1000*(28 - df['air_temp'])
    
    # ORIGINAL VALIDATED OSM-MEPS DC POWER CALCULATION
    dc_power_osm = panel_power_max * num_panels * (1 + temp_coeff*(module_temp - 45)) * poa_total/stc_irradiance * (1 - 0.002*df['relative_humidity'])
    ac_power_osm = dc_power_osm * inverter_efficiency
    df["AC_Power_kW_osm_total"] += ac_power_osm / 1000  # Convert to kW

# === DEBUGGING OSM-MEPS CALCULATION ===
print(f"\n=== OSM-MEPS DEBUGGING ===")
print(f"Expected annual energy: 146,413 kWh")
print(f"Calculated annual energy: {annual_energy_osm:,.0f} kWh")
print(f"Difference: {146413 - annual_energy_osm:,.0f} kWh")

# Check key parameters that could cause discrepancy
print(f"\n=== DATA QUALITY CHECK ===")
print(f"Data coverage: {len(df)} timesteps")
print(f"Date range: {df.index.min()} to {df.index.max()}")
print(f"Missing values in key columns:")
for col in ['dni', 'ghi', 'dhi', 'air_temp', 'cloud_opacity', 'relative_humidity']:
    missing = df[col].isna().sum()
    print(f"  {col}: {missing} missing ({missing/len(df)*100:.1f}%)")

# Check if weather data has reasonable ranges
print(f"\n=== WEATHER DATA RANGES ===")
print(f"GHI: {df['ghi'].min():.1f} to {df['ghi'].max():.1f} W/m²")
print(f"DNI: {df['dni'].min():.1f} to {df['dni'].max():.1f} W/m²") 
print(f"DHI: {df['dhi'].min():.1f} to {df['dhi'].max():.1f} W/m²")
print(f"Air temp: {df['air_temp'].min():.1f} to {df['air_temp'].max():.1f} °C")
print(f"Cloud opacity: {df['cloud_opacity'].min():.1f} to {df['cloud_opacity'].max():.1f} %")
print(f"Relative humidity: {df['relative_humidity'].min():.1f} to {df['relative_humidity'].max():.1f} %")

# Check power outputs
print(f"\n=== POWER OUTPUT ANALYSIS ===")
print(f"Max OSM-MEPS power: {df['AC_Power_kW_osm_total'].max():.2f} kW")
print(f"System capacity: {total_system_capacity_kw:.1f} kW")
print(f"Capacity utilization: {df['AC_Power_kW_osm_total'].max()/total_system_capacity_kw*100:.1f}%")

# Check daily patterns
peak_day = df['AC_Power_kW_osm_total'].idxmax()
print(f"Peak power day: {peak_day}")
print(f"Peak day max power: {df.loc[peak_day, 'AC_Power_kW_osm_total']:.2f} kW")

# Check if timezone shift is causing issues
print(f"\n=== TIMEZONE VERIFICATION ===")
print(f"Data timezone: {df.index.tz}")
print(f"First few timestamps:")
print(df.index[:10])

# Check for negative power values (shouldn't exist)
negative_power = (df['AC_Power_kW_osm_total'] < 0).sum()
print(f"Negative power values: {negative_power}")

# Check energy calculation
print(f"\n=== ENERGY CALCULATION VERIFICATION ===")
print(f"Time interval: {time_interval_hours} hours")
print(f"Total timesteps: {len(df)}")
print(f"Total hours: {len(df) * time_interval_hours:.1f}")
print(f"Average OSM-MEPS power: {df['AC_Power_kW_osm_total'].mean():.2f} kW")
print(f"Estimated annual energy from avg power: {df['AC_Power_kW_osm_total'].mean() * 8760:.0f} kWh")

# Compare with your expected 146,413 kWh
expected_avg_power = 146413 / 8760
print(f"Required avg power for 146,413 kWh: {expected_avg_power:.2f} kW")
print(f"Current avg power ratio: {df['AC_Power_kW_osm_total'].mean() / expected_avg_power:.2f}")

#-------------------------------------------------------------------------------------------------

# === DAILY AGGREGATION & STATISTICAL ANALYSIS ===
print(f"\n=== DAILY AGGREGATION & STATISTICAL ANALYSIS ===")

# Convert hourly energy data to daily sums
daily_energy_pvlib = hourly_energy_pvlib.resample('D').sum()
daily_energy_osm = hourly_energy_osm.resample('D').sum()
daily_energy_pvwatts = hourly_energy_pvwatts.resample('D').sum()

# Ensure all indices are timezone-naive and normalize to pure dates
daily_energy_pvlib.index = daily_energy_pvlib.index.tz_localize(None).normalize()
daily_energy_osm.index = daily_energy_osm.index.tz_localize(None).normalize()
daily_energy_pvwatts.index = daily_energy_pvwatts.index.tz_localize(None).normalize()

# Aurora data is already daily - handle timezone and time component
aurora_daily = aurora_energy_2021.copy()

# Convert Aurora index to timezone-naive and normalize to pure dates
if aurora_daily.index.tz is not None:
    aurora_daily.index = aurora_daily.index.tz_localize(None).normalize()
else:
    aurora_daily.index = aurora_daily.index.normalize()

print(f"PVLib index type: {daily_energy_pvlib.index.dtype}")
print(f"Aurora index type: {aurora_daily.index.dtype}")
print(f"PVLib dates: {daily_energy_pvlib.index[:5]}")
print(f"Aurora dates: {aurora_daily.index[:5]}")
print(f"PVLib shape: {daily_energy_pvlib.shape}")
print(f"Aurora shape: {aurora_daily.shape}")

# Find the intersection of dates between both datasets
pvlib_dates = set(daily_energy_pvlib.index)
aurora_dates = set(aurora_daily.index)
common_dates = sorted(pvlib_dates.intersection(aurora_dates))

print(f"PVLib unique dates: {len(pvlib_dates)}")
print(f"Aurora unique dates: {len(aurora_dates)}")
print(f"Common dates: {len(common_dates)}")

if len(common_dates) == 0:
    print("ERROR: No common dates found! Checking date ranges...")
    print(f"PVLib date range: {daily_energy_pvlib.index.min()} to {daily_energy_pvlib.index.max()}")
    print(f"Aurora date range: {aurora_daily.index.min()} to {aurora_daily.index.max()}")
    
    # If no common dates, let's create them by using the full year
    full_year_2024 = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
    daily_energy_pvlib = daily_energy_pvlib.reindex(full_year_2024)
    daily_energy_osm = daily_energy_osm.reindex(full_year_2024)
    daily_energy_pvwatts = daily_energy_pvwatts.reindex(full_year_2024)
    aurora_daily = aurora_daily.reindex(full_year_2024)
    
    print(f"After reindexing - PVLib: {daily_energy_pvlib.shape}, Aurora: {aurora_daily.shape}")
    common_dates = full_year_2024

# Use common dates to filter all datasets
daily_energy_pvlib_common = daily_energy_pvlib.loc[common_dates]
daily_energy_osm_common = daily_energy_osm.loc[common_dates]
daily_energy_pvwatts_common = daily_energy_pvwatts.loc[common_dates]
aurora_daily_common = aurora_daily.loc[common_dates]

print(f"After filtering - PVLib: {daily_energy_pvlib_common.shape}, Aurora: {aurora_daily_common.shape}")

# Combine into single DataFrame
daily_df = pd.DataFrame({
    'PVLIB': daily_energy_pvlib_common,
    'OSM-MEPS': daily_energy_osm_common,
    'PVWatts': daily_energy_pvwatts_common,
    'Aurora': aurora_daily_common
}).dropna()

print(f"Final daily data shape: {daily_df.shape}")
print(f"Date range: {daily_df.index.min()} to {daily_df.index.max()}")
print(f"Total days analyzed: {len(daily_df)}")

if len(daily_df) == 0:
    print("ERROR: No data after combining! Trying alternative approach...")
    
    # Alternative: Just use PVLib dates and align Aurora to them
    daily_df = pd.DataFrame({
        'PVLIB': daily_energy_pvlib,
        'OSM-MEPS': daily_energy_osm,
        'PVWatts': daily_energy_pvwatts
    })
    
    # Add Aurora by aligning with the index
    aurora_aligned = aurora_daily.reindex(daily_df.index)
    daily_df['Aurora'] = aurora_aligned
    
    daily_df = daily_df.dropna()
    print(f"Alternative approach - daily data shape: {daily_df.shape}")

if len(daily_df) > 0:
    # Create arrays for ANOVA
    models_data_daily = {col: daily_df[col].dropna() for col in daily_df.columns}
    groups_daily = [models_data_daily[m] for m in models_data_daily]

    # Perform One-Way ANOVA on daily energy
    f_stat_daily, p_value_daily = stats.f_oneway(*groups_daily)
    print(f"\nOne-Way ANOVA Results (Daily Energy):")
    print(f"F-statistic: {f_stat_daily:.6f}")
    print(f"P-value: {p_value_daily:.10e}")

    if p_value_daily < 0.05:
        print("Significant differences exist between models (p < 0.05)")
        
        # === Tukey HSD Post-hoc test ===
        daily_melted = daily_df.melt(var_name="Model", value_name="Daily_Energy_kWh")
        tukey_results_daily = pairwise_tukeyhsd(daily_melted["Daily_Energy_kWh"],
                                                daily_melted["Model"],
                                                alpha=0.05)
        
        print(f"\nTukey HSD Post-hoc Test (Daily Energy):")
        print(tukey_results_daily)
        
        # FIXED: Correct way to access significant pairs
        significant_pairs = []
        # Convert results to DataFrame for easier access
        tukey_df = pd.DataFrame(data=tukey_results_daily._results_table.data[1:], 
                               columns=tukey_results_daily._results_table.data[0])
        
        print(f"\nDetailed Tukey HSD Results:")
        print(tukey_df)
        
        # Get significant pairs
        significant_mask = tukey_df['p-adj'] < 0.05
        significant_pairs_df = tukey_df[significant_mask]
        
        if len(significant_pairs_df) > 0:
            print(f"\nSignificant pairwise differences (p < 0.05):")
            for _, row in significant_pairs_df.iterrows():
                print(f"  • {row['group1']} vs {row['group2']}: mean diff = {row['meandiff']:.3f}, p-adj = {row['p-adj']:.4f}")
        else:
            print(f"\nNo significant pairwise differences found")
            
    else:
        print("No significant differences between models (p ≥ 0.05)")

    # === DAILY DESCRIPTIVE STATISTICS ===
    print(f"\n=== DAILY DESCRIPTIVE STATISTICS ===")
    for model_name, data in models_data_daily.items():
        print(f"{model_name}:")
        print(f"  Mean: {data.mean():.3f} kWh/day")
        print(f"  Std: {data.std():.3f} kWh/day")
        print(f"  Min: {data.min():.3f} kWh/day")
        print(f"  Max: {data.max():.3f} kWh/day")
        print(f"  Annual Total: {data.sum():,.0f} kWh")
        print(f"  Capacity Factor: {(data.sum() / (total_system_capacity_kw * 365 * 24)) * 100:.2f}%")

      
#------------------------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------------------------
#------------------------------------------OSM-MEPS----------------------------------------------------------------------
