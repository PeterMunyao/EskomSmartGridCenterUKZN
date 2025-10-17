# === IMPORT LIBRARIES ===
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import pvlib
from pvlib.irradiance import get_total_irradiance
from pvlib.temperature import sapm_cell

# === LOAD WEATHER DATA ===
file_path = 'csv_-29.815268_30.946439_fixed_23_0_PT5M.csv'
df = pd.read_csv(file_path)
df['period_end'] = pd.to_datetime(df['period_end'], utc=True)
df.set_index('period_end', inplace=True)

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
fig, ax = plt.subplots(figsize=(13, 6), facecolor='#f0f0f0')
ax.set_facecolor('#f0f0f0')

ax.plot(df.index, df["Energy_kWh_pvlib_5min"], label="PVLIB Energy", color='orange', linewidth=1.0)
ax.plot(df.index, df["Energy_kWh_osm_5min"], label="OSM-MEPS Energy", color='green', linewidth=1.0)

ax.set_xlabel("Date", fontsize=18)
ax.set_ylabel("Energy per 5 min (kWh)", fontsize=20)

ax.legend(fontsize=14)
ax.grid(True, linestyle='--', alpha=0.5)

ax.tick_params(axis='x', labelsize=18)
ax.tick_params(axis='y', labelsize=18)

plt.tight_layout()
plt.savefig("SMART-GRID_11_Energy_5min.pdf", format='pdf')
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
fig, ax = plt.subplots(figsize=(13, 6), facecolor='#f0f0f0')
ax.set_facecolor('#f0f0f0')

ax.plot(df.index, df["Ramp_W_per_s_pvlib"],
        color="orange", label="PVLIB Ramp Rate (W/s)", linewidth=1.0)
ax.plot(df.index, df["Ramp_W_per_s_osm"],
        color="green", label="OSM-MEPS Ramp Rate (W/s)", linewidth=1.0)

ax.set_xlabel("Time", fontsize=18, fontweight='bold')
ax.set_ylabel("Ramp Rate (W/s)", fontsize=20)

ax.legend(fontsize=14)
ax.grid(True, linestyle="--", alpha=0.5)

plt.tight_layout()
plt.savefig("RampRate_W_per_s_SMARTG.pdf", format="pdf")
plt.show()


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

# Select day with maximum power changes for OSM-MEPS model
analysis_date_osm = max_swing_time_5min_osm.date()
day_data_osm = df[df.index.date == analysis_date_osm]

print(f"\n=== OSM-MEPS ANALYSIS FOR {analysis_date_osm} ===")
print(f"Maximum 5-min swing: {day_data_osm['AC_Power_kW_osm_total'].diff().abs().max():.1f} kW")
print(f"Maximum ramp rate: {day_data_osm['Ramp_W_per_s_osm'].abs().max():.1f} W/s")

# === PROFESSIONAL GRAPH STYLING ===
plt.rcParams["font.family"] = "Garamond"
plt.rcParams["font.size"] = 19
plt.rcParams["font.weight"] = "bold"
plt.rcParams["axes.titleweight"] = "bold"
plt.rcParams["axes.labelweight"] = "bold"
plt.rcParams['xtick.labelsize'] = 18
plt.rcParams['ytick.labelsize'] = 18


# === CREATE COMBINED GRAPH ===
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12,8))

# Set professional background and grid
for ax in [ax1, ax2]:
    ax.set_facecolor('#f8f9fa')
    ax.grid(True, linestyle='--', alpha=0.3, linewidth=0.5)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

# === GRAPH 1: IRRADIANCE, METEOROLOGICAL DATA AND POWER OUTPUT ===
# Primary axis - Irradiance
color_ghi = 'brown'  
color_dni = '#ff7f0e'  # Orange
color_dhi = 'blue'  

ax1.plot(day_data_osm.index, day_data_osm['ghi'], 
         color=color_ghi, linewidth=2.5, label='GHI', alpha=0.9)
