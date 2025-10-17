import pandas as pd
import matplotlib.pyplot as plt
import calendar
import numpy as np


plt.rcParams['xtick.labelsize'] = 16
plt.rcParams['ytick.labelsize'] = 16


# === Load the CSV ===
file_path = 'csv_-29.815268_30.946439_fixed_23_0_PT5M.csv'
df = pd.read_csv(file_path)

# Ensure datetime index
df['period_end'] = pd.to_datetime(df['period_end'], utc=True)
df.set_index('period_end', inplace=True)
df.index = df.index.tz_convert('Africa/Johannesburg')
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
# Slightly taller and with a bit more column spacing
fig, axes = plt.subplots(6, 2, figsize=(10.5, 13.5), facecolor='#f9f9f9')  
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
    df_month = df[df.index.month == month].copy()
    df_month['hour'] = df_month.index.hour
    df_hourly = df_month.groupby('hour')[columns_to_plot].mean()

    # Plot DNI on primary y-axis
    line_dni, = ax.plot(df_hourly.index, df_hourly['ghi'], label='GHI', 
                        color=color_dict['ghi'], linewidth=1.5)
    ax.set_ylabel('GHI (W/m²)', fontsize=14)
    ax.set_ylim(0, df_hourly['ghi'].max() * 1.1)
    ax.set_xticks(range(0, 24, 3))
    ax.grid(True, linestyle=':', linewidth=0.4, color='gray')

    # Plot secondary y-axis
    ax2 = ax.twinx()
    line_rh, = ax2.plot(df_hourly.index, df_hourly['relative_humidity'], 
                        label='Relative Humidity (%)', color=color_dict['relative_humidity'],
                        linestyle='--', linewidth=1.3)
    line_cloud, = ax2.plot(df_hourly.index, df_hourly['cloud_opacity'], 
                           label='Cloud Opacity (%)', color=color_dict['cloud_opacity'],
                           linestyle='-', linewidth=1.3)
    line_temp, = ax2.plot(df_hourly.index, df_hourly['air_temp'], 
                          label='Air Temp (°C)', color=color_dict['air_temp'],
                          linestyle='-.', linewidth=1.3)
    ax2.set_ylim(0, 100)
    ax2.set_ylabel('Humidity / Temp (%)', fontsize=14)

    if month == 1:
        all_lines.extend([line_dni, line_rh, line_cloud, line_temp])
        all_labels.extend(['GHI (W/m²)', 'Relative Humidity (%)', 
                           'Cloud Opacity (%)', 'Air Temp (°C)'])

    # Month title
    ax.set_title(calendar.month_abbr[month], fontsize=14, fontweight='bold')
    if month > 10:
        ax.set_xlabel('Hour of Day', fontsize=14)


# === Layout Adjustments ===
# Extra horizontal space (wspace) prevents label overlap
plt.subplots_adjust(
    left=0.07, right=0.93, top=0.95, bottom=0.08, 
    hspace=0.45, wspace=0.40   # increased from 0.25 → 0.40
)

# Combined legend below all plots
fig.legend(all_lines, all_labels, loc='lower center', ncol=4, fontsize=16, frameon=False)

# Save final figure
plt.savefig(
    "SMART_GRID_MONTHLY_24HR_AVERAGED_GHI_CLOUDOPACITY_2024.pdf",
    format='pdf',
    bbox_inches='tight',
    facecolor=fig.get_facecolor()
)
plt.show()
