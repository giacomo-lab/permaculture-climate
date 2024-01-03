import xarray as xr
import sqlite3
import pandas as pd

# List of NetCDF files and corresponding variable names
files = [('prediction_data/eastward_near_surface_wind/uas_Amon_EC-Earth3-CC_ssp245_r1i1p1f1_gr_20160116-20461216_v20210113.nc', 'u_wind'),
         ('prediction_data/northward_near_surface_wind/vas_Amon_EC-Earth3-CC_ssp245_r1i1p1f1_gr_20160116-20461216_v20210113.nc', 'v_wind'),
         ('prediction_data/precipitation/pr_Amon_EC-Earth3-CC_ssp245_r1i1p1f1_gr_20160116-20461216_v20210113.nc', 'precipitation'),
         ('prediction_data/near_surface_air_temperature/tas_Amon_EC-Earth3-CC_ssp245_r1i1p1f1_gr_20160116-20461216_v20210113.nc', 'temperature')
         ]

# Initialize an empty DataFrame
df_all = pd.DataFrame()

for file, variable in files:
    # Load NetCDF file
    ds = xr.open_dataset(file)

    # Convert to DataFrame and reset index to flatten the data
    df = ds.to_dataframe().reset_index()

    # Add a column for the variable name
    df['variable'] = variable

    # Concatenate the DataFrame with the main DataFrame
    df_all = pd.concat([df_all, df])

# Create a SQLite database
conn = sqlite3.connect('prediction_data.db')

# Store the DataFrame in SQLite table
df_all.to_sql('prediction_data', conn, if_exists='replace', index=False)

conn.close()
print('Database created successfully.')