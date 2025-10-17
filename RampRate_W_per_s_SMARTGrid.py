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