ax1.plot(day_data_osm.index, day_data_osm['dni'], 
         color=color_dni, linewidth=2, linestyle='--', label='DNI', alpha=0.8)
ax1.plot(day_data_osm.index, day_data_osm['dhi'], 
         color=color_dhi, linewidth=2, linestyle=':', label='DHI', alpha=0.8)

ax1.set_ylabel('Irradiance (W/m²)', fontweight='bold', color='#333333')
ax1.tick_params(axis='y', labelcolor='#333333')
ax1.set_ylim(bottom=0)

# Secondary axis - Meteorological data
ax1_twin = ax1.twinx()
color_cloud = '#7f7f7f'  # Gray
color_humidity = '#8c564b'  # Brown

# Plot with adjusted scales to avoid overlap
cloud_opacity_scaled = day_data_osm['cloud_opacity']
humidity_scaled = day_data_osm['relative_humidity']

ax1_twin.plot(day_data_osm.index, cloud_opacity_scaled, 
              color=color_cloud, linewidth=2, alpha=0.7, label='Cloud Opacity')
ax1_twin.plot(day_data_osm.index, humidity_scaled, 
              color=color_humidity, linewidth=2, alpha=0.7, linestyle='--', label='Relative Humidity')

ax1_twin.set_ylabel('Cloud Opacity / Humidity (%)', fontweight='bold', color='#666666')
ax1_twin.tick_params(axis='y', labelcolor='#666666')
ax1_twin.set_ylim(0, 100)

# Tertiary axis - Power output
ax1_twin2 = ax1.twinx()
ax1_twin2.spines['right'].set_position(('outward', 60))
color_power = 'green'  

ax1_twin2.plot(day_data_osm.index, day_data_osm['AC_Power_kW_osm_total'], 
               color=color_power, linewidth=3, label='PV Power (OSM-MEPS)')

ax1_twin2.set_ylabel('Power (kW)', fontweight='bold', color=color_power)
ax1_twin2.tick_params(axis='y', labelcolor=color_power)
ax1_twin2.set_ylim(bottom=0)

ax1.set_ylabel('Irradiance (W/m²)', fontsize=18, fontweight='bold')
ax1.set_xlabel('Time of Day', fontsize=18, fontweight='bold')

ax1_twin.set_ylabel('Cloud Opacity / Humidity (%)', fontsize=18, fontweight='bold')
# tertiary axis
ax1_twin2.set_ylabel('Power (kW)', fontsize=18, fontweight='bold')

# === GRAPH 2: RAMP RATE ===
color_ramp = 'red'  

ax2.plot(day_data_osm.index, day_data_osm['Ramp_W_per_s_osm'], 
         color=color_ramp, linewidth=2.5, label='Ramp Rate', alpha=0.9)

ax2.set_ylabel('Ramp Rate (W/s)', fontweight='bold', color='#333333')
ax2.set_xlabel('Time of Day', fontweight='bold', color='#333333')
ax2.set_ylim(bottom=day_data_osm['Ramp_W_per_s_osm'].min() * 1.1, 
             top=day_data_osm['Ramp_W_per_s_osm'].max() * 1.1)
ax2.axhline(y=0, color='black', linestyle='-', alpha=0.3, linewidth=1)

# === GRAPH 2: Ramp Rate ===
ax2.set_ylabel('Ramp Rate (W/s)', fontsize=18, fontweight='bold')
ax2.set_xlabel('Time of Day', fontsize=18, fontweight='bold')

# Highlight maximum ramp event with professional styling
max_ramp_time_osm = day_data_osm['Ramp_W_per_s_osm'].abs().idxmax()
max_ramp_value_osm = day_data_osm.loc[max_ramp_time_osm, 'Ramp_W_per_s_osm']

ax2.plot(max_ramp_time_osm, max_ramp_value_osm, 'o', 
         markersize=10, markerfacecolor='red', markeredgecolor='darkred', 
         markeredgewidth=2, label=f'Max Ramp: {max_ramp_value_osm:.1f} W/s')

