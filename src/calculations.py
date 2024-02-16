import dask
import pandas as pd
import xarray as xr
from geopy.geocoders import Nominatim
import time
import sqlite3


def compute_climatology(lat, lon, db_file='data.db'):
   
    conn = sqlite3.connect(db_file)
    datasets = {}
    
    # list of names of tables and columns containing the values within the tables. 2 variables needed as per CDS default the names are different 
    tables = ['10v', '10u', '2t', 'tp', 'tcc', 'rh']
    columns = ['v10', 'u10', 't2m', 'tp', 'tcc', 'rh']
    tables_and_column = dict(zip(tables, columns))

    #define coordinates for the creation of xarrays later on
    coordinates = ['latitude', 'longitude', 'time']
    coordinates_tp = ['latitude', 'longitude', 'time', 'step']

    query = f"""
            SELECT *
            FROM past_data
            WHERE latitude BETWEEN {lat - 1} AND {lat + 1}
            AND longitude BETWEEN {lon - 1} AND {lon + 1}
            """
    
    
    # put query result into a pandas dataframe
    past_df = pd.read_sql_query(query, conn)
    #TODO Maybe do this before, when creating database?
    # Convert the 'time' coordinate to datetime64
    past_df['time'] = pd.to_datetime(df['time'])

    #TODO qua convertiamo a un xarray? A sto punto non ci converrebbe fare il database con xarray direttamente? amesso che sia possibile 
    datasets[var] = xr.Dataset.from_dataframe(df.set_index(coordinates_tp))

    
    
    
    
    #Loop trough the tables with SQL querys in order to ectract the needed data for specified lat and lon values
    for var in tables_and_column:
        #treat tp differently as it also needs the col steps, which the other variables dont need. Minimize number of imported cols for speed
        col = tables_and_column[var]

        if var == 'tp':

            query = f"""
            SELECT time, longitude, latitude, step, [{col}]
            FROM [{var}_climate]
            WHERE latitude BETWEEN {lat - 1} AND {lat + 1}
            AND longitude BETWEEN {lon - 1} AND {lon + 1}
            """
            # put query result into a pandas dataframe
            df = pd.read_sql_query(query, conn)
            # Convert the 'time' coordinate to datetime64
            df['time'] = pd.to_datetime(df['time'])
            
            datasets[var] = xr.Dataset.from_dataframe(df.set_index(coordinates_tp))

        else:     
            #Same as above but with all other tables
            query = f"""
            SELECT time, longitude, latitude, [{col}]
            FROM [{var}_climate]
            WHERE latitude BETWEEN {lat - 1} AND {lat + 1}
            AND longitude BETWEEN {lon - 1} AND {lon + 1}
            """
            df = pd.read_sql_query(query, conn)
            # Convert the 'time' coordinate to datetime64
            df['time'] = pd.to_datetime(df['time'])
            datasets[var] = xr.Dataset.from_dataframe(df.set_index(coordinates))

    conn.close()

    #Parallelize calculations for better performance
    chunksize = 600
    datasets['tp']['tp'] = datasets['tp']['tp'].chunk({'time': chunksize})
    datasets['2t']['t2m'] = datasets['2t']['t2m'].chunk({'time': chunksize})
    datasets['rh']['rh'] = datasets['rh']['rh'].chunk({'time': chunksize}) 
    datasets['10u']['u10'] = datasets['10u']['u10'].chunk({'time': chunksize})
    datasets['10v']['v10'] = datasets['10v']['v10'].chunk({'time': chunksize})
    datasets['tcc']['tcc'] = datasets['tcc']['tcc'].chunk({'time': chunksize})

    with dask.config.set(scheduler='threads'):  

        print("Calculating precipitation")

        # Average precipitation. Converting from m per hour to mm per month
        days_per_month = [31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        avg_prec = datasets['tp']['tp'].groupby('time.month').mean(['time', 'latitude', 'longitude', 'step'])*1000 * 24 * days_per_month

        print("Calculating temperature")

        #average temperature. Convert from K to C
        mean_spatial_temp = datasets['2t']['t2m'].mean(['latitude', 'longitude'])-273.15
        avg_temp = mean_spatial_temp.groupby('time.month').mean(['time'])
        mean_spatial_temp['month_year'] = mean_spatial_temp['time'].dt.strftime('%Y-%m')

        #Calculate average max temp
        max_monthly_temp = mean_spatial_temp.groupby('month_year').max()
        max_monthly_temp['month'] = max_monthly_temp['month_year'].str.slice(start=5, stop=7).astype(int)
        mean_max_temp = max_monthly_temp.groupby('month').mean()

        #calculate average min temperature
        min_monthly_temp = mean_spatial_temp.groupby('month_year').min()
        min_monthly_temp['month'] = min_monthly_temp['month_year'].str.slice(start=5, stop=7).astype(int)
        mean_min_temp = min_monthly_temp.groupby('month').mean() 

        print("Calculating relative humidity")

        #relative humidity
        mean_spatial_rh = datasets['rh']['rh'].mean(['latitude', 'longitude'])
        avg_rh = mean_spatial_rh.groupby('time.month').mean(['time'])
        mean_spatial_rh['month_year'] = mean_spatial_rh['time'].dt.strftime('%Y-%m')

        #calculate average max rh
        max_monthly_rh = mean_spatial_rh.groupby('month_year').max()
        max_monthly_rh['month'] = max_monthly_rh['month_year'].str.slice(start=5, stop=7).astype(int)
        mean_max_rh = max_monthly_rh.groupby('month').mean()

        #calculate average min rh
        min_monthly_rh = mean_spatial_rh.groupby('month_year').min()
        min_monthly_rh['month'] = min_monthly_rh['month_year'].str.slice(start=5, stop=7).astype(int)
        mean_min_rh = min_monthly_rh.groupby('month').mean()

        print("Calculating winds")

        #Average winds
        avg_u = datasets['10u']['u10'].groupby('time.month').mean(['latitude', 'longitude'])
        avg_v = datasets['10v']['v10'].groupby('time.month').mean(['latitude', 'longitude'])

        print("Calculating total cloud cover")

        #Get rid of the latitude and longitude dimensions by averaging the data
        avg_tcc_spatial = datasets['tcc']['tcc'].mean(['longitude', 'latitude'])

        #Now average the data of each hour of each month across the 30 years of data. We end up with 288 data points, representing 24 h per month
        month_hour_grouped = avg_tcc_spatial.groupby(avg_tcc_spatial['time.month'] * 100 + avg_tcc_spatial['time.hour'])
        avg_tcc = month_hour_grouped.mean(dim='time')
        
        print("Climatology calculated")

    return avg_prec, avg_temp, mean_max_temp, mean_min_temp, avg_rh, mean_max_rh, mean_min_rh, avg_u, avg_v, avg_tcc


def compute_prediction(lat, lon, db_file='data.db'):
    #Load predictions from database for specified coordinates
    conn = sqlite3.connect(db_file)

    query = f"""SELECT * FROM prediction_data 
            WHERE lat BETWEEN {lat - 1} AND {lat + 1}
            AND lon BETWEEN {lon - 1} AND {lon + 1}
            """

    prediction_data = pd.read_sql_query(query, conn)
    conn.close()

    #convert data to datetime
    prediction_data['time']=pd.to_datetime(prediction_data['time'])
    
    # calculate precipitation
    prediction_data[prediction_data['variable']=='precipitation_prediction']
    proj_avg_prec = prediction_data[prediction_data['variable']=='precipitation_prediction']
    proj_avg_prec = xr.Dataset.from_dataframe(proj_avg_prec.set_index(['lat', 'lon', 'time'])).groupby(
        'time.month').mean(['time', 'lat', 'lon'])['pr']*2592000

    # Temperature
    proj_avg_temp = prediction_data[prediction_data['variable']=='temperature_prediction']
    proj_avg_temp = xr.Dataset.from_dataframe(proj_avg_temp.set_index(['lat', 'lon', 'time'])).groupby(
        'time.month').mean(['time', 'lat', 'lon'])['tas']-273.15

    # Relative humidity
    proj_avg_rh = prediction_data[prediction_data['variable']=='relative_humidity_prediction']
    proj_avg_rh = xr.Dataset.from_dataframe(proj_avg_rh.set_index(['lat', 'lon', 'time'])).groupby(
        'time.month').mean(['time', 'lat', 'lon'])['hurs']

    # Wind speed and direction
    proj_avg_u = prediction_data[prediction_data['variable']=='u_wind_prediction']
    proj_avg_u = xr.Dataset.from_dataframe(proj_avg_u.set_index(['lat', 'lon', 'time'])).groupby(
        'time.month').mean(['time', 'lat', 'lon'])['uas']

    proj_avg_v = prediction_data[prediction_data['variable']=='v_wind_prediction']
    proj_avg_v = xr.Dataset.from_dataframe(proj_avg_v.set_index(['lat', 'lon', 'time'])).groupby(
        'time.month').mean(['time', 'lat', 'lon'])['vas']
    
    return proj_avg_prec, proj_avg_temp, proj_avg_rh, proj_avg_u, proj_avg_v



def get_coordinates(location):
    # get coordinates using Nominatim
    geolocator = Nominatim(user_agent="permaculture-climate")
    try:
        location = geolocator.geocode(location)
        time.sleep(1)
        return location
    except GeocoderTimedOut:
        print("Error: geocode failed on input %s with message TIMEOUT" % (location))
        return None
    except GeocoderUnavailable:
        print("Error: geocode failed on input %s with message SERVICE_UNAVAILABLE" % (location))
        return None
    except:
        print("Error: geocode failed on input %s with message UNKNOWN_ERROR" % (location))
        return None
    
