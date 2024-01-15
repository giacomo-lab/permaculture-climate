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
import diskcache
from dash.exceptions import PreventUpdate
from dash.long_callback import DiskcacheLongCallbackManager

#just for mac
#===========
import os
os.environ['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = 'YES'
#===========

# Set up a long callback manager
long_callback_manager = DiskcacheLongCallbackManager(cache=diskcache.Cache("./cache"))

app = dash.Dash(__name__, long_callback_manager=long_callback_manager)
server = app.server


# Define the initial style of the button
button_style = {'backgroundColor': 'rgb(25, 25, 25)', 'color': 'white', 'borderRadius': '5px', 'fontSize': '22px'}

#define app structure
app.layout = html.Div([
    html.Div([
        dcc.Input(id='location-input', type='text', placeholder='Enter a location', style={'font-size' : '22px'}),
        html.Button('Submit', id='submit-button', n_clicks=0, style=button_style),  # Use the variable here
    ], style={'display': 'flex', 'justify-content': 'center', 'margin-top': '50px' }),

    html.Div(id='message', style={'display': 'flex', 'justify-content': 'center', 'margin': '10px auto', 'text-align': 'center'}),  # Add a div for messages
    html.Div([dcc.Graph(id='fig_temp_and_prec', style={'width': '100%', 'max-width': '1000px', 'margin': '0 auto'}),
              dcc.Graph(id='fig_range_temp', style={'width': '100%', 'max-width': '1000px', 'margin': '0 auto'}),
              dcc.Graph(id='fig_range_rh', style={'width': '100%', 'max-width': '1000px', 'margin': '0 auto'}),
              dcc.Graph(id='fig_tcc', style={'width': '100%', 'max-width': '1000px', 'margin': '0 auto'}),
              dcc.Graph(id='fig_wind', style={'width': '100%', 'max-width': '1000px', 'margin': '0 auto'})
              ], 
              style={'display': 'flex', 'flex-direction': 'column', 'align-items': 'center'}
              )
])


@app.long_callback(
    [Output('fig_temp_and_prec', 'figure'),
     Output('fig_range_temp', 'figure'),
     Output('fig_range_rh', 'figure'),
     Output('fig_tcc', 'figure'),
     Output('fig_wind', 'figure'),
     Output('message', 'children'),
     Output('submit-button', 'disabled')],
    [Input('submit-button', 'n_clicks')],
    [State('location-input', 'value')],
    running=[
        (Output('submit-button', 'disabled'), True, False),
        (Output('submit-button', 'style'), {**button_style, 'backgroundColor': 'grey'}, button_style)
    ]
)

#TODO: imprvoe the error handling with more specific messages

#======================

def update_figures(n_clicks, location):
    if n_clicks == 0:
        # If the button hasn't been clicked, return default figures
        return [generate_default_figure(), generate_default_figure(), generate_default_figure(), 
            generate_default_figure(), generate_default_figure(), 
            '', 
            False
            ]

    if location is None or location == '':
        # If no location is provided, return default figures
        return [generate_default_figure(), generate_default_figure(), generate_default_figure(), 
                generate_default_figure(), generate_default_figure(), 
                'Your location is invalid. Choose a new location and click Submit', 
                False
                ]

    coords = get_coordinates(location)
    lat, lon = coords.latitude, coords.longitude
    
    if lat is None or lon is None:
        # Handle the error: return default figures, show an error message, etc.
        return [generate_default_figure(), generate_default_figure(), generate_default_figure(),
                generate_default_figure(), generate_default_figure(), 
                'Your location is invalid. Choose a new location and click Submit',
                False
                 ]
 

#Calculate climatology and perform units conversion. Parallelized the process using dask.
    print("Calculating climatology...")

    lat, lon = coords.latitude, coords.longitude

    avg_prec, avg_temp, mean_max_temp, mean_min_temp, avg_rh, mean_max_rh, mean_min_rh, avg_u, avg_v, avg_tcc = compute_climatology(lat, lon, db_file='data.db')
    # Calculate prediction
    proj_avg_prec, proj_avg_temp, proj_avg_rh, proj_avg_u, proj_avg_v = compute_prediction(lat, lon, db_file='data.db')
    # proj_avg_prec, proj_avg_temp, proj_avg_u, proj_avg_v = compute_prediction(lat, lon, db_file='data.db')
    #TODO separare, fare due funzioni, una prediction und past data,
    # poi unaltra funzione per sta roba qua sotto, solo che prende na lista assurda di input variables
    
    message = "figure generated successfully"
    print('generating figures')
    fig_temp_and_prec = generate_fig_temp_and_prec(avg_prec, avg_temp, proj_avg_prec, proj_avg_temp)
    print('f1')
    fig_range_temp = generate_fig_range_temp(avg_temp, mean_max_temp, mean_min_temp)
    print('f2')
    fig_range_rh = generate_fig_range_rh(avg_rh, mean_max_rh, mean_min_rh, proj_avg_rh)
    print('f3')
    fig_cloud_cover = generate_fig_cloud_cover(coords, avg_tcc)
    print('f4')
    fig_wind_rose = generate_fig_wind_rose(avg_u, avg_v, proj_avg_u, proj_avg_v )
    print('done')
    return fig_temp_and_prec, fig_range_temp, fig_range_rh, fig_cloud_cover, fig_wind_rose, message, False



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
    



if __name__ == '__main__':
    app.run_server(debug=True)