# Add annotation for max ramp event
ax2.annotate(f'Max: {max_ramp_value_osm:.1f} W/s', 
             xy=(max_ramp_time_osm, max_ramp_value_osm),
             xytext=(10, 20), textcoords='offset points',
             bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7),
             arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'),
             fontweight='bold')

ax2.legend(loc='lower right', framealpha=0.9, fancybox=True, shadow=True)

# Format x-axis for both plots
for ax in [ax1, ax2]:
    ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%H:%M'))
    ax.xaxis.set_major_locator(plt.matplotlib.dates.HourLocator(interval=2))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=1, ha='right')

# === LEGEND PLACEMENT - PROFESSIONAL STYLING ===
# Combine legends for first graph and place below
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax1_twin.get_legend_handles_labels()
lines3, labels3 = ax1_twin2.get_legend_handles_labels()

fig.legend(lines1 + lines2 + lines3, labels1 + labels2 + labels3,
           loc='lower center',
           bbox_to_anchor=(0.5, -0.05),
           ncol=4,
           framealpha=0.95,
           fancybox=True,
           shadow=True,
           fontsize=16,
           frameon=True)

plt.tight_layout()

# === CALCULATE AND DISPLAY STATISTICS ===
max_power_osm = day_data_osm['AC_Power_kW_osm_total'].max()
min_power_osm = day_data_osm['AC_Power_kW_osm_total'].min()
max_ghi_osm = day_data_osm['ghi'].max()
max_ramp_osm = day_data_osm['Ramp_W_per_s_osm'].abs().max()
max_power_swing_osm = day_data_osm['AC_Power_kW_osm_total'].diff().abs().max()
max_cloud_opacity_osm = day_data_osm['cloud_opacity'].max()
max_humidity_osm = day_data_osm['relative_humidity'].max()

# Create professional statistics box
stats_text = (
    f"OSM-MEPS MODEL STATISTICS\n\n"
    f"• Maximum Power: {max_power_osm:.1f} kW\n"
    f"• Maximum GHI: {max_ghi_osm:.1f} W/m²\n"
    f"• Maximum Ramp Rate: {max_ramp_osm:.1f} W/s\n"
    f"• Maximum 5-min Swing: {max_power_swing_osm:.1f} kW\n"
    f"• Maximum Cloud Opacity: {max_cloud_opacity_osm:.1f}%\n"
    f"• Recommended Battery: {battery_power_rating_osm:.1f} kW / {recommended_energy_osm:.1f} kWh"
)

# Add statistics box at the bottom of the graph
ax2.text(0.02, 0.06, stats_text, transform=ax2.transAxes, fontsize=12,
         bbox=dict(boxstyle="round,pad=0.8", facecolor="white", alpha=0.9,
                   edgecolor='gray', linewidth=1),
         verticalalignment='bottom', fontweight='bold')

# Adjust subplot spacing
plt.subplots_adjust(top=0.98, bottom=0.15, hspace=0.3)


# Save combined graph
plt.savefig('OSM_MEPS_Max_Ramp_Analysis.pdf', dpi=300, bbox_inches='tight', 
            facecolor='white', edgecolor='none')
plt.show()

# === PRINT DETAILED OSM-MEPS ANALYSIS ===
print(f"\n=== OSM-MEPS DETAILED ANALYSIS ===")
print(f"Power Characteristics:")
print(f"  - Max Power: {max_power_osm:.1f} kW")
print(f"  - Min Power: {min_power_osm:.1f} kW") 
print(f"  - Power Range: {max_power_osm - min_power_osm:.1f} kW")

print(f"\nRamp Analysis:")
print(f"  - Max Ramp Rate: {max_ramp_osm:.1f} W/s at {max_ramp_time_osm}")
print(f"  - Max 5-min Power Change: {max_power_swing_osm:.1f} kW")

