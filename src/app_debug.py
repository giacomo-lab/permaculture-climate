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
#from figures import *
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
    html.Div([dcc.Graph(id='fig_temp_and_prec', style={'width': '100%', 'max-width': '1000px', 'margin': '0 auto'})
              ], 
              style={'display': 'flex', 'flex-direction': 'column', 'align-items': 'center'}
              )
])
@app.callback(
    [Output('fig_temp_and_prec', 'figure')],
    [Input('submit-button', 'n_clicks')],  # Listen to the button's n_clicks property
    [State('location-input', 'value')]  # Get the current value of the location-input
)
#TODO: improve default figures looks
#TODO: imprvoe the error handling with more specific messages

#======================

def update_figures(n_clicks, location):
    if n_clicks == 0:
        # If the button hasn't been clicked, return default figures
        return [generate_default_figure()]

    if location is None or location == '':
        # If no location is provided, return default figures
        return [generate_default_figure()]

    coords = get_coordinates(location)
    lat, lon = coords.latitude, coords.longitude
    
    if lat is None or lon is None:
        # Handle the error: return default figures, show an error message, etc.
        return [generate_default_figure()]
    else:
        pass

    lat, lon = coords.latitude, coords.longitude

    avg_prec, avg_temp, mean_max_temp, mean_min_temp, avg_rh, mean_max_rh, mean_min_rh, avg_u, avg_v, avg_tcc = compute_climatology(lat, lon, db_file='data.db')

    # Calculate prediction
    proj_avg_prec, proj_avg_temp, proj_avg_rh, proj_avg_u, proj_avg_v = compute_prediction(lat, lon, db_file='data.db')
    
    print("prediction calculated, now generating figures")

#TODO separare, fare due funzioni, una prediction und past data,
# poi unaltra funzione per sta roba qua sotto, solo che prende na lista assurda di input variables
    #FIXME: check the inputs of the functions
    fig_temp_and_prec = generate_fig_temp_and_prec(avg_prec, avg_temp, proj_avg_prec, proj_avg_temp)
    return [fig_temp_and_prec]

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

def generate_fig_temp_and_prec(avg_prec, avg_temp, proj_avg_prec, proj_avg_temp):

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    # Add a bar chart for precipitation and forcasted precipitation to the secondary y-axis
    bar_prec = go.Bar(x=avg_prec.month, 
                      y=avg_prec, 
                      name='Precipitation', 
                      opacity=0.75, 
                      marker_color = 'blue', 
                      hovertemplate=('%{x}: %{y:.0f} mm <extra></extra>')
                      )

    bar_prec_forecast = go.Bar(x=proj_avg_prec.month, 
                                y=proj_avg_prec, 
                                name='Forcasted precipitation', 
                                marker_color = 'lightblue',
                                hovertemplate=('%{x}: %{y:.0f} mm <extra></extra>')
                                )

    fig.add_trace(bar_prec)
    fig.add_trace(bar_prec_forecast)

    # Add a line chart for temperature to the primary y-axis
    fig.add_trace(go.Scatter(x=avg_temp.month, 
                             y=avg_temp, 
                             mode='lines', 
                             name='Temperature', 
                             opacity=0.85,
                             line=dict(color='red', width=3),  # Make the line thicker
                             hovertemplate=('%{x}: %{y:.0f} °C <extra></extra>')
                             ),
                    secondary_y=True
                    )

    # Add forecasted temperature
    fig.add_trace(go.Scatter(x=proj_avg_temp.month, 
                             y=proj_avg_temp, 
                             mode='lines', 
                             opacity=0.85,
                             name='Forcasted temperature', 
                             line=dict(color='orange', width=3),  # Make the line thicker
                             hovertemplate=('%{x}: %{y:.0f} °C <extra></extra>')
                             ),   
                secondary_y=True,
                )
    
    # Set the layout to have two y-axes
    fig.update_layout(title='Temperature and precipitation (past and forcasted)',
                      yaxis=dict(title='Precipitation (mm)', tickfont=dict(size=14)),  # Make the tick labels bigger
                      yaxis2=dict(title='Temperature (°C)', overlaying='y', side='right', tickfont=dict(size=14)),  # Make the tick labels bigger
                      xaxis=dict(tickmode='array',
                                 tickvals=avg_temp.month,
                                 ticktext=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
                                 tickangle=-45,
                                 tickfont=dict(size=14)  # Make the tick labels bigger
                                 ),
                        template='simple_white',
                        width=1075,  # Set the figure width
                        height=600,  # Set the figure height
                        margin=dict(b=200) # Adjust the bottom margin to create more space below the figure
                        )

    # Add a text on the bottom of the figure
    fig.add_annotation(text=f"""This figure show the average monthly temperature and precipitation for the past 30 years and the 
                       <br>forcasted values for the next 30 years. 
                       <br>Blue and lightblue bars represent precipitation, red and orange lines represents temperature.
                       <br>Hover over the bars and lines to see the values. Click on the legend to hide/show the data.""",
                        xref='paper', yref='paper',
                        x=0, y=-0.5,  # Adjust this value to position the text below the x-axis legend
                        showarrow=False,
                        align='left',  # Set align to 'left'
                        font=dict(size=12, color='black'),
                        )
    return fig

if __name__ == '__main__':
    #port = int(os.environ.get("PORT", 10000))
    app.run_server(debug=True)