import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from dash.dependencies import Input, Output, State
import pandas as pd
import xarray as xr
import cdsapi
import requests
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
import time
from datetime import datetime

# Initialize the Dash app
app = dash.Dash(__name__)

# Define the layout of the app
app.layout = html.Div([
    dcc.Input(id='location-input', type='text', placeholder='Enter location'),
    html.Button('Submit', id='submit-button', n_clicks=0),  # Add a button
    dcc.Graph(id='figure-1'),
    dcc.Graph(id='figure-2'),
    #dcc.Graph(id='figure-3')
])

@app.callback(
    [Output('figure-1', 'figure'),
     Output('figure-2', 'figure'),
     #Output('figure-3', 'figure')
      ],
    [Input('submit-button', 'n_clicks')],  # Listen to the button's n_clicks property
    [State('location-input', 'value')]  # Get the current value of the location-input
)
def update_figures(n_clicks, location):
    if n_clicks == 0:
        # If the button hasn't been clicked, return default figures
        return generate_default_figure(), generate_default_figure()

    if location is None or location == '':
        # If no location is provided, return default figures
        return generate_default_figure(), generate_default_figure()

    location = get_coordinates(location)
    if location is None:
        # Handle the error: return default figures, show an error message, etc.
        return generate_default_figure(), generate_default_figure()

    lat, lon = location.latitude, location.longitude
    if lat is None or lon is None:
        # Handle the error: return default figures, show an error message, etc.
        print("lat or lon is None")
        pass
    else:
        # Perform the API request and generate the figures
        pass

    # select the years you want to download:
    start_year = 1992
    end_year = 2022
    year_range = [i for i in range(start_year, end_year + 1)]

    #API request for era5 data
    c = cdsapi.Client()
    try:
        data = c.retrieve("reanalysis-era5-single-levels-monthly-means",
        {"format": "grib",
         "product_type": "monthly_averaged_reanalysis_by_hour_of_day",
         "variable": ['10m_u_component_of_wind', '10m_v_component_of_wind', 
                    '2m_temperature',
                    'total_cloud_cover', 
                    'total_precipitation',
                    ],
        "area": [location.latitude + 1,    
                 location.longitude - 1, 
                 location.latitude - 1, 
                 location.longitude + 1],  # North, West, South, East. 
        "year": year_range,
        "month": ['01', '02', '03',
               '04', '05', '06',
               '07', '08', '09',
               '10', '11', '12'],
        "time": ["00:00","01:00","02:00","03:00","04:00","05:00",
                 "06:00","07:00","08:00","09:00","10:00","11:00",
                 "12:00", "13:00","14:00","15:00","16:00","17:00",
                 "18:00","19:00","20:00","21:00","22:00","23:00"]
        })

        # Get the location of the file to download
        url = data.location

        # Download the file
        response = requests.get(url)

        # Check if the request was successful
        response.raise_for_status()

    except requests.exceptions.HTTPError as errh:
        print ("HTTP Error:",errh)
    except requests.exceptions.ConnectionError as errc:
        print ("Error Connecting:",errc)
    except requests.exceptions.Timeout as errt:
        print ("Timeout Error:",errt)
    except requests.exceptions.RequestException as err:
        print ("Something went wrong with the request:",err)

    else:
        # If the request was successful, write the file
        filename = 'download.grib'
        with open(filename, 'wb') as f:
            f.write(response.content)

        # Open the GRIB file for each variable
    variables = ['Total cloud cover', '10 metre V wind component', 
                 '2 metre temperature', 'Total precipitation', '10 metre U wind component']
    datasets = {}
    for var in variables:
        ds = xr.open_dataset(filename, engine='cfgrib', backend_kwargs={'filter_by_keys': {'parameterName': var}})
        datasets[var] = ds

    # Calculate the climatology and average over latitude and longitude
    precip_climatology = datasets['Total precipitation']['tp'].groupby('time.month').mean(['time', 'latitude', 'longitude', 'step'])*1000
    avg_temp = datasets['2 metre temperature']['t2m'].groupby('time.month').mean(['time', 'latitude', 'longitude'])-273.15
    max_temp = datasets['2 metre temperature']['t2m'].groupby('time.month').max(['time', 'latitude', 'longitude'])-273.15
    min_temp = datasets['2 metre temperature']['t2m'].groupby('time.month').min(['time', 'latitude', 'longitude'])-273.15

    # Generate the figures based on the data
    figure_1 = generate_figure_1(precip_climatology, avg_temp)
    figure_2 = generate_figure_2(avg_temp, max_temp, min_temp)
    #figure_3 = generate_figure_3(filename)

    return figure_1, figure_2


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
    


def generate_figure_1(precip_climatology, avg_temp):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(x=precip_climatology.month, y=precip_climatology, name='Precipitation', opacity=0.5),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(x=avg_temp.month, y=avg_temp, mode='lines', name='Temperature'),
        secondary_y=True,
    )
    fig.update_layout(
        title = 'Average Temperature and Precipitation',
        yaxis=dict(title='Precipitation (mm)'),
        yaxis2=dict(title='Temperature (°C)', overlaying='y', side='right'),
        xaxis=dict(
            title='Month',
            tickmode='array',
            tickvals=avg_temp.month,
            ticktext=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
            tickangle=-45
        ),
        template='simple_white'
    )
    return fig


def generate_figure_2(avg_temp, max_temp, min_temp):
    # Create a DataFrame from the DataArrays
    df = pd.DataFrame({
        'month': avg_temp.month.values,
        'avg_temp': avg_temp.values,
        'max_temp': max_temp.values,
        'min_temp': min_temp.values
    })

    # Create a line chart for average temperature
    fig = px.line(df, x='month', y='avg_temp', title='Min and max temperature')

    # Add a line chart for max temperature
    fig.add_trace(go.Scatter(x=df['month'], y=df['max_temp'], mode='lines', name='Max Temperature', line_color='red'))

    # Add a line chart for min temperature
    fig.add_trace(go.Scatter(x=df['month'], y=df['min_temp'], mode='lines', name='Min Temperature', line_color='red', fill='tonexty'))

    # Add a line chart for min temperature
    fig.add_hline(y=0, opacity=1, line_width=2, line_dash='dash', line_color='blue', annotation_text='freezing', annotation_position='top')

    # Set the layout
    fig.update_layout(
        yaxis=dict(title='Temperature (°C)'),
        xaxis=dict(
            title='Month',
            tickmode='array',
            tickvals=df['month'],
            ticktext=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
            tickangle=-45
        ),
        template='simple_white'
    )

    return fig

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

if __name__ == '__main__':
    app.run_server(debug=True)