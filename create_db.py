import xarray as xr
import sqlite3
import pandas as pd
import numpy as np

# List of NetCDF files and corresponding variable names
files = [('prediction_data/eastward_near_surface_wind/uas_Amon_EC-Earth3-CC_ssp245_r1i1p1f1_gr_20160116-20461216_v20210113.nc', 'u_wind'),
         ('prediction_data/northward_near_surface_wind/vas_Amon_EC-Earth3-CC_ssp245_r1i1p1f1_gr_20160116-20461216_v20210113.nc', 'v_wind'),
         ('prediction_data/precipitation/pr_Amon_EC-Earth3-CC_ssp245_r1i1p1f1_gr_20160116-20461216_v20210113.nc', 'precipitation'),
         ('prediction_data/near_surface_relative_humidity/hurs_Amon_EC-Earth3-CC_ssp245_r1i1p1f1_gr_20160116-20461216_v20210113.nc', 'relative_humidity'),
         ('prediction_data/near_surface_air_temperature/tas_Amon_EC-Earth3-CC_ssp245_r1i1p1f1_gr_20160116-20461216_v20210113.nc', 'temperature')
         ]

# Initialize an empty DataFrame
df_all = pd.DataFrame()

for file, variable in files:
    # Load NetCDF file
    ds = xr.open_dataset(file)
    ds = ds.drop_vars(['lat_bnds', 'lon_bnds', 'time_bnds'])
    #print(variable)

    # Convert to DataFrame and reset index to flatten the data
    df = ds.to_dataframe().reset_index()

    # Add a column for the variable name
    df['variable'] = variable + '_prediction'

    # Concatenate the DataFrame with the main DataFrame
    df_all = pd.concat([df_all, df])
    df_all['lon'] = df_all['lon'].apply(lambda x: x-360 if x > 180 else x)

# Create a SQLite database
conn = sqlite3.connect('data.db')

# Store the DataFrame in SQLite table
df_all.to_sql('prediction_data', conn, if_exists='replace', index=False)

print('Prediction_data table created successfully.')
#climate tables (one table for each varibale)

# Open the GRIB file
filename = "past_climate.grib"
variables = ['2t','2d','10v', '10u', 'tp', 'tcc', 'rh']
datasets = {}

for var in variables:
    ds = xr.open_dataset(filename, engine='cfgrib', backend_kwargs={'filter_by_keys': {'shortName': var}})
    datasets[var] = ds

#calculate relative humidity from temperature and dewpoint temperature
def rh(dewpoint, temperature):
    return 100*(np.exp((17.625*dewpoint)/(243.04+dewpoint))/np.exp((17.625*temperature)/(243.04+temperature)))


rh_all = rh(datasets['2d']['d2m']-273.15, datasets['2t']['t2m']-273.15)
datasets['rh'] = xr.Dataset({'rh': xr.DataArray(rh_all, coords=datasets['2d']['d2m'].coords, dims=datasets['2d']['d2m'].dims)})


# Connect to the SQLite database
db_file = 'data.db'
conn = sqlite3.connect(db_file)

for var, ds in datasets.items():
    # Convert the Dataset to a DataFrame and reset the index
    df = ds.to_dataframe().reset_index()

    # Convert timedelta columns to strings
    for col in df.columns:
        if df[col].dtype == 'timedelta64[ns]':
            df[col] = df[col].astype(str)

    # Add a column for the variable name
    df['variable'] = var
    print('writing', var, 'to database')

    # Write the DataFrame to the SQLite database
    # Use the variable name as the table name
    df.to_sql(var + "_climate", conn, if_exists='replace', index=False)

conn.close()
print('Database created successfully.')