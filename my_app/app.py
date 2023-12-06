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
from datetime import datetime

# Initialize the Dash app
app = dash.Dash(__name__)

app.layout = html.Div([
    dcc.Input(id='location-input', type='text', placeholder='Enter location'),
    html.Button('Submit', id='submit-button', n_clicks=0),  # Add a button
    html.Div(id='message'),  # Add a div for messages
    dcc.Graph(id='figure-1'),
    dcc.Graph(id='figure-2'),
    #dcc.Graph(id='figure-3')
])
@app.callback(
    [Output('figure-1', 'figure'),
     Output('figure-2', 'figure'),
     Output('message', 'children')],  # Add an output for the message
    [Input('submit-button', 'n_clicks')],  # Listen to the button's n_clicks property
    [State('location-input', 'value')]  # Get the current value of the location-input
)

def update_figures(n_clicks, location):
    if n_clicks == 0:
        # If the button hasn't been clicked, return default figures
        return generate_default_figure(), generate_default_figure(), 'Choose a location and click Submit'

    if location is None or location == '':
        # If no location is provided, return default figures
        return generate_default_figure(), generate_default_figure(), 'Choose a location and click Submit'

    location = get_coordinates(location)
    if location is None:
        # Handle the error: return default figures, show an error message, etc.
        return generate_default_figure(), generate_default_figure(), ''
    

    lat, lon = location.latitude, location.longitude
    if lat is None or lon is None:
        # Handle the error: return default figures, show an error message, etc.
        print("lat or lon is None")
        pass
    else:
        pass

    filename = "my_app/data/download.grib"

    # List of variables to load
    variables = ['2t','10v','10u','tp','tcc']

    # Dictionary to hold the datasets
    datasets = {}

    show_message(location)
    # Open the GRIB file for each variable using the short name parameter
    print("Opening GRIB file...")
    
    for var in variables:
        ds = xr.open_dataset(filename, engine='cfgrib', 
                             backend_kwargs={'filter_by_keys': {'shortName': var}})
        ds = ds.sel(latitude=slice(lat + 1, lat - 1), longitude=slice(lon - 1, lon + 1))
        datasets[var] = ds
    
    import dask

    # Chunk the data
    datasets['tp']['tp'] = datasets['tp']['tp'].chunk({'time': -1})
    datasets['2t']['t2m'] = datasets['2t']['t2m'].chunk({'time': -1})

    with dask.config.set(scheduler='threads'):  # or dask.config.set(scheduler='processes') for multiprocessing
        print("Calculating climatology ==")
        # Calculate the climatology and average over latitude and longitude
        precip_climatology = datasets['tp']['tp'].groupby('time.month').mean(['time', 'latitude', 'longitude', 'step']).compute()*1000
        print("Calculating climatology ====")
        avg_temp = datasets['2t']['t2m'].groupby('time.month').mean(['time', 'latitude', 'longitude']).compute()-273.15
        print("Calculating climatology ======")
        max_temp = datasets['2t']['t2m'].groupby('time.month').max(['time', 'latitude', 'longitude']).compute()-273.15
        print("Calculating climatology ========")
        min_temp = datasets['2t']['t2m'].groupby('time.month').min(['time', 'latitude', 'longitude']).compute()-273.15
        print("Climatology calculated")

    # Convert Dask DataFrames back to pandas DataFrames
    precip_climatology = precip_climatology.compute()
    avg_temp = avg_temp.compute()
    max_temp = max_temp.compute()
    min_temp = min_temp.compute()
    # Generate the figures based on the data
    message = 'Generating figures...'
    figure_1 = generate_figure_1(precip_climatology, avg_temp)
    figure_2 = generate_figure_2(avg_temp, max_temp, min_temp)

    return figure_1, figure_2, message


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