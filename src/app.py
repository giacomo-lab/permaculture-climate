import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
import time
import os
import diskcache
from dash.long_callback import DiskcacheLongCallbackManager

from figures import *
from calculations import *
from text_messages import *

#TODO: be awesome
# Initialize the Dash app
import os
os.environ['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = 'YES'
#===========

# Set up a long callback manager
long_callback_manager = DiskcacheLongCallbackManager(cache=diskcache.Cache("./cache"))

app = dash.Dash(__name__, long_callback_manager=long_callback_manager)
server = app.server

# Define the initial style of the button
button_style = {'backgroundColor': 'rgb(25, 25, 25)', 'color': 'white', 'borderRadius': '5px', 'fontSize': '22px'}
button_style_running = {**button_style, 'backgroundColor': 'grey'}

#define app structure
margin_left = '10vw'
margin_right = '3vw'
style_comment = {'margin-left': margin_left,'margin-right': margin_right, 'max-width': '30vw', 'fontsize': '16px'}
style_figure = {'width': '100%', 'max-width': '1000px', 'margin': '0 auto'}

# Input field and button
app.layout = html.Div([
    html.Div([
        dcc.Input(id='location-input', type='text', placeholder='Enter a location', style={'font-size' : '22px'}),
        html.Button('Submit', id='submit-button', n_clicks=0, style=button_style),
    ], style={'display': 'flex', 'justify-content': 'center', 'margin-top': '50px' }),
    
    # Message like please input location
    html.Div(id='message', style={'display': 'flex', 'justify-content': 'center', 'margin': '10px auto', 'text-align': 'center', 'fontsize':'18px'}),
    
    # Dynamic text for each location
    html.Div(id='dynamic_text', style={'text-align': 'center', 'font-size': '18px', 'margin-top': '10px', 
                                       'margin-left': '14vw','margin-right': '14vw'}),
    #center line
    html.Div(style={'width': '33%', 'margin-bottom':'10px', 'margin-top': '10px', 'margin-right' : 'auto', 'margin-left' : 'auto', 'border-top': '1px solid black'}),
    
    html.Div([
        html.Div(id='message_temp_and_prec', style=style_comment),
        dcc.Graph(id='fig_temp_and_prec', style=style_figure),
    ], style={'display': 'flex', 'align-items': 'center'}),

    html.Div([
        html.Div(id='message_range_temp', style=style_comment),
        dcc.Graph(id='fig_range_temp', style=style_figure),
    ], style={'display': 'flex', 'align-items': 'center'}),

    html.Div([
        html.Div(id='message_range_rh', style=style_comment),
        dcc.Graph(id='fig_range_rh', style=style_figure),
    ], style={'display': 'flex', 'align-items': 'center'}),

    html.Div([
        html.Div(id='message_tcc', style=style_comment),
        dcc.Graph(id='fig_tcc', style=style_figure),
    ], style={'display': 'flex', 'align-items': 'center'}),

    html.Div([
        html.Div(id='message_wind', style=style_comment),
        dcc.Graph(id='fig_wind', style=style_figure),
    ], style={'display': 'flex', 'align-items': 'center'}),
])

@app.long_callback(
    [Output('dynamic_text', 'children'),
     Output('fig_temp_and_prec', 'figure'),
     Output('fig_range_temp', 'figure'),
     Output('fig_range_rh', 'figure'),
     Output('fig_tcc', 'figure'),
     Output('fig_wind', 'figure'),
     Output('message_temp_and_prec', 'children'),
     Output('message_range_temp', 'children'),
     Output('message_range_rh', 'children'),
     Output('message_tcc', 'children'),
     Output('message_wind', 'children'),
     Output('message', 'children'),
     Output('submit-button', 'disabled'),
     Output('submit-button', 'style')],
    [Input('submit-button', 'n_clicks')],
    [State('location-input', 'value')],
    running=[
        (Output('submit-button', 'disabled'), True, False),
        (Output('submit-button', 'style'), button_style_running, button_style)
    ]
)

#======================
def update_figures(n_clicks, location):
    if n_clicks == 0:
        # If the button hasn't been clicked, return default figures
        message = "Enter a location like 'Berlin, Germany' and click submit"
        return [message, generate_default_figure(), generate_default_figure(), generate_default_figure(), 
            generate_default_figure(), generate_default_figure(), 
            " ", " ", " ", " ", " ", " ", 
            False, button_style
            ]

    if location is None or location == '':
        # If no location is provided, return default figures
        return ['', generate_default_figure(), generate_default_figure(), generate_default_figure(), 
                generate_default_figure(), generate_default_figure(),
                " ", " ", " ", " ", " ",
                'Your location is invalid. Choose a new location and click Submit', 
                False, button_style
                ]

    coords = get_coordinates(location)
    lat, lon = coords.latitude, coords.longitude
    
    if lat is None or lon is None:
        # Handle the error: return default figures, show an error message, etc.
        return ['', generate_default_figure(), generate_default_figure(), generate_default_figure(),
                generate_default_figure(), generate_default_figure(), 
                " ", " ", " ", " ", " ",
                'Your location is invalid. Choose a new location and click Submit',
                False, button_style
                 ]
 

#Calculate climatology and perform units conversion. Parallelized the process using dask.
    print("Calculating climatology...")

    lat, lon = coords.latitude, coords.longitude

    avg_prec, avg_temp, mean_max_temp, mean_min_temp, avg_rh, mean_max_rh, mean_min_rh, avg_u, avg_v, avg_tcc = compute_climatology(lat, lon, db_file='data.db')
    # Calculate prediction
    proj_avg_prec, proj_avg_temp, proj_avg_rh, proj_avg_u, proj_avg_v = compute_prediction(lat, lon, db_file='data.db')
    #message 
    
    message = ' '
    # load descriptions of each figure and dynamic introduction text
    text_temp_and_prec = comm_temp_and_prec()
    text_range_temp = comm_range_temp()
    text_range_rh = comm_range_rh()
    text_cloud_cover = comm_cloud_cover() 
    text_wind_rose = comm_wind_rose()
    
    dynamic_text = generate_dynamic_text(coords, avg_temp, avg_prec)
    
    # generate figures
    print('generating figures')

    fig_temp_and_prec = generate_fig_temp_and_prec(avg_prec, avg_temp, proj_avg_prec, proj_avg_temp)
    
    fig_range_temp = generate_fig_range_temp(avg_temp, mean_max_temp, mean_min_temp)
    
    fig_range_rh = generate_fig_range_rh(avg_rh, mean_max_rh, mean_min_rh, proj_avg_rh)
    
    fig_cloud_cover = generate_fig_cloud_cover(coords, avg_tcc)
    
    fig_wind_rose = generate_fig_wind_rose(avg_u, avg_v, proj_avg_u, proj_avg_v )
    
    return dynamic_text, fig_temp_and_prec, fig_range_temp, fig_range_rh, fig_cloud_cover, fig_wind_rose, \
       text_temp_and_prec, text_range_temp, text_range_rh, text_cloud_cover, text_wind_rose, message, \
         False, button_style



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