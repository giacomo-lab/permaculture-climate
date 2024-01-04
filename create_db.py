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
    #print(variable)

    # Convert to DataFrame and reset index to flatten the data
    df = ds.to_dataframe().reset_index()

    # Add a column for the variable name
    df['variable'] = variable + 'prediction'

    # Concatenate the DataFrame with the main DataFrame
    df_all = pd.concat([df_all, df])

# Create a SQLite database
conn = sqlite3.connect('data.db')

# Store the DataFrame in SQLite table
df_all.to_sql('prediction_data', conn, if_exists='replace', index=False)



#climate tables (one table for each varibale)


# Open the GRIB file
filename = "past_climate.grib"
variables = ['2t', '10v', '10u', 'tp', 'tcc']
datasets = {}

for var in variables:
    ds = xr.open_dataset(filename, engine='cfgrib', backend_kwargs={'filter_by_keys': {'shortName': var}})
    datasets[var] = ds

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