# === IMPORT LIBRARIES ===
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import pvlib
from pvlib.irradiance import get_total_irradiance
from pvlib.temperature import sapm_cell
from pvlib.pvsystem import pvwatts_dc

# === LOAD AURORA MULTI-YEAR AVERAGES ===
aurora_csv = 'Aurora_Multi_Year_Averages_2021_2022.csv'
aurora_avg_df = pd.read_csv(aurora_csv)
aurora_dates = pd.date_range(start='2024-01-01', periods=365, freq='D')
aurora_energy_2021 = pd.Series(aurora_avg_df['Year_2021_kWh'].values, index=aurora_dates, name='Aurora_2021')

# === LOAD WEATHER DATA ===
weather_csv = 'csv_-29.815268_30.946439_fixed_23_0_PT5M.csv'
df = pd.read_csv(weather_csv)
df['period_end'] = pd.to_datetime(df['period_end'], utc=True)
df.set_index('period_end', inplace=True)
df = df[(df.index >= '2024-01-01') & (df.index < '2025-01-01')]
df.index = df.index.tz_convert('Africa/Johannesburg')

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

# === PLOTTING WITH DOTTED LINES AND UNIFORM SCALING ===
plt.rcParams["font.family"] = "Garamond"
fig, ax = plt.subplots(figsize=(13, 8), facecolor='#f0f0f0')
ax.set_facecolor('#f0f0f0')

# Plot with dotted lines for some models and uniform styling
ax.plot(daily_energy_pvlib.index, daily_energy_pvlib, 
        label="PVLIB (2024)", 
        color='red', 
        linewidth=2.5,
        linestyle='--')  # Solid line for PVLIB

ax.plot(daily_energy_osm.index, daily_energy_osm, 
        label="OSM-MEPS (2024)", 
        color='green', 
        linewidth=2.5,
        linestyle='-')  # Dashed line for OSM-MEPS

ax.plot(daily_energy_pvwatts.index, daily_energy_pvwatts, 
        label="PVWatts (2024)", 
        color='orange', 
        linewidth=2.5,
        linestyle=':')  # Dotted line for PVWatts

ax.plot(aurora_energy_2021.index, aurora_energy_2021, 
        label="Aurora Solar (2021/22 Averaged)", 
        color='blue', 
        linewidth=2.5, 
        alpha=0.8,
        linestyle='-.')  # Dash-dot line for Aurora

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

# Add performance metrics below plot
performance_text = f"""
Annual Energy (kWh) | PVLIB: {annual_energy_pvlib:,.0f} | OSM-MEPS: {annual_energy_osm:,.0f}
PVWatts: {annual_energy_pvwatts:,.0f} | Aurora Solar (2021/22 Averaged): {annual_energy_aurora:,.0f}
System Capacity: {total_system_capacity_kw:.1f} kW DC | {num_panels_total} × {panel_power_max}W panels
"""

fig.text(0.5, -0.09, performance_text, ha='center', va='bottom', fontsize=20, 
         bbox=dict(boxstyle="round,pad=0.8", facecolor="lightgray", alpha=0.5),
         transform=fig.transFigure)

plt.subplots_adjust(bottom=0.2)
plt.savefig("Aurora_PVlib_Osmmeps_PVwatts.pdf", format="pdf", bbox_inches='tight', dpi=700)
plt.show()

# Print scaling verification
print(f"\n=== POWER SCALING VERIFICATION ===")
print(f"Peak daily energy values:")
print(f"  PVLIB: {daily_energy_pvlib.max():.1f} kWh")
print(f"  OSM-MEPS: {daily_energy_osm.max():.1f} kWh")
print(f"  PVWatts: {daily_energy_pvwatts.max():.1f} kWh")
print(f"  Aurora: {aurora_energy_2021.max():.1f} kWh")
