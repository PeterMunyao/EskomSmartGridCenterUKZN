# Energy Assessment of Rooftop Solar PV and Ramp Rate Mitigation Using the OSM-MEPS Model in Westville-Durban, South Africa


## 🕒 NB: Ensure Manual Time Zone Conversion of Solcast DNV data (SAST = UTC + 2 Hours)

## === LOAD WEATHER DATA - SHIFT CSV TIME BY +2 HOURS ===
file_path = 'csv_-29.815268_30.946439_fixed_23_0_PT5M.csv'

## Read CSV and parse datetime
df = pd.read_csv(file_path)
df['period_end'] = pd.to_datetime(df['period_end'])  # Original timezone
df.set_index('period_end', inplace=True)

## Apply manual timezone shift (SAST = UTC +2)
df.index = df.index + pd.Timedelta(hours=2)

## Optional: filter desired date range
df = df[(df.index >= '2024-01-01') & (df.index < '2025-01-01')]


## System Overview

<img src="SGB.png" alt="PV rooftop" width="700" height="auto"/>


# Feasible Rooftop PV Field Segments

| Segment | Tilt (°) | Azimuth (°) | No. of Modules |
|---------|-----------|-------------|----------------|
| 1       | 5.6       | 319.88      | 32             |
| 2       | 2.8       | 146.61      | 32             |
| 3       | 5.0       | 326.42      | 32             |
| 4       | 3.0       | 315.21      | 32             |
| 5       | 3.0       | 134.65      | 64             |


# Summary of Annual and Hourly Statistical Comparison Among PV Models

| Model | Annual (kWh) | Mean (kWh/h) | SD (kWh/h) |
|-------|-------------|-------------|------------|
| PVLIB | 149,465 | 17.060 | 24.582 |
| OSM-MEPS | 147,892 | 16.881 | 25.048 |
| PVWatts | 147,970 | 16.890 | 24.336 |
| Aurora (2021) | 161,936 | 18.535 | 6.131 |

*ANOVA (Hourly):* F = 12.0099, p = 7.45×10⁻⁸ (significant)  
*Tukey HSD:* Aurora differs from others (p < 0.05)

# 🌞 Bell Curve PV Smoothing with Battery Dispatch

This repository implements a **battery-assisted PV smoothing algorithm** that reshapes raw photovoltaic output into a smooth, grid-friendly bell curve while respecting:

- Battery power limits
- State-of-charge (SOC) constraints
- Ramp-rate limits
- Time-of-day solar behavior

---

## 🧠 Core Algorithm (What and Why)

This model is not just smoothing — it is a **hybrid control system** combining:

- 📉 PV power post processing → removes noise and short-term fluctuations  
- ⚡ Control theory → enforces ramp-rate constraints  
- 🔋 Energy storage dynamics → battery SOC evolution  
- 🌞 Solar structure preservation → maintains bell-curve PV shape  

---

## ⚙️ Python Implementation (Fully Commented with Engineering Rationale)

