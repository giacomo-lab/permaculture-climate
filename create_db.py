import xarray as xr
import sqlite3
import pandas as pd
import numpy as np
import dask
import dask.dataframe as dd
import logging

#Set up logging
logging.basicConfig(filename='app.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s')

#
#List of NetCDF files with predicted climate data
files = [('src/data/prediction_data/eastward_near_surface_wind-ssp2_4_5_2016_2046.nc', 'u_wind'),
         ('src/data/prediction_data/northward_near_surface_wind-ssp2_4_5_2016_2046.nc', 'v_wind'),
         ('src/data/prediction_data/precipitation-ssp2_4_5_2016_2046.nc', 'precipitation'),
         ('src/data/prediction_data/near_surface_relative_humidity-ssp2_4_5_2016_2046.nc', 'relative_humidity'),
         ('src/data/prediction_data/near_surface_air_temperature-ssp2_4_5_2016_2046.nc', 'temperature')
         ]

# Initialize an empty DataFrame
df_all = pd.DataFrame()


for file, variable in files:
    try:
        # Load NetCDF file
        ds = xr.open_dataset(file)
        ds = ds.drop_vars(['lat_bnds', 'lon_bnds', 'time_bnds'])

        # Convert to DataFrame and reset index to flatten the data
        df = ds.to_dataframe().reset_index()

        # Add a column for the variable name
        df['variable'] = variable + '_prediction'

        # Concatenate the DataFrame with the main DataFrame
        df_all = pd.concat([df_all, df])
        df_all['lon'] = df_all['lon'].apply(lambda x: x-360 if x > 180 else x)
    except Exception as e:
        logging.error('Error processing file %s: %s', file, e)

# Create a SQLite database    
with sqlite3.connect('data.db') as conn:
    # Store the prediction dataframe in SQLite table
    df_all.to_sql('prediction_data', conn, if_exists='replace', index=False)

    print('Prediction_data table created successfully.')

    # Open the GRIB file with past data
    print('opening GRIB file')
    filename = "src/data/past_climate.grib"
    variables = ['tp', 'tcc', 'rh', '2t','2d','10v', '10u'] 
    datasets = {}

    # Set up Dask to use a single thread
    dask.config.set(scheduler='single-threaded')

    for var in variables:
        try:
            # Open the GRIB file with chunks
            ds = xr.open_dataset(filename, engine='cfgrib', backend_kwargs={'filter_by_keys': {'shortName': var}}, chunks={'time': 10})
            datasets[var] = ds
        except Exception as e:
            logging.error('Error opening dataset for variable %s: %s', var, e)

    #calculate relative humidity from temperature and dewpoint temperature
    def rh(dewpoint, temperature):
        return 100*(np.exp((17.625*dewpoint)/(243.04+dewpoint))/np.exp((17.625*temperature)/(243.04+temperature)))

    rh_all = rh(datasets['2d']['d2m']-273.15, datasets['2t']['t2m']-273.15)
    datasets['rh'] = xr.Dataset({'rh': xr.DataArray(rh_all, coords=datasets['2d']['d2m'].coords, dims=datasets['2d']['d2m'].dims)})

    #standardize tp to make it in the same format as the other variables 
    # Flatten the 'valid_time' coordinate from 2D to 1D
    datasets['tp']['valid_time'] = datasets['tp']['valid_time'].values.flatten()

    # Stack the 'time' and 'step' dimensions of the 'tp' variable into a single new dimension called 'total_time'
    datasets['tp']['tp'] = datasets['tp']['tp'].stack(total_time=('time', 'step'))

    # Assign the flattened 'valid_time' data to the 'total_time' coordinate
    datasets['tp'].coords["valid_time"] = ("total_time", datasets['tp']['valid_time'].data)

    # Swap the 'total_time' dimension with the 'valid_time' dimension
    datasets['tp'] = datasets['tp'].swap_dims({'total_time': 'valid_time'})

    # Drop the 'time', 'step', 'number', and 'surface' dimensions from 'tp_single_time_and_step' and assign the result to 'tp_dropped'
    tp_dropped = datasets['tp'].drop(['time','step','number','surface'])

    # Rename the 'valid_time' dimension to 'time' in 'tp_dropped' and assign the result back to 'datasets['tp']'
    datasets['tp'] = tp_dropped.rename({'valid_time': 'time'})

    # Drop all NA values in the 'time' dimension of 'datasets['tp']' and assign the result back to 'datasets['tp']'
    datasets['tp'] = datasets['tp'].dropna(dim='time', how='all')

    #TODO:check if the transpose works correctly
    # Reorder the dimensions of 'datasets['tp']' to have 'time' as the first dimension
    datasets['tp'] = datasets['tp'].transpose('time', 'latitude', 'longitude')

    print('writing to database')
    for var, ds in datasets.items():
        try:
            print('processing', var)
            with dask.config.set(**{'array.slicing.split_large_chunks': True}):
            # Convert the Dataset to a DataFrame and reset the index
                df = ds.to_dask_dataframe().reset_index()

            #print(df.dtypes)
            #print(len(df))
            # Convert the DataFrame to a Dask DataFrame
            #df = dd.from_pandas(df, npartitions=4)  

            df['variable'] = var
            print('writing', var, 'to database')

            # Write the DataFrame to the SQLite database in chunks
            # Use the variable name as the table name
            # Write the DataFrame to the SQLite database in chunks
            # Use the variable name as the table name
            print('Number of partitions:', df.npartitions)
            print('Size of DataFrame:', len(df))
            for i in range(df.npartitions):
                # Compute the partition to load the data into memory and convert it to a Pandas DataFrame
                partition_pd = df.get_partition(i).compute()
                #print(type(partition_pd))
                #print(type(partition_pd.empty)) 
                    
                # Convert timedelta columns to strings
                for col in partition_pd.columns:
                    if partition_pd[col].dtype == 'timedelta64[ns]':
                        partition_pd[col] = partition_pd[col].astype(str)
                # Check if the DataFrame is empty
                if not partition_pd.empty:
                    # Write the DataFrame to the database
                    partition_pd.to_sql(var + "_climate", conn, if_exists='append', index=False)
                    # Commit the transaction to ensure the data is saved to the database
                    conn.commit()
        except Exception as e:
            logging.error('Error writing variable %s to database: %s', var, e)

print('Database created successfully.')