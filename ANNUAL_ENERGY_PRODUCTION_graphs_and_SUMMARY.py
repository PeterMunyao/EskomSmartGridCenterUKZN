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

df.index = df.index.tz_convert('Africa/Johannesburg')

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
num_panels_total = 32+32+32+32+64  # Total modules in all segments

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
    actual_power = scaled_power * (1 - 0.01)  # 1% system loss
    df["AC_Power_kW_osm_total"] += actual_power / 1000  # kW

# === ENERGY CALCULATION ===
df["Energy_kWh_pvlib"] = df["AC_Power_kW_pvlib_total"] * (5/60)
df["Energy_kWh_osm"] = df["AC_Power_kW_osm_total"] * (5/60)

daily_energy_pvlib = df["Energy_kWh_pvlib"].resample('D').sum()
daily_energy_osm = df["Energy_kWh_osm"].resample('D').sum()

annual_energy_pvlib = daily_energy_pvlib.sum()
annual_energy_osm = daily_energy_osm.sum()

# === PLOTTING ===
plt.rcParams["font.family"] = "Garamond"
fig, ax = plt.subplots(figsize=(14, 8), facecolor='#f0f0f0')
ax.set_facecolor('#f0f0f0')

ax.plot(daily_energy_pvlib.index, daily_energy_pvlib, label="PVLIB", color='orange', linewidth=2.5)
ax.plot(daily_energy_osm.index, daily_energy_osm, label="OSM-MEPS", color='green', linewidth=2.5)

ax.set_xlabel("Date", fontsize=16, fontweight='bold')
ax.set_ylabel("Daily Energy (kWh)", fontsize=16, fontweight='bold')
ax.set_title("Daily Energy Production - 2024", fontsize=18, fontweight='bold', pad=20)
ax.legend(fontsize=16)
ax.grid(True, linestyle='--', alpha=0.3)

# Format ticks
ax.tick_params(axis='both', which='major', labelsize=14)
for label in ax.get_xticklabels() + ax.get_yticklabels():
    label.set_fontweight('bold')

plt.tight_layout()

# Display annual results below the graph
results_text = f"""
ANNUAL ENERGY RESULTS:
        PVLIB Model: {annual_energy_pvlib:,.2f} kWh  and  OSM-MEPS Model: {annual_energy_osm:,.2f} kWh
   System Size: {num_panels_total} × {panel_power_max}W = {num_panels_total * panel_power_max / 1000:.1f} kW
"""

# Add text box below the plot
fig.text(0.5, 0.02, results_text, ha='center', va='bottom', fontsize=13, fontweight='bold',
         bbox=dict(boxstyle="round,pad=0.8", facecolor="lightgray", alpha=0.5),
         transform=fig.transFigure)

plt.subplots_adjust(bottom=0.25)  # Make space for the results text
plt.savefig("Annual_Energy_Production_2024.pdf", format="pdf", bbox_inches='tight', dpi=300)
plt.show()

# Print results to console as well
print("\n" + "="*50)
print("ANNUAL ENERGY PRODUCTION SUMMARY")
print("="*50)
print(f"Annual PVLIB Energy: {annual_energy_pvlib:,.2f} kWh")
print(f"Annual OSM-MEPS Energy: {annual_energy_osm:,.2f} kWh")
print(f"PVLIB produces {annual_energy_pvlib - annual_energy_osm:,.2f} kWh more "
      f"({((annual_energy_pvlib - annual_energy_osm)/annual_energy_osm*100):.1f}% higher)")
print(f"Total System DC Capacity: {num_panels_total * panel_power_max / 1000:.1f} kW")
print("="*50)