```python
import numpy as np
import pandas as pd


def bell_curve_smoothing(power_data, battery_power_kw, battery_energy_kwh, 
                        target_ramp_rate=20.0, smoothing_aggression=0.8):
    """
    PURPOSE:
    --------
    This function simulates a battery that reshapes PV output into a smooth
    and grid-compliant signal while preserving the natural solar bell curve.

    WHY THIS EXISTS:
    ----------------
    Raw PV is:
        - noisy (clouds, irradiance variation)
        - non-grid-friendly (high ramp rates)

    So we introduce:
        - smoothing (to stabilize output)
        - battery dispatch (to physically realize smoothing)
    """

    # ------------------------------------------------------------
    # STEP 1: STATE INITIALIZATION
    # ------------------------------------------------------------

    smoothed_power = power_data.copy()

    # Battery power signal:
    # +ve = charging (absorbing excess PV)
    # -ve = discharging (supplying deficit)
    battery_power = np.zeros(len(power_data))

    # Battery energy state (SOC in kWh)
    battery_soc = np.zeros(len(power_data))

    # WHY 50% INITIAL SOC?
    # ---------------------
    # Provides symmetric flexibility:
    #   - room to charge during midday PV peaks
    #   - room to discharge during ramps
    battery_soc[0] = battery_energy_kwh / 2


    # ------------------------------------------------------------
    # STEP 2: CREATE IDEAL SOLAR REFERENCE (BELL CURVE)
    # ------------------------------------------------------------

    # WHY MOVING AVERAGE?
    # --------------------
    # It approximates "clear sky irradiance behavior"
    # and removes high-frequency noise.

    target_bell_curve = power_data.rolling(
        '60min', center=True, min_periods=1
    ).mean()


    # ------------------------------------------------------------
    # STEP 3: RAMP RATE CONSTRAINT (GRID REQUIREMENT)
    # ------------------------------------------------------------

    # WHY THIS MATTERS:
    # ------------------
    # Grid operators limit how fast generation can change.

    # Convert ramp rate to 5-minute timestep constraint
    max_ramp_kw_per_5min = target_ramp_rate * 300 / 1000


    # ------------------------------------------------------------
    # STEP 4: TIME-STEPPED SIMULATION LOOP
    # ------------------------------------------------------------

    for i in range(1, len(power_data)):

        current_power = power_data.iloc[i]

        # WHY USE PREVIOUS VALUE?
        # ------------------------
        # This introduces "system memory" → prevents abrupt jumps.
        previous_smoothed = smoothed_power.iloc[i - 1]

        current_time = power_data.index[i]
        hour_decimal = current_time.hour + current_time.minute / 60


        # --------------------------------------------------------
        # STEP 5: MULTI-SCALE SIGNAL ESTIMATION
        # --------------------------------------------------------

        # SHORT-TERM SIGNAL:
        # -------------------
        # Captures fast fluctuations (cloud transients)
        short_term_avg = power_data.iloc[max(0, i-3):i+1].mean()

        # MEDIUM-TERM SIGNAL:
        # --------------------
        # Represents expected solar bell shape trend
        medium_term_avg = target_bell_curve.iloc[i]


        # --------------------------------------------------------
        # STEP 6: TIME-OF-DAY ADAPTATION
        # --------------------------------------------------------

        # WHY THIS EXISTS:
        # ----------------
        # PV dynamics are not symmetric:
        #   - midday = stable high irradiance
        #   - morning/evening = steep ramps

        if 10 <= hour_decimal <= 14:
            # Preserve peak structure (avoid over-smoothing)
            bell_weight = 0.7
        else:
            # Follow natural ramps more aggressively
            bell_weight = 0.4


        # --------------------------------------------------------
        # STEP 7: TARGET CONSTRUCTION (HYBRID MODEL)
        # --------------------------------------------------------

        # WHY BLEND TWO SIGNALS?
        # -----------------------
        # We combine:
        #   - physics-based expectation (medium term)
        #   - real observed variation (short term)

        bell_target = (
            bell_weight * medium_term_avg +
            (1 - bell_weight) * short_term_avg
        )


        # --------------------------------------------------------
        # STEP 8: RAMP RATE LIMITING (SAFETY FILTER)
        # --------------------------------------------------------

        # WHY THIS STEP IS CRITICAL:
        # --------------------------
        # Prevents unrealistic step changes that would:
        #   - violate grid codes
        #   - stress inverter/battery systems

        ramp_limited_target = previous_smoothed + np.clip(
            bell_target - previous_smoothed,
            -max_ramp_kw_per_5min,
            max_ramp_kw_per_5min
        )


        # --------------------------------------------------------
        # STEP 9: FINAL CONTROL BLEND
        # --------------------------------------------------------

        # smoothing_aggression controls system behavior:
        #   1.0 → maximum smoothing (grid-friendly)
        #   0.0 → raw PV tracking

        final_target = (
            smoothing_aggression * ramp_limited_target +
            (1 - smoothing_aggression) * bell_target
        )


        # --------------------------------------------------------
        # STEP 10: BATTERY DISPATCH LOGIC
        # --------------------------------------------------------

        # CORE PHYSICAL INTERPRETATION:
        # ------------------------------
        # Battery acts as a buffer:
        #   - absorbs excess PV (charging)
        #   - supplies deficits (discharging)

        required_battery_power = final_target - current_power

        battery_power[i] = np.clip(
            required_battery_power,
            -battery_power_kw,
            battery_power_kw
        )


        # --------------------------------------------------------
        # STEP 11: ENERGY BALANCE (SOC DYNAMICS)
        # --------------------------------------------------------

        # WHY 5/60?
        # ----------
        # Converts kW → kWh over 5-minute timestep

        energy_change = battery_power[i] * (5 / 60)
        battery_soc[i] = battery_soc[i - 1] + energy_change


        # --------------------------------------------------------
        # STEP 12: SOC PROTECTION (PHYSICAL CONSTRAINTS)
        # --------------------------------------------------------

        # WHY THIS EXISTS:
        # ----------------
        # Prevents unrealistic battery operation:
        #   - deep discharge damage
        #   - overcharge stress

        soc_adjustment = 0

        if battery_soc[i - 1] < battery_energy_kwh * 0.2:
            # LOW SOC → discourage discharge
            if battery_power[i] < 0:
                soc_adjustment = battery_power[i] * 0.3
            elif battery_power[i] > 0:
                soc_adjustment = battery_power[i] * 0.1

        elif battery_soc[i - 1] > battery_energy_kwh * 0.9:
            # HIGH SOC → discourage charging
            if battery_power[i] > 0:
                soc_adjustment = -battery_power[i] * 0.3
            elif battery_power[i] < 0:
                soc_adjustment = battery_power[i] * 0.1


        battery_power[i] += soc_adjustment

        # Re-apply hardware limits after correction
        battery_power[i] = np.clip(
            battery_power[i],
            -battery_power_kw,
            battery_power_kw
        )


        # --------------------------------------------------------
        # STEP 13: FINAL SOC UPDATE
        # --------------------------------------------------------

        energy_change = battery_power[i] * (5 / 60)
        battery_soc[i] = battery_soc[i - 1] + energy_change

        # ENSURE PHYSICAL VALIDITY
        battery_soc[i] = np.clip(
            battery_soc[i],
            0,
            battery_energy_kwh
        )


        # --------------------------------------------------------
        # STEP 14: FINAL OUTPUT SIGNAL
        # --------------------------------------------------------

        # WHAT THE GRID SEES:
        # -------------------
        # Smoothed PV = raw PV + battery correction

        smoothed_power.iloc[i] = current_power + battery_power[i]

    return smoothed_power, battery_power, battery_soc

# System Configuration
- **Total panels:** 192  
- **Panel power:** 600 W each  
- **Total DC capacity:** 115.2 kW  


## Annual Energy Results
- **PVLIB:** 155,724 kWh  
- **OSM-MEPS:** 147,892 kWh  
- **PVWatts:** 154,167 kWh  
- **Aurora (2021):** 162,646 kWh

![PV ramp calculation](max_ramp.png)

## Power Characteristics
- **Max Power:** 95.8 kW  
- **Min Power:** 0.0 kW  
- **Power Range:** 95.8 kW  

## Ramp Analysis
- **Max Ramp Rate:** 118.7 W/s at 2024-01-12 13:30:00+00:00  
- **Max 5-min Power Change:** 35.6 kW  

## Meteorological Conditions
- **Max GHI:** 1053.0 W/m²  
- **Max Cloud Opacity:** 95.9%  
- **Max Humidity:** 91.2%  

## Battery Sizing (OSM-MEPS)
- **Power Rating:** 42.7 kW  
- **Energy Capacity:** 85.4 kWh  
- **Can handle:** 120.0% of worst-case swing (+20.0% margin)  

# Max Ramp Event Analysis
**Event at 2024-01-12 13:30:00+00:00**
- **Power:** 61.8 → 26.3 kW (Δ: -35.6 kW)  
- **GHI:** 758.0 → 290.0 W/m²  
- **Cloud:** 23.6% → 70.6%  
- **Calculated Ramp:** -118.7 W/s  


![PV Smoothing Illustration](smoothing.png)


# Smoothing Algorithm

**Detected daily pattern:**
- Peak: 95.8 kW at 2024-01-12 11:55:00+00:00
- Sunrise: 2024-01-12 07:00:00+00:00
- Sunset: 2024-01-12 17:30:00+00:00

## Performance Comparison

**Original System:**
- Max Ramp: 118.7 W/s
- Power Range: 95.8 kW

**Basic Smoothing:**
- Max Ramp: 34.6 W/s
- Ramp Reduction: 70.8%

**Bell Curve Smoothing:**
- Max Ramp: 22.3 W/s
- Ramp Reduction: 81.2%
- Peak Preservation: -1.2% vs basic

**Battery Usage:**
- Max Charge (Bell): 28.2 kW
- Max Discharge (Bell): 22.6 kW
- Battery Utilization: 66.0%

## Bell Curve Preservation Analysis

**Peak Time Alignment:**
- Original: 2024-01-12 11:55:00+00:00
- Smoothing/Bell Curve: 2024-01-12 11:45:00+00:00
- Basic: 2024-01-12 11:45:00+00:00

**Morning-Afternoon Symmetry:**
- Original: 3.997
- Bell Curve: 4.018
- Closer to 1.0 = better symmetry preservation


