# Energy Assessment of Rooftop Solar PV and Ramp Rate Mitigation Using the OSM-MEPS Model in Westville-Durban, South Africa

## System Overview

<img src="rts.png" alt="PV rooftop" width="700" height="auto"/>


# Feasible Rooftop PV Field Segments

| Segment | Tilt (°) | Azimuth (°) | No. of Modules |
|---------|-----------|-------------|----------------|
| 1       | 5.6       | 319.88      | 32             |
| 2       | 2.8       | 146.61      | 32             |
| 3       | 5.0       | 326.42      | 32             |
| 4       | 3.0       | 315.21      | 32             |
| 5       | 3.0       | 134.65      | 64             |


![PV ENERGY MODELS](Aurora_PVLIB_OSMMEPS_PVWATTS.png
)

# System Configuration
- **Total panels:** 192  
- **Panel power:** 600 W each  
- **Total DC capacity:** 115.2 kW  

---

## Processing Segments
1. **Segment 1:** 32 panels, tilt = 5.6°, azimuth = 319.88214°  
2. **Segment 2:** 32 panels, tilt = 2.8°, azimuth = 146.6122°  
3. **Segment 3:** 32 panels, tilt = 5.0°, azimuth = 326.42346°  
4. **Segment 4:** 32 panels, tilt = 3.0°, azimuth = 315.20587°  
5. **Segment 5:** 64 panels, tilt = 3.0°, azimuth = 134.65346°  

---

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
- **Max Ramp Rate:** 118.7 W/s at 2024-01-12 11:30:00+00:00  
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
**Event at 2024-01-12 11:30:00+00:00**
- **Power:** 61.8 → 26.3 kW (Δ: -35.6 kW)  
- **GHI:** 758.0 → 290.0 W/m²  
- **Cloud:** 23.6% → 70.6%  
- **Calculated Ramp:** -118.7 W/s  


![PV Smoothing Illustration](smoothing.png)


# Smoothing Algorithm

**Detected daily pattern:**
- Peak: 95.8 kW at 2024-01-12 09:55:00+00:00
- Sunrise: 2024-01-12 05:00:00+00:00
- Sunset: 2024-01-12 15:30:00+00:00

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
- Original: 2024-01-12 09:55:00+00:00
- Smoothing/Bell Curve: 2024-01-12 09:45:00+00:00
- Basic: 2024-01-12 09:45:00+00:00

**Morning-Afternoon Symmetry:**
- Original: 3.997
- Bell Curve: 4.018
- Closer to 1.0 = better symmetry preservation