print(f"\nMeteorological Conditions:")
print(f"  - Max GHI: {max_ghi_osm:.1f} W/m²")
print(f"  - Max Cloud Opacity: {max_cloud_opacity_osm:.1f}%")
print(f"  - Max Humidity: {max_humidity_osm:.1f}%")

print(f"\nBattery Sizing (OSM-MEPS):")
print(f"  - Power Rating: {battery_power_rating_osm:.1f} kW")
print(f"  - Energy Capacity: {recommended_energy_osm:.1f} kWh")

# Calculate correct battery coverage
battery_coverage = battery_power_rating_osm / max_power_swing_5min_osm * 100
margin = battery_coverage - 100

print(f"  - Can handle {battery_coverage:.1f}% of worst-case swing ({margin:+.1f}% margin)")
# === ANALYZE MAX RAMP EVENT ===
print(f"\n=== MAX RAMP EVENT ANALYSIS ===")
if max_ramp_time_osm - pd.Timedelta(minutes=5) in day_data_osm.index:
    prev_time = max_ramp_time_osm - pd.Timedelta(minutes=5)
    power_before = day_data_osm.loc[prev_time, 'AC_Power_kW_osm_total']
    power_after = day_data_osm.loc[max_ramp_time_osm, 'AC_Power_kW_osm_total']
    power_change = power_after - power_before
    
    ghi_before = day_data_osm.loc[prev_time, 'ghi']
    ghi_after = day_data_osm.loc[max_ramp_time_osm, 'ghi']
    
    cloud_before = day_data_osm.loc[prev_time, 'cloud_opacity']
    cloud_after = day_data_osm.loc[max_ramp_time_osm, 'cloud_opacity']
    
    print(f"Event at {max_ramp_time_osm}:")
    print(f"  - Power: {power_before:.1f} → {power_after:.1f} kW (Δ: {power_change:.1f} kW)")
    print(f"  - GHI: {ghi_before:.1f} → {ghi_after:.1f} W/m²")
    print(f"  - Cloud: {cloud_before:.1f}% → {cloud_after:.1f}%")
    print(f"  - Calculated Ramp: {power_change * 1000 / 300:.1f} W/s")

# === PLOT COMPARISON WITH VISIBLE MARGINS ===
plt.rcParams["font.family"] = "Garamond"
plt.rcParams["font.size"] = 19
plt.rcParams["font.weight"] = "bold"

fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(8, 13))

for ax in [ax1, ax2, ax3]:
    ax.set_facecolor('#f8f9fa')
    ax.grid(True, linestyle='--', alpha=0.3)
    # KEEP TOP AND RIGHT SPINES VISIBLE
    ax.spines['top'].set_visible(True)
    ax.spines['right'].set_visible(True)
    ax.spines['top'].set_color('black')
    ax.spines['right'].set_color('black')
    ax.spines['top'].set_linewidth(2)
    ax.spines['right'].set_linewidth(2)
    # Also highlight left and bottom for reference
    ax.spines['left'].set_color('black')
    ax.spines['bottom'].set_color('black')
    ax.spines['left'].set_linewidth(1.5)
    ax.spines['bottom'].set_linewidth(1.5)

# Plot 1: Power comparison
ax1.plot(day_data_osm.index, day_data_osm['AC_Power_kW_osm_total'],
         color='black', linewidth=2, label='Original PV Power', alpha=0.8)
ax1.plot(day_data_osm.index, smoothed_basic,
         color='blue', linewidth=2, label='Basic Smoothing', alpha=0.7)
ax1.plot(day_data_osm.index, smoothed_bell,
         color='red', linewidth=2.5, label='Strategic Smoothing')

ax1.set_ylabel('Power (kW)', fontweight='bold')
ax1.legend(framealpha=0.9)



# Plot 2: Ramp rate comparison
original_ramp = day_data_osm['Ramp_W_per_s_osm']
basic_ramp = smoothed_basic.diff() * 1000 / 300
bell_ramp = smoothed_bell.diff() * 1000 / 300

