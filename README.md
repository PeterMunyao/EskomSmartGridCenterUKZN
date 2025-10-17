# Energy Assessment of Rooftop Solar PV and Ramp Rate Mitigation Using the OSM-MEPS Model in Westville-Durban, South Africa
This project simulates PV smoothing and battery operation.

## System Overview

![PV Smoothing Illustration](rts.png)

# Feasible Rooftop PV Field Segments

| Segment | Tilt (°) | Azimuth (°) | No. of Modules |
|---------|-----------|-------------|----------------|
| 1       | 5.6       | 319.88      | 32             |
| 2       | 2.8       | 146.61      | 32             |
| 3       | 5.0       | 326.42      | 32             |
| 4       | 3.0       | 315.21      | 32             |
| 5       | 3.0       | 134.65      | 64             |


![PV Smoothing Illustration](max_ramp.png)

# OSM-MEPS Detailed Analysis

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
