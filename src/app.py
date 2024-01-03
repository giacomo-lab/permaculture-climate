import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import xarray as xr
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
import time
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import dask
import os
from datetime import datetime
from figures import *
from calculations import *


#TODO: be awesome
# Initialize the Dash app
app = dash.Dash(__name__)
server = app.server

#define app structure
app.layout = html.Div([
    html.Div([
        dcc.Input(id='location-input', type='text', placeholder='Enter location'),
        html.Button('Submit', id='submit-button', n_clicks=0),  # Add a button
    ], style={'display': 'flex', 'justify-content': 'center'}),

    html.Div(id='message', style={'display': 'flex', 'justify-content': 'center', 'margin': '0 auto'}),  # Add a div for messages
    html.Div(id='message', style={'display': 'flex', 'justify-content': 'center', 'margin': '0 auto'}), #dynamic summary
    html.Div([dcc.Graph(id='fig_temp_and_prec', style={'width': '100%', 'max-width': '1000px', 'margin': '0 auto'}),
              dcc.Graph(id='fig_range_temp', style={'width': '100%', 'max-width': '1000px', 'margin': '0 auto'}),
              dcc.Graph(id='fig_range_rh', style={'width': '100%', 'max-width': '1000px', 'margin': '0 auto'})
              dcc.Graph(id='fig_tcc', style={'width': '100%', 'max-width': '1000px', 'margin': '0 auto'})
              dcc.Graph(id='fig_wind', style={'width': '100%', 'max-width': '1000px', 'margin': '0 auto'})
              ], 
              style={'display': 'flex', 'flex-direction': 'column', 'align-items': 'center'}
              )
])
@app.callback(
    [Output('fig_temp_and_prec', 'figure'),
     Output('fig_range_temp', 'figure'),
     Output('fig-range_rh', 'figure'),
     Output('fig_tcc', 'figure'),
     Output('fig_wind', 'figure'),
     Output('message', 'children')],  # Add an output for the message
    [Input('submit-button', 'n_clicks')],  # Listen to the button's n_clicks property
    [State('location-input', 'value')]  # Get the current value of the location-input
)
#TODO: improve default figures looks
#TODO: imprvoe the error handling with more specific messages

#======================
def show_message(location):
    return(f'Fetching data for {location}...')

def get_coordinates(location):
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
    




def generate_default_figure():
    fig = go.Figure()

    fig.add_annotation(
        x=0.5,
        y=0.5,
        text="Input your location",
        showarrow=False,
        font_size=16
    )

    fig.update_layout(
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        template='simple_white'
    )

    return fig


def update_figures(n_clicks, location):
    if n_clicks == 0:
        # If the button hasn't been clicked, return default figures
        return generate_default_figure(), 'Choose a location and click Submit'

    if location is None or location == '':
        # If no location is provided, return default figures
        return generate_default_figure(), 'Choose a location and click Submit'

    location = get_coordinates(location)

    if location is None:
        # Handle the error: return default figures, show an error message, etc.
        return generate_default_figure(),''
    
    lat, lon = location.latitude, location.longitude
    if lat is None or lon is None:
        # Handle the error: return default figures, show an error message, etc.
        return generate_default_figure(), 'Lat or Lon is None'
    else:
        pass

    filename = "src/data/download.grib"

    # List of variables to load
    variables = ['2t','10v','10u','tp','tcc']

    # Dictionary to hold the datasets
    datasets = {}

    show_message(location)
    # Open the GRIB file for each variable using the short name parameter
    #TODO: make this (or similar) messages appear in the dashboard
    print("Opening GRIB file...")
    
    for var in variables:
        ds = xr.open_dataset(filename, engine='cfgrib', 
                             backend_kwargs={'filter_by_keys': {'shortName': var}})
        ds = ds.sel(latitude=slice(lat + 1, lat - 1), longitude=slice(lon - 1, lon + 1))
        datasets[var] = ds

#Calculate climatology and perform units conversion. Parallelized the process using dask.
#TODO: download updated data with RH
#TODO: download prediction data
# Chunk the data using dask
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
    
    
    #Perfom the calcultaions set above and return the results as a pandas dataframe
    avg_prec = avg_prec.compute()
    avg_temp = avg_temp.compute()
    mean_max_temp = mean_max_temp.compute()
    mean_min_temp = mean_min_temp.compute()
    avg_rh = avg_rh.compute()
    mean_max_rh = mean_max_rh.compute()
    mean_min_rh = mean_min_rh.compute()
    avg_u = avg_u.compute()
    avg_v = avg_v.compute()
    avg_tcc = avg_tcc.compute()
    
#TODO separare, fare due funzioni, una prediction und past data,
# poi unaltra funzione per sta roba qua sotto, solo che prende na lista assurda di input variables
    #FIXME: check the inputs of the functions
    message = "figure generated successfully "
    temp_and_prec = generate_fig_temp_and_prec(avg_prec, avg_temp, proj_avg_prec, proj_avg_temp)
    range_temp = generate_fig_range_temp(avg_temp, mean_max_temp, mean_min_temp)
    range_rh = generate_fig_range_rh(avg_rh, mean_max_rh, mean_min_rh)
    cloud_cover = generate_fig_cloud_cover(location, avg_tcc)
    wind_rose = generate_fig_wind_rose(avg_u, avg_v, proj_avg_u, proj_avg_v )
    return temp_and_prec, range_temp, range_rh, cloud_cover, wind_rose, message


if __name__ == '__main__':
    #port = int(os.environ.get("PORT", 10000))
    app.run_server(debug=True)