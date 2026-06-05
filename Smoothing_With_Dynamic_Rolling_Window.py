
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

#---------------------------------------------------------------------------
#-------FIND--THE---DAY---WITH---MAXIMUM-----POWER--CHANGE/RAMP-------------
#---------------------------------------------------------------------------

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
color_cloud = 'cyan'  # Gray
color_humidity = '#8c564b'  # Brown

# Plot with adjusted scales to avoid overlap
cloud_opacity_scaled = day_data_osm['cloud_opacity']
humidity_scaled = day_data_osm['relative_humidity']

ax1_twin.plot(day_data_osm.index, cloud_opacity_scaled, 
              color=color_cloud, linewidth=2, alpha=0.7, label='Cloud Opacity')
ax1_twin.plot(day_data_osm.index, humidity_scaled, 
              color=color_humidity, linewidth=2, alpha=0.7, linestyle='--', label='Relative Humidity')

ax1_twin.set_ylabel('Cloud Opacity / Humidity (%)', fontweight='bold', color='cyan')
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
                   edgecolor='#fafafa', linewidth=1),
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

#---------------------------------------------------------------------------
#----------------------------------------------------------------------------
#---------------------------------------------------------------------------

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
        
        # === FIXED: Update battery state of charge (CORRECT SIGN) ===
        # Positive battery_power = charging = INCREASE SOC
        # Negative battery_power = discharging = DECREASE SOC
        energy_change = battery_power[i] * (5/60)  # kWh added/removed in 5 minutes
        battery_soc[i] = battery_soc[i-1] + energy_change  # ADD (not subtract)
        
        # SOC-based power adjustment to maintain charge throughout day
        # Use previous SOC for decision to avoid circular logic
        soc_adjustment = 0
        if battery_soc[i-1] < battery_energy_kwh * 0.2:  # Too low
            # Reduce discharge or increase charging
            if battery_power[i] < 0:  # Currently discharging
                soc_adjustment = battery_power[i] * 0.3  # Reduce discharge magnitude
            elif battery_power[i] > 0:  # Currently charging
                soc_adjustment = battery_power[i] * 0.1  # Slightly increase charging
        elif battery_soc[i-1] > battery_energy_kwh * 0.9:  # Too high
            # Reduce charging or increase discharge
            if battery_power[i] > 0:  # Currently charging
                soc_adjustment = -battery_power[i] * 0.3  # Reduce charging magnitude
            elif battery_power[i] < 0:  # Currently discharging
                soc_adjustment = battery_power[i] * 0.1  # Slightly increase discharge
        
        battery_power[i] += soc_adjustment  # Add adjustment
        battery_power[i] = np.clip(battery_power[i], -battery_power_kw, battery_power_kw)
        
        # Recalculate SOC with adjusted battery power
        energy_change_adjusted = battery_power[i] * (5/60)
        battery_soc[i] = battery_soc[i-1] + energy_change_adjusted
        
        # Final smoothed power
        smoothed_power.iloc[i] = current_power + battery_power[i]
        
        # Ensure SOC stays within physical bounds
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

# Set battery capacity to 85.4 kWh
battery_capacity_kwh = 85.4

# Detect daily pattern
daily_pattern = detect_daily_pattern(day_data_osm['AC_Power_kW_osm_total'])
print(f"Detected daily pattern:")
print(f"  - Peak: {daily_pattern['peak_power']:.1f} kW at {daily_pattern['peak_time']}")
print(f"  - Sunrise: {daily_pattern['sunrise_time']}")
print(f"  - Sunset: {daily_pattern['sunset_time']}")