ax2.plot(day_data_osm.index, original_ramp,
         color='black', linewidth=1, alpha=0.5, label='Original Ramp')
ax2.plot(day_data_osm.index, basic_ramp,
         color='blue', linewidth=2, label='Basic Smoothing', alpha=0.7)
ax2.plot(day_data_osm.index, bell_ramp,
         color='red', linewidth=2, label='Strategic Smoothing')

ax2.set_ylabel('Ramp Rate (W/s)', fontweight='bold')
ax2.legend(framealpha=0.9)

ax2.axhline(y=0, color='gray', linestyle='-', alpha=0.3)


# Plot 3: Battery usage
ax3.plot(day_data_osm.index, battery_basic,
         color='blue', linewidth=2, label='Basic Smoothing Battery', alpha=0.7)
ax3.plot(day_data_osm.index, battery_bell,
         color='red', linewidth=2, label='Strategic Smoothing Battery')

# FIX: Convert numpy arrays to pandas Series for fill_between
battery_bell_series = pd.Series(battery_bell, index=day_data_osm.index)
battery_basic_series = pd.Series(battery_basic, index=day_data_osm.index)

# Now use .where() on pandas Series
ax3.fill_between(day_data_osm.index, 0, battery_bell_series.where(battery_bell_series > 0),
                 alpha=0.3, color='green', label='Charging')
ax3.fill_between(day_data_osm.index, 0, battery_bell_series.where(battery_bell_series < 0),
                 alpha=0.3, color='orange', label='Discharging')

ax3.set_ylabel('Battery Power (kW)', fontweight='bold')
ax3.set_xlabel('Time of Day', fontweight='bold')
ax3.legend(framealpha=0.9)

ax3.axhline(y=0, color='gray', linestyle='-', alpha=0.3)



# Format x-axis
for ax in [ax1, ax2, ax3]:
    ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%H:%M'))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=0, ha='right')



plt.tight_layout()

print("=== GRAPH MARGIN VISUALIZATION ===")
print("Red borders: Top and right axes margins")
print("Blue borders: Left and bottom axes margins") 
print("Yellow boxes: Margin labels within each subplot")
print("Pink boxes: Overall figure margin labels")

# === PERFORMANCE METRICS ===
print(f"\n=== PERFORMANCE COMPARISON ===")
print(f"Original System:")
print(f"  - Max Ramp: {original_ramp.abs().max():.1f} W/s")
print(f"  - Power Range: {day_data_osm['AC_Power_kW_osm_total'].max() - day_data_osm['AC_Power_kW_osm_total'].min():.1f} kW")

print(f"\nBasic Smoothing:")
print(f"  - Max Ramp: {basic_ramp.abs().max():.1f} W/s")
print(f"  - Ramp Reduction: {((original_ramp.abs().max() - basic_ramp.abs().max()) / original_ramp.abs().max() * 100):.1f}%")

print(f"\nBell Curve Smoothing:")
print(f"  - Max Ramp: {bell_ramp.abs().max():.1f} W/s")
print(f"  - Ramp Reduction: {((original_ramp.abs().max() - bell_ramp.abs().max()) / original_ramp.abs().max() * 100):.1f}%")
print(f"  - Peak Preservation: {((smoothed_bell.max() - smoothed_basic.max()) / smoothed_basic.max() * 100):+.1f}% vs basic")

print(f"\nBattery Usage:")
print(f"  - Max Charge (Bell): {battery_bell.max():.1f} kW")
print(f"  - Max Discharge (Bell): {abs(battery_bell.min()):.1f} kW")
print(f"  - Battery Utilization: {max(abs(battery_bell.max()), abs(battery_bell.min())) / battery_power_rating_osm * 100:.1f}%")

plt.savefig('Smart_grid_Smoothing_Comparison_With_Margins.pdf', dpi=300, bbox_inches='tight',
            facecolor='white', edgecolor='none')
