import xarray as xr
import sqlite3
import pandas as pd
import numpy as np
import dask.dataframe as dd
import logging

#Set up logging
logging.basicConfig(filename='app.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s')

######################
#Open grib file with past data, prepare it and write it to data.db

filename = "src/data/past_climate.grib"
#names of the variables as saved in the xarrays within the grib file
variables = ['tp', 'tcc',  '2t','2d','10v', '10u'] 
#empty list, append all opened and prepared xarray datasets
past_ds_list = []



for var in variables:
    if var == 'tp':
        #open total precipitation from grib file
        ds_tp = xr.open_dataset(filename, engine='cfgrib', backend_kwargs={'filter_by_keys': {'shortName': var}})
        
        #standardize tp to make it in the same format as the other variables 
        # Flatten the 'valid_time' coordinate from 2D to 1D
        ds_tp['valid_time'] = ds_tp['valid_time'].values.flatten()
        
        # Stack the 'time' and 'step' dimensions of the 'tp' variable into a single new dimension called 'total_time'
        ds_tp['tp'] = ds_tp['tp'].stack(total_time=('time', 'step'))
        
        # Assign the flattened 'valid_time' data to the 'total_time' coordinate
        ds_tp.coords["valid_time"] = ("total_time", ds_tp['valid_time'].data)
        
        # Swap the 'total_time' dimension with the 'valid_time' dimension
        ds_tp['tp'] = ds_tp['tp'].swap_dims({'total_time': 'valid_time'})
        
        # Drop the 'time', 'step', 'number', and 'surface' dimensions/variables
        ds_tp_dropped = ds_tp.drop_dims(['time', 'step'])
        ds_tp_dropped = ds_tp_dropped.drop_vars(['number', 'surface'])
        
        # Rename the 'valid_time' dimension to 'time' in 'tp_dropped' and assign the result back to 'datasets['tp']'
        ds_tp_dropped = ds_tp_dropped.rename({'valid_time' : 'time'})
        
        # Drop all NA values in the 'time' dimension of 'datasets['tp']' and assign the result back to 'datasets['tp']'
        ds_tp_dropped = ds_tp_dropped.dropna(dim='time', how='all')
        
        # Reorder the dimensions of 'datasets['tp']' to have 'time' as the first dimension
        ds_tp_dropped = ds_tp_dropped.transpose('time', 'latitude', 'longitude')
        
        #modify time by substracting 1 h, in order to use the same format as the other variables
        ds_tp_dropped['time'] = ds_tp_dropped['time'] - np.timedelta64(1, 'h')

        
        #eppend to dataset list
        past_ds_list.append(ds_tp_dropped)     
        
    else:
        #open the rest of the datasets and append them to the list
        ds_past = xr.open_dataset(filename, engine='cfgrib', backend_kwargs={'filter_by_keys': {'shortName': var}})

        #get rid of unneeded coordinates to minimize the final table
        ds_past_dropped = ds_past.reset_coords(['valid_time', 'step', 'number', 'surface'], drop = True)

        
        past_ds_list.append(ds_past_dropped)

#merge all datasets in past_ds_list into one. All duplicate cols like lat and lons are merged, end result only has them once
merged_ds_past = xr.merge(past_ds_list)

#convert dxarray dataset to pandas dataframe
past_df = merged_ds_past.to_dataframe().reset_index()

#write dataframe to data.db database
with sqlite3.connect('data.db') as conn:
    past_df.to_sql('past_data', conn, if_exists='replace', index=False)

print('Prediction_data table created successfully.')


##########################
#Open prediction data from the netcdf files and wrtie it to the database


#get a list of paths of all the netcdf files containing the different variables.

nc_folder = 'src/data/prediction_data'
nc_files = [file_path for file_path in glob.glob(os.path.join(nc_folder, '*.nc'))]

# Initialize an empty list to append the single datasets to
pred_ds_list = []

# loop trough the files and load the datasets 
for file in nc_files:
    #try except block needed for log file
    try:
        # Load NetCDF file
        pred_ds = xr.open_dataset(file)

        #append the arrays to the list
        pred_ds_list.append(pred_ds)
        
    except Exception as e:
        logging.error('Error opening dataset for variable %s: %s', e)

# merge all datasets into one, things like lat, lon and time, that are the same for all, are merged, variable values are kept. 
# compat = override needed for height, a dimension present only in some datasets. Ignores it if it is not present 
pred_ds_merged = xr.merge(pred_ds_list, compat='override')


# drop unneeded bnds dimension and all variables it includes
pred_ds_dropped = pred_ds_merged.drop_dims('bnds')
pred_ds_dropped = pred_ds_dropped.reset_coords(drop = True)

# convert xr dataset to pd dataframe
pred_df = pred_ds_dropped.to_dataframe().reset_index()

# Adjust longitudes to have the same format as the past dataset
pred_df['lon'] = pred_df['lon'].apply(lambda x: x - 360 if x > 180 else x)

# Store the prediction dataframe in SQLite table 
with sqlite3.connect('data.db') as conn:
    pred_df.to_sql('prediction_data', conn, if_exists='replace', index=False)
    