# Apply strategic smoothing with 85.4 kWh battery capacity
smoothed_bell, battery_bell, soc_bell = bell_curve_smoothing(
    day_data_osm['AC_Power_kW_osm_total'],
    battery_power_rating_osm,
    battery_capacity_kwh,  # Using 85.4 kWh capacity
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

fig, (ax1, ax2, ax3, ax4) = plt.subplots(4, 1, figsize=(8, 16))

for ax in [ax1, ax2, ax3, ax4]:
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
ax1.legend(framealpha=0.9, fontsize=15)

# Plot 2: Ramp rate comparison
original_ramp = day_data_osm['Ramp_W_per_s_osm']
basic_ramp = smoothed_basic.diff() * 1000 / 300
bell_ramp = smoothed_bell.diff() * 1000 / 300

ax2.plot(day_data_osm.index, original_ramp,
         color='red', linewidth=2, alpha=0.8, label='Original Ramp')
ax2.plot(day_data_osm.index, basic_ramp,
         color='blue', linewidth=2, label='Basic Smoothing', alpha=0.7)
ax2.plot(day_data_osm.index, bell_ramp,
         color='maroon', linewidth=2, label='Strategic smoothing')

ax2.set_ylabel('Ramp Rate (W/s)', fontweight='bold')
ax2.legend(framealpha=0.9, fontsize=15)
ax2.axhline(y=0, color='gray', linestyle='-', alpha=0.3)

# Plot 3: Battery usage
ax3.plot(day_data_osm.index, battery_basic,
         color='blue', linewidth=2, label='Basic Smoothing Battery', alpha=0.7)
ax3.plot(day_data_osm.index, battery_bell,
         color='maroon', linewidth=2, label='Strategic smoothing Battery')

# Convert numpy arrays to pandas Series for fill_between
battery_bell_series = pd.Series(battery_bell, index=day_data_osm.index)

ax3.fill_between(day_data_osm.index, 0, battery_bell_series.where(battery_bell_series > 0),
                 alpha=0.3, color='green', label='Charging')
ax3.fill_between(day_data_osm.index, 0, battery_bell_series.where(battery_bell_series < 0),
                 alpha=0.3, color='magenta', label='Discharging')

ax3.set_ylabel('Battery Power (kW)', fontweight='bold')
ax3.legend(framealpha=0.9, fontsize=14)
ax3.axhline(y=0, color='gray', linestyle='-', alpha=0.3)

# Plot 4: Battery State of Charge (NEW)
soc_percent = (soc_bell / battery_capacity_kwh) * 100
ax4.plot(day_data_osm.index, soc_percent,
         color='green', linewidth=2, label='Battery SOC')
ax4.fill_between(day_data_osm.index, 0, soc_percent,
                 alpha=0.3, color='green')
ax4.set_ylabel('Battery SOC (%)', fontweight='bold')
ax4.set_xlabel('Time of Day', fontweight='bold')
ax4.legend(framealpha=0.9, fontsize=14)
ax4.axhline(y=50, color='gray', linestyle='--', alpha=0.5, label='50% SOC')
ax4.axhline(y=20, color='orange', linestyle='--', alpha=0.5, label='20% Minimum')
ax4.axhline(y=90, color='orange', linestyle='--', alpha=0.5, label='90% Maximum')
ax4.set_ylim(0, 100)

# Format x-axis
for ax in [ax1, ax2, ax3, ax4]:
    ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%H:%M'))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=1, ha='right')

plt.tight_layout()

# === PERFORMANCE METRICS ===
print(f"\n=== PERFORMANCE COMPARISON ===")
print(f"Battery Capacity: {battery_capacity_kwh} kWh")
print(f"\nOriginal System:")
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

print(f"\nBattery State of Charge:")
print(f"  - Initial SOC: 50.0% ({battery_capacity_kwh/2:.1f} kWh)")
print(f"  - Minimum SOC: {soc_percent.min():.1f}% ({(soc_percent.min()/100)*battery_capacity_kwh:.1f} kWh)")
print(f"  - Maximum SOC: {soc_percent.max():.1f}% ({(soc_percent.max()/100)*battery_capacity_kwh:.1f} kWh)")

# FIXED: Use array indexing instead of .iloc for numpy array
print(f"  - Final SOC: {soc_percent[-1]:.1f}% ({(soc_percent[-1]/100)*battery_capacity_kwh:.1f} kWh)")
print(f"  - Total Energy Throughput: {np.sum(np.abs(battery_bell)) * (5/60):.1f} kWh")

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

plt.savefig('Strategic_Smoothing_PA.pdf', dpi=300, bbox_inches='tight',
            facecolor='#fafafa', edgecolor='none')
plt.show()




#----------------------------------------------------------

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
        
        # === FIXED: Update battery state of charge (CORRECT SIGN) ===
        # Positive battery_power = charging = INCREASE SOC
        # Negative battery_power = discharging = DECREASE SOC
        energy_change = battery_power[i] * (5/60)  # kWh added/removed in 5 minutes
        battery_soc[i] = battery_soc[i-1] + energy_change  # ADD (not subtract)
        
        # SOC-based power adjustment to maintain charge throughout day
        # Use previous SOC for decision to avoid circular logic
        soc_adjustment = 0
        if battery_soc[i-1] < battery_energy_kwh * 0.2:  # Too low
            # Reduce discharge or increase charging
            if battery_power[i] < 0:  # Currently discharging
                soc_adjustment = battery_power[i] * 0.3  # Reduce discharge magnitude
            elif battery_power[i] > 0:  # Currently charging
                soc_adjustment = battery_power[i] * 0.1  # Slightly increase charging
        elif battery_soc[i-1] > battery_energy_kwh * 0.9:  # Too high
            # Reduce charging or increase discharge
            if battery_power[i] > 0:  # Currently charging
                soc_adjustment = -battery_power[i] * 0.3  # Reduce charging magnitude
            elif battery_power[i] < 0:  # Currently discharging
                soc_adjustment = battery_power[i] * 0.1  # Slightly increase discharge
        
        battery_power[i] += soc_adjustment  # Add adjustment
        battery_power[i] = np.clip(battery_power[i], -battery_power_kw, battery_power_kw)
        
        # Recalculate SOC with adjusted battery power
        energy_change_adjusted = battery_power[i] * (5/60)
        battery_soc[i] = battery_soc[i-1] + energy_change_adjusted
        
        # Final smoothed power
        smoothed_power.iloc[i] = current_power + battery_power[i]
        
        # Ensure SOC stays within physical bounds
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

# Set battery capacity to 85.4 kWh
battery_capacity_kwh = 85.4

# Detect daily pattern
daily_pattern = detect_daily_pattern(day_data_osm['AC_Power_kW_osm_total'])
print(f"Detected daily pattern:")
print(f"  - Peak: {daily_pattern['peak_power']:.1f} kW at {daily_pattern['peak_time']}")
print(f"  - Sunrise: {daily_pattern['sunrise_time']}")
print(f"  - Sunset: {daily_pattern['sunset_time']}")

# Apply strategic smoothing with 85.4 kWh battery capacity
smoothed_bell, battery_bell, soc_bell = bell_curve_smoothing(
    day_data_osm['AC_Power_kW_osm_total'],
    battery_power_rating_osm,
    battery_capacity_kwh,  # Using 85.4 kWh capacity
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

fig, (ax1, ax2, ax3, ax4) = plt.subplots(4, 1, figsize=(8, 16))

for ax in [ax1, ax2, ax3, ax4]:
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
ax1.legend(framealpha=0.9, fontsize=15)

# Plot 2: Ramp rate comparison
original_ramp = day_data_osm['Ramp_W_per_s_osm']
basic_ramp = smoothed_basic.diff() * 1000 / 300
bell_ramp = smoothed_bell.diff() * 1000 / 300

ax2.plot(day_data_osm.index, original_ramp,
         color='red', linewidth=2, alpha=0.8, label='Original Ramp')
ax2.plot(day_data_osm.index, basic_ramp,
         color='blue', linewidth=2, label='Basic Smoothing', alpha=0.7)
ax2.plot(day_data_osm.index, bell_ramp,
         color='maroon', linewidth=2, label='Strategic smoothing')

ax2.set_ylabel('Ramp Rate (W/s)', fontweight='bold')
ax2.legend(framealpha=0.9, fontsize=15)
ax2.axhline(y=0, color='gray', linestyle='-', alpha=0.3)

# Plot 3: Battery usage
ax3.plot(day_data_osm.index, battery_basic,
         color='blue', linewidth=2, label='Basic Smoothing Battery', alpha=0.7)
ax3.plot(day_data_osm.index, battery_bell,
         color='maroon', linewidth=2, label='Strategic smoothing Battery')

# Convert numpy arrays to pandas Series for fill_between
battery_bell_series = pd.Series(battery_bell, index=day_data_osm.index)

ax3.fill_between(day_data_osm.index, 0, battery_bell_series.where(battery_bell_series > 0),
                 alpha=0.3, color='green', label='Charging')
ax3.fill_between(day_data_osm.index, 0, battery_bell_series.where(battery_bell_series < 0),
                 alpha=0.3, color='magenta', label='Discharging')

ax3.set_ylabel('Battery Power (kW)', fontweight='bold')
ax3.legend(framealpha=0.9, fontsize=14)
ax3.axhline(y=0, color='gray', linestyle='-', alpha=0.3)

# Plot 4: Battery State of Charge (NEW)
soc_percent = (soc_bell / battery_capacity_kwh) * 100
ax4.plot(day_data_osm.index, soc_percent,
         color='green', linewidth=2, label='Battery SOC')
ax4.fill_between(day_data_osm.index, 0, soc_percent,
                 alpha=0.3, color='green')
ax4.set_ylabel('Battery SOC (%)', fontweight='bold')
ax4.set_xlabel('Time of Day', fontweight='bold')
ax4.legend(framealpha=0.9, fontsize=14)
ax4.axhline(y=50, color='gray', linestyle='--', alpha=0.5, label='50% SOC')
ax4.axhline(y=20, color='orange', linestyle='--', alpha=0.5, label='20% Minimum')
ax4.axhline(y=90, color='orange', linestyle='--', alpha=0.5, label='90% Maximum')
ax4.set_ylim(0, 100)

# Format x-axis
for ax in [ax1, ax2, ax3, ax4]:
    ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%H:%M'))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=1, ha='right')

plt.tight_layout()

# === PERFORMANCE METRICS ===
print(f"\n=== PERFORMANCE COMPARISON ===")
print(f"Battery Capacity: {battery_capacity_kwh} kWh")
print(f"\nOriginal System:")
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

print(f"\nBattery State of Charge:")
print(f"  - Initial SOC: 50.0% ({battery_capacity_kwh/2:.1f} kWh)")
print(f"  - Minimum SOC: {soc_percent.min():.1f}% ({(soc_percent.min()/100)*battery_capacity_kwh:.1f} kWh)")
print(f"  - Maximum SOC: {soc_percent.max():.1f}% ({(soc_percent.max()/100)*battery_capacity_kwh:.1f} kWh)")

# FIXED: Use array indexing instead of .iloc for numpy array
print(f"  - Final SOC: {soc_percent[-1]:.1f}% ({(soc_percent[-1]/100)*battery_capacity_kwh:.1f} kWh)")
print(f"  - Total Energy Throughput: {np.sum(np.abs(battery_bell)) * (5/60):.1f} kWh")

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

plt.savefig('Strategic_Smoothing_PA.pdf', dpi=300, bbox_inches='tight',
            facecolor='#fafafa', edgecolor='none')
plt.show()

#--------------------------------------------------------



import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Set Garamond font for all text
plt.rcParams["font.family"] = "Garamond"
plt.rcParams["font.size"] = 12
plt.rcParams["font.weight"] = "normal"

print("="*80)
print("SINGLE PLOT: Energy, Ramp Rate & Reduction vs Aggression")
print("="*80)

# Extract arrays from your results
agg_arr = np.array([r['aggression'] for r in all_results])
energy_arr = np.array([r['energy'] for r in all_results])
ramp_arr = np.array([r['max_ramp'] for r in all_results])
reduction_arr = np.array([r['reduction'] for r in all_results])
original_ramp = 118.7  # From your results

# Create single figure with THREE y-axes
fig = plt.figure(figsize=(7, 4))
fig.patch.set_facecolor('white')

# Create primary axis (left y-axis for Total Energy)
ax1 = plt.gca()
ax1.set_facecolor('#fafafa')
ax1.grid(True, linestyle='--', alpha=0.3, linewidth=0.5, zorder=0)

# Plot 1: Total Cumulative Energy (area) - on left axis
color_energy = '#2E7D32'  # Dark green
ax1.fill_between(agg_arr, 0, energy_arr, alpha=0.15, color=color_energy)
ax1.plot(agg_arr, energy_arr, color=color_energy, linewidth=2.5, zorder=5, label='Total Energy (kWh)')

# Set primary axis labels (left)
ax1.set_xlabel('Smoothing Aggression Factor', fontsize=14, labelpad=8)
ax1.set_ylabel('Total Energy (kWh)', fontsize=15, color=color_energy)
ax1.tick_params(axis='y', labelcolor=color_energy, labelsize=14)
ax1.tick_params(axis='x', labelsize=14)
ax1.set_xlim(-0.05, 1.05)
ax1.set_ylim(0, max(energy_arr) * 1.15)

# Create secondary axis (right y-axis for Max Ramp Rate)
ax2 = ax1.twinx()
color_ramp = '#D32F2F'  # Dark red
ax2.plot(agg_arr, ramp_arr, color=color_ramp, linewidth=2.5, zorder=7, label='Max Ramp Rate (W/s)')

# Set secondary axis labels (right)
ax2.set_ylabel('Max Ramp Rate (W/s)', fontsize=15, color=color_ramp)
ax2.tick_params(axis='y', labelcolor=color_ramp, labelsize=14)
ax2.set_ylim(0, original_ramp * 1.2)

# Create third axis (far right y-axis for Reduction Percentage)
ax3 = ax1.twinx()
# Offset the third axis to the right
ax3.spines['right'].set_position(('outward', 60))
color_reduction = '#F57C00'  # Orange
ax3.plot(agg_arr, reduction_arr, color=color_reduction, linewidth=2.5, zorder=9, label='Ramp Rate Reduction (%)')
ax3.fill_between(agg_arr, 0, reduction_arr, alpha=0.1, color=color_reduction, zorder=1)

# Set third axis labels (far right)
ax3.set_ylabel('Ramp Rate Reduction (%)', fontsize=15, color=color_reduction)
ax3.tick_params(axis='y', labelcolor=color_reduction, labelsize=14)
ax3.set_ylim(0, 105)

# Annotate values at intervals of 0.1 aggression factor with boxes
annotation_aggressions = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

for agg in annotation_aggressions:
    # Find index of closest aggression value
    idx = np.argmin(np.abs(agg_arr - agg))
    
    # Get values at this aggression
    energy_val = energy_arr[idx]
    ramp_val = ramp_arr[idx]
    reduction_val = reduction_arr[idx]
    
    # Adjust vertical offsets for agg=0 to avoid overlapping with y-axis
    if agg == 0:
        energy_offset = 15
        ramp_offset = -15
        reduction_offset = 15
    else:
        energy_offset = 10
        ramp_offset = -12
        reduction_offset = 12
    
    # Annotate on energy line (left axis) with box - very light green fill
    bbox_props_energy = dict(boxstyle='round,pad=0.3', facecolor=color_energy, alpha=0.15, edgecolor=color_energy, linewidth=0.5)
    ax1.annotate(f'{energy_val:.0f}', 
                xy=(agg, energy_val),
                xytext=(0, energy_offset), textcoords='offset points',
                fontsize=12, color=color_energy, fontweight='bold',
                ha='center', bbox=bbox_props_energy)
    
    # Annotate on ramp rate line (right axis) with box - very light red fill
    bbox_props_ramp = dict(boxstyle='round,pad=0.3', facecolor=color_ramp, alpha=0.15, edgecolor=color_ramp, linewidth=0.5)
    ax2.annotate(f'{ramp_val:.0f}', 
                xy=(agg, ramp_val),
                xytext=(0, ramp_offset), textcoords='offset points',
                fontsize=12, color=color_ramp, fontweight='bold',
                ha='center', bbox=bbox_props_ramp)
    
    # Annotate on reduction line (far right axis) with box - very light orange fill
    bbox_props_reduction = dict(boxstyle='round,pad=0.3', facecolor=color_reduction, alpha=0.15, edgecolor=color_reduction, linewidth=0.5)
    ax3.annotate(f'{reduction_val:.0f}', 
                xy=(agg, reduction_val),
                xytext=(0, reduction_offset), textcoords='offset points',
                fontsize=12, color=color_reduction, fontweight='bold',
                ha='center', bbox=bbox_props_reduction)

plt.tight_layout()
plt.subplots_adjust(bottom=0.15, right=0.85)

# Create simplified legend below the plot
legend_elements = [
    plt.Line2D([0], [0], color=color_energy, linewidth=2.5, label='Total Energy (kWh)'),
    plt.Line2D([0], [0], color=color_ramp, linewidth=2.5, label='Max Ramp Rate (W/s)'),
    plt.Line2D([0], [0], color=color_reduction, linewidth=2.5, label='Ramp Rate Reduction (%)')
]

ax1.legend(handles=legend_elements, loc='upper center', bbox_to_anchor=(0.57, -0.16),
           framealpha=0.95, fontsize=12.5, ncol=3, fancybox=True, shadow=False)

# Save the figure
plt.savefig('Aggression_Analysis_PA.pdf', dpi=300, bbox_inches='tight', 
            facecolor='white', edgecolor='none')
plt.show()

# Print additional insights
print("\n" + "="*80)
print("KEY INSIGHTS FROM THE SINGLE PLOT")
print("="*80)

# Calculate optimal points for console output
efficiency_arr = reduction_arr / energy_arr
best_eff_idx = np.argmax(efficiency_arr)
best_agg = agg_arr[best_eff_idx]
best_energy = energy_arr[best_eff_idx]
best_reduction = reduction_arr[best_eff_idx]

reduction_50_idx = np.argmin(np.abs(reduction_arr - 50))
agg_50 = agg_arr[reduction_50_idx]
energy_50 = energy_arr[reduction_50_idx]

ramp_derivative = -np.gradient(ramp_arr, agg_arr)
max_derivative = np.max(ramp_derivative)
knee_idx = np.where(ramp_derivative < max_derivative * 0.5)[0]

print(f"\nANNOTATION VALUES AT 0.1 INTERVALS (including 0):")
print(f"Aggression | Energy (kWh) | Ramp Rate (W/s) | Reduction (%)")
print("-" * 60)
for agg in [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
    idx = np.argmin(np.abs(agg_arr - agg))
    print(f"   {agg:.1f}     |     {energy_arr[idx]:.1f}     |      {ramp_arr[idx]:.0f}       |      {reduction_arr[idx]:.1f}")

print(f"\nTHREE DISTINCT REGIONS IDENTIFIED:")
print(f"   Region 1 (Agg 0.01-0.30): Light smoothing, minimal energy ({energy_arr[29]:.1f} kWh), ramp reduction {reduction_arr[29]:.1f}%")
print(f"   Region 2 (Agg 0.30-0.60): Medium smoothing, moderate energy ({energy_arr[59]:.1f} kWh), ramp reduction {reduction_arr[59]:.1f}%")
print(f"   Region 3 (Agg 0.60-1.00): Heavy smoothing, high energy ({energy_arr[-1]:.1f} kWh), ramp reduction {reduction_arr[-1]:.1f}%")

print(f"\nRECOMMENDED OPERATING POINTS:")
print(f"   • Conservative (best efficiency): Agg = {best_agg:.2f}")
print(f"   • Balanced (50% reduction): Agg = {agg_50:.2f}")
if len(knee_idx) > 0:
    print(f"   • Diminishing returns threshold: Agg = {agg_arr[knee_idx[0]]:.2f}")

print(f"\nENERGY-RAMP TRADE-OFF:")
print(f"   • To achieve 50% reduction: Need {energy_50:.1f} kWh")
print(f"   • To achieve 80% reduction: Need ~{energy_arr[np.argmin(np.abs(reduction_arr - 80))]:.1f} kWh")
print(f"   • To achieve 90% reduction: Need ~{energy_arr[np.argmin(np.abs(reduction_arr - 90))]:.1f} kWh")

print("\n" + "="*80)