plt.show()





# --- Filter for first 4 days of August and December 2024 ---
df_aug = df[(df.index >= '2024-08-01') & (df.index < '2024-08-05')]
df_dec = df[(df.index >= '2024-12-01') & (df.index < '2024-12-05')]

# Function to plot ramp rate
def plot_ramp_rate(df_plot, month_name):
    plt.rcParams["font.family"] = "Garamond"
    fig, ax = plt.subplots(figsize=(13, 7), facecolor='#f0f0f0')  # Increased height for legend
    ax.set_facecolor('#f0f0f0')

    ax.plot(df_plot.index, df_plot["Ramp_W_per_s_pvlib"],
            color="orange", label="PVLIB Ramp Rate (W/s)", linewidth=1.0)
    ax.plot(df_plot.index, df_plot["Ramp_W_per_s_osm"],
            color="green", label="OSM-MEPS Ramp Rate (W/s)", linewidth=1.0)

    ax.set_xlabel("Date", fontsize=19)
    ax.set_ylabel("Ramp Rate (W/s)", fontsize=19)


    # Place legend below the plot with improved formatting
    ax.legend(fontsize=16, loc='upper center', bbox_to_anchor=(0.5, -0.15),
              ncol=2, framealpha=1.0, fancybox=True, shadow=True)
    
    ax.grid(True, linestyle="--", alpha=0.5)

    # Bold tick labels
    ax.tick_params(axis='x', labelsize=18, rotation=1)
    ax.tick_params(axis='y', labelsize=18)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontweight('bold')

    # Adjust layout to accommodate legend below
    plt.tight_layout(rect=[0, 0.1, 1, 0.95])  # Reserve space at bottom
    plt.savefig(f"RampRate_W_per_s_{month_name}_1-4.pdf", format="pdf", bbox_inches='tight')
    plt.show()

# --- Plot August ---
plot_ramp_rate(df_aug, "August")

# --- Plot December ---
plot_ramp_rate(df_dec, "December")


#effects of GHI, DNI, DHI ON POWER DURING CLOUD OBSTRUCTION ON DIRECT NORMAL IRRADIANCE


# --- Filter for first 4 days of August and December 2024 ---
df_aug = df[(df.index >= '2024-08-01') & (df.index < '2024-08-05')]
df_dec = df[(df.index >= '2024-12-01') & (df.index < '2024-12-05')]

# Function to plot all irradiance components, AC Power, and Ramp Rate
def plot_all_metrics(df_plot, month_name):
    plt.rcParams["font.family"] = "Garamond"
    
    # Create subplots: Irradiance, AC Power, Ramp Rate
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 14), facecolor='#f0f0f0')
    
    for ax in [ax1, ax2, ax3]:
        ax.set_facecolor('#f0f0f0')
    
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
    ax2.legend(fontsize=16, loc='upper right')
    ax2.grid(True, linestyle="--", alpha=0.5)
   
    # Bottom subplot: Ramp Rate
    ax3.plot(df_plot.index, df_plot["Ramp_W_per_s_pvlib"],
            color="orange", label="PVLIB Ramp Rate (W/s)", linewidth=1.5)
    ax3.plot(df_plot.index, df_plot["Ramp_W_per_s_osm"],
            color="darkgreen", label="OSM-MEPS Ramp Rate (W/s)", linewidth=1.5)
    ax3.set_xlabel("Date", fontsize=19)
    ax3.set_ylabel("Ramp Rate (W/s)", fontsize=19)
    
    # Place ramp rate legend below the bottom plot
    ax3.legend(fontsize=16, loc='upper center', bbox_to_anchor=(0.5, -0.25),
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
    plt.savefig(f"Smart_grid_Complete_Analysis_{month_name}_1-4.pdf", format="pdf", bbox_inches='tight')
    plt.show()

# --- Plot August ---
plot_all_metrics(df_aug, "August")

# --- Plot December ---
plot_all_metrics(df_dec, "December")


