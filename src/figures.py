import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime
import timezonefinder
from astral.sun import sun
from astral.location import LocationInfo
from calculations import *



def generate_default_figure():
    #generate a placeholder figure 
    fig = go.Figure()

    fig.add_annotation(
    x=4,
    y=11,
    text="""PLACEHOLDER GRAPH <br> please insert location""",
    showarrow=False,
    font_size=24,
    textangle=-45,  
    opacity=0.5,  
    bordercolor="black",  
    borderwidth=2, 
    borderpad=4 
)
    fig.update_layout(
        xaxis=dict(range=[0, 10], showgrid=False, showticklabels=False),  
        yaxis=dict(range=[0, 20], showgrid=False, showticklabels=False),  
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
                             line=dict(color='red', width=3),  
                             hovertemplate=('%{x}: %{y:.0f} °C <extra></extra>')
                             ),
                    secondary_y=True
                    )

    # Add forecasted temperature
    fig.add_trace(go.Scatter(x=proj_avg_temp.month, 
                             y=proj_avg_temp, 
                             mode='lines', 
                             opacity=1,                         
                             line_dash='dash',
                             line_width=3,
                             name='Forcasted temperature', 
                             line=dict(color='red', width=3), 
                             hovertemplate=('%{x}: %{y:.0f} °C <extra></extra>')
                             ),   
                secondary_y=True,
                )


    # Set the layout to have two y-axes
    fig.update_layout(yaxis=dict(title='Precipitation (mm)', tickfont=dict(size=14)),  
                      yaxis2=dict(title='Temperature (°C)', overlaying='y', side='right', tickfont=dict(size=14)),  
                      xaxis=dict(tickmode='array',
                                 tickvals=avg_temp.month,
                                 ticktext=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
                                 tickangle=-45,
                                 tickfont=dict(size=14) 
                                 ),
                        template='simple_white',
                        width=1075, 
                        height=600,  
                        )    
    return fig


def generate_fig_range_temp(avg_temp, mean_max_temp, mean_min_temp):
    df = pd.DataFrame({'month': avg_temp.month.values,
                       'avg_temp': avg_temp.values,
                       'max_temp': mean_max_temp.values,
                       'min_temp': mean_min_temp.values
                       })
    # Create a line chart for average temperature
    fig = go.Figure()

    fig.add_trace(go.Scatter(x=df['month'], y=df['avg_temp'],
                             mode='lines', 
                             name='Average temperature', 
                             line_color='orange',
                             opacity=0.9,
                             )
                 )

    # Add a line chart for max temperature
    fig.add_trace(go.Scatter(x=df['month'], y=df['max_temp'], 
                             mode='lines',
                             name='Average range per month', 
                             line_color='red',
                             opacity=0.85,
                             )
                 )

    # Add a line chart for min temperature
    fig.add_trace(go.Scatter(x=df['month'], y=df['min_temp'], 
                             mode='lines', 
                             name='Min temperature', 
                             line_color='red', 
                             fill='tonexty', 
                             fillcolor='rgba(255, 0, 0, 0.1)', 
                             showlegend=False
                             )
                 )

    # Add a line chart for min temperature
    if min(mean_min_temp.values) <= 0.9:
        fig.add_hline(y=0, 
                      opacity=0.85, 
                      line_width=2, 
                      line_dash='dash', 
                      line_color='blue',
                      annotation_text='freezing', 
                      annotation_position='top'
                      )
    
    # Set the layout
    padding = (max(df['max_temp']) - min(df['min_temp']))/5
    if min(mean_min_temp.values) > 0.5:
        fig.update_yaxes(range=[0, max(df['max_temp'] + padding)])
    else:
        fig.update_yaxes(range=[min(df['min_temp']) - padding, max(df['max_temp']) + padding])

    fig.update_layout(yaxis=dict(title='Temperature (°C)', tickfont=dict(size=14)),
                      xaxis=dict(
                          tickmode='array',
                          tickvals=df['month'],
                          ticktext=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
                          tickangle=-45,
                          tickfont=dict(size=14),
                          ),
                      width=1075,
                      height=600,
                      template='simple_white',
                      )

    # Adjust the bottom margin to create more space below the figure
    fig.update_layout(margin=dict(b=200))

    # Show the figure
    fig.update_traces(hovertemplate='%{x}: %{y:.0f} °C <extra></extra>')

    
    return fig


#DONE: add image rh range
def generate_fig_range_rh(avg_rh, mean_max_rh, mean_min_rh, proj_avg_hum):
    df = pd.DataFrame({
        'month': avg_rh.month.values,
        'avg_rh': avg_rh.values,
        'max_rh': mean_max_rh.values,
        'min_rh': mean_min_rh.values,
        'proj': proj_avg_hum.values
    })

    # Create a line chart for average rel humidity
    fig = go.Figure()

    fig.add_trace(go.Scatter(x=df['month'], y=df['avg_rh'], 
                             mode='lines', 
                             name='Average relative humidity', 
                             line_color='rgb(0, 0, 200)')
                             )



    # Add a line chart for projected rel humidity
    fig.add_trace(go.Scatter(x=df['month'], y=df['proj'], 
                             mode='lines', 
                             name='Forecasted realtive humidity', 
                             line_dash='dash',
                             line_width=2.7,
                             line_color='rgb(0, 0, 200)', 
                             showlegend=True
                             )
                             )

    # Add a line chart for max rel humidity
    fig.add_trace(go.Scatter(x=df['month'], y=df['max_rh'], 
                             mode='lines',
                             name='Average range per month', 
                             line_color='rgb(5, 150, 250)')
                             )

    # Add a line chart for min rel humidity
    fig.add_trace(go.Scatter(x=df['month'], y=df['min_rh'], 
                             mode='lines', 
                             name='Min realtive humidity', 
                             line_color='rgb(5, 150, 250)', 
                             fill='tonexty', 
                             fillcolor = 'rgba(5, 150, 250, 0.1)', 
                             showlegend=False
                             )
                             )

    # Set the layout
    padding = (max(df['max_rh']) - min(df['min_rh']))/5
    fig.update_yaxes(range=[min(df['min_rh']) - padding, max(df['max_rh']) + padding])

    # Set the layout
    fig.update_layout(yaxis=dict(title='Relative humidity (%)',
                                 tickfont=dict(size=14)
                                 ),
                      yaxis_title_font=dict(size=16), 
                      xaxis=dict(tickmode='array',
                                 tickvals=df['month'],
                                 ticktext=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
                                 tickangle=-45,
                                 tickfont=dict(size=14),
                                 ),
                      width=1075,
                      height=600,
                      template='simple_white',
                          legend=dict(
                       traceorder='normal', 
                     ),
                      )

    # Show the figure
    fig.update_traces(hovertemplate='%{x}: %{y:.0f} % <extra></extra>')


    return fig


def generate_fig_cloud_cover(coords, avg_tcc):
   #find the timezone of the location
    tf = timezonefinder.TimezoneFinder()
    timezone_str = tf.certain_timezone_at(lat=coords.latitude, lng=coords.longitude)

    #define location infos for the astral package only using coordinates
    location_info = LocationInfo(None, None, timezone_str, coords.latitude, coords.longitude)

    #define two empty lists for sunrise and sunset times
    sunrise_times, sunset_times = [], []

    # append sunrise and sunset times for the 15th of every month of 2022. Automatically adjusted for Daylight Saving Time (DST)
    for month in range(1, 13):
        date = datetime(2022, month, 15)

        s = sun(location_info.observer, date=date, tzinfo=timezone_str)
        sunrise_times.append(s['sunrise'].strftime('%H:%M'))
        sunset_times.append(s['sunset'].strftime('%H:%M')) 
        
    # Create the graph with cloud cover values plus sunrise and sunset times

    # Reshape the data to match the format expected by Plotly
    # As we want to calculate an áverage for hours of each month over the years, 
    # doing *100 creates a unique label for each month+hour combination
    data_reshaped = avg_tcc.values.reshape((12, 24)).T*100  # Use -1 to automatically infer the size

    fig = go.Figure()

    fig.add_trace(go.Heatmap(z=data_reshaped,
                             x=list(range(12)),
                             y=list(range(24)),
                             xgap = 5,
                             colorscale='gray_r',
                             colorbar=dict(
                             title="Cloud Cover [%]",
                             y=0.4,  
                             len=0.75  
                             ),
                             hovertemplate='Month: %{x}<br>Time:%{y}:00<br>Cloud Cover: %{z:.0f}%<extra></extra>',  # Custom hover text
                            )
                  )

    # Set x-axis tickvals and ticktext for each month
    fig.update_xaxes(tickvals=list(range(12)),
                     ticktext=[f"{month_name}" for month_name in ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]],
                     tickmode='array',  # Use 'array' for custom tickvals and ticktext
                     tickangle=-45,  
                     )

    # Set x-axis tickvals and ticktext for each day of the month

    # Add a line for sunset times
    fig.add_trace(go.Scatter(x=list(range(12)),
                             y=[float('{:.2f}'.format(int(h) + int(m) / 60)) for h, m in [time.split(':') for time in sunset_times]],
                             mode='lines',
                             line=dict(color='rgb(150,0,255)', width=2),
                             name='Sunset',
                             hovertemplate='Month: %{x}<br>Sunset at: %{text}<extra></extra>',  # Custom hover text 
                             text=sunset_times
                             )
                  )

    # Add a line for sunrise times
    fig.add_trace(go.Scatter(x=list(range(12)),
                             y=[float('{:.2f}'.format(int(h) + int(m) / 60)) for h, m in [time.split(':') for time in sunrise_times]],
                             mode='lines',
                             line=dict(color='rgb(255,65,0)', width=2),
                             name='Sunrise',
                             hovertemplate='Month: %{x}<br>Sunrise at: %{text}<extra></extra>',  # Custom hover text
                             text=sunrise_times
                             )
                  )

    # Update layout to show custom line in legend and set title and x axis
    fig.update_layout(yaxis_title='Hour of the day',
                      showlegend=True,
                      legend_font=dict(size=14),  
                      yaxis_title_font=dict(size=16), 
                      legend=dict(x=1.02, y=1),
                      yaxis=dict(dtick=2,
                                 tickfont=dict(size=14)
                                 ), # y axis ticks every 2 hours
                      xaxis=dict(tickfont=dict(size=14)),
                      width=1075,
                      height=600,
                      )

    return fig



def generate_fig_wind_rose(avg_u, avg_v, proj_avg_u, proj_avg_v):
    # Calculate wind speeds for past data
    wind_speed = np.sqrt(avg_u**2 + avg_v**2)
    
    #convert to km/h
    wind_speed = wind_speed*3.6
    
    # Calculate wind direction (see: https://confluence.ecmwf.int/pages/viewpage.action?pageId=133262398)
    wind_direction = np.mod(180 + np.arctan2(avg_u, avg_v) * (180 / np.pi), 360)

    #prepare the data for the wind rose
    df = pd.DataFrame({'speed': wind_speed.values, 'direction': wind_direction.values})
    bins_dir = np.linspace(0, 360, 9)
    labels_dir = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    labels_speed = ["0-5", "5-10", "10-15", "15-20", "20-25", "25+"]
    bins_speed = np.concatenate([np.arange(0, 26, 5), np.array([np.inf])])
    df['direction'] = pd.cut(df['direction'], bins=bins_dir, labels=labels_dir)
    df['speed'] = pd.cut(df['speed'], bins=bins_speed, labels=labels_speed)

    # Calculate frequencies
    frequency_df = df.groupby(['direction', 'speed'], observed=False).size().reset_index(name='frequency')

    # Calculate total frequency
    total_frequency = frequency_df['frequency'].sum()

    # Convert frequency to proportion
    frequency_df['frequency'] = frequency_df['frequency'] / total_frequency
    
    # Calculate wind speeds for climate forcasted data
    wind_speed_proj = np.sqrt(proj_avg_u**2 + proj_avg_v**2)
    #convert to km/h
    wind_speed_proj = wind_speed_proj*3.6

    # Calculate wind direction (see: https://confluence.ecmwf.int/pages/viewpage.action?pageId=133262398)
    wind_direction_proj = np.mod(180 + np.arctan2(proj_avg_u, proj_avg_v) * (180 / np.pi), 360)

    #prepare the data for the wind rose
    df_proj = pd.DataFrame({'speed': wind_speed_proj, 'direction': wind_direction_proj})

    bins_dir = np.linspace(0, 360, 9)
    labels_dir = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    labels_speed = ["0-5", "5-10", "10-15", "15-20", "20-25", "25+"]
    bins_speed = np.concatenate([np.arange(0, 26, 5), np.array([np.inf])])
    df_proj['direction'] = pd.cut(df_proj['direction'], bins=bins_dir, labels=labels_dir)
    df_proj['speed'] = pd.cut(df_proj['speed'], bins=bins_speed, labels=labels_speed)

    # Calculate frequencies
    frequency_df_pred = df_proj.groupby(['direction', 'speed'], observed=False).size().reset_index(name='frequency')

    # Calculate total frequency
    total_frequency_pred = frequency_df_pred['frequency'].sum()

    # Convert frequency to proportion
    frequency_df_pred['frequency'] = frequency_df_pred['frequency'] / total_frequency_pred 
    
    template = 'simple_white'
    # Convert the 'speed' column to string type
    frequency_df['speed'] = frequency_df['speed'].astype(str)
    frequency_df_pred['speed'] = frequency_df_pred['speed'].astype(str)

    # Get the unique 'speed' values from both dataframes
    speed_values = pd.concat([frequency_df['speed'], frequency_df_pred['speed']]).unique()

    # Create a color scale based on the unique 'speed' values
    color_scale = {speed: color for speed, color in zip(speed_values, px.colors.sequential.Viridis_r)}

    # Create a subplot with 1 row and 2 columns
    fig = make_subplots(rows=1, cols=2, subplot_titles=['Winds (past) <br> <br> ', 'Winds (forcasted) <br> <br> '], specs=[[{'type': 'polar'}, {'type': 'polar'}]])

    # Create the wind rose chart
    fig1 = px.bar_polar(frequency_df, 
                       r='frequency', 
                       theta='direction', 
                       color='speed', 
                       template='simple_white', 
                       color_discrete_map=color_scale
                       )  

    # Create the second wind rose chart
    fig2 = px.bar_polar(frequency_df_pred, 
                       r='frequency', 
                       theta='direction', 
                       color='speed', 
                       template='simple_white', 
                       color_discrete_map=color_scale
                       )  

    # Add all traces from the first wind rose chart to the subplot
    for trace in fig1.data:
        trace.showlegend = True
        fig.add_trace(trace, row=1, col=1)

    # Add all traces from the second wind rose chart to the subplot
    for trace in fig2.data:
        trace.showlegend = False
        fig.add_trace(trace, row=1, col=2)

    # Update the layout for the first subplot
    fig.update_layout(
        width = 1000,
        height = 600,
        polar_radialaxis_showgrid=True,  
        polar_angularaxis_showgrid=False,  
        polar_angularaxis_direction='clockwise', 
        polar_angularaxis_rotation=90,  
        polar_radialaxis_tickformat='.0%',  # Display the radial axis labels as percentages
        polar=dict(domain=dict(x=[0, 0.46])), # Specify the domain of the first subplot
        template = template
    )

    # Update the layout for the second subplot
    fig.update_layout(
        legend=dict(orientation="v",  # Horizontal orientation
                    yanchor="middle",
                    y=0.5, 
                    xanchor="center",
                    x=0.5 
                    ),
        polar2_angularaxis=dict(gridcolor='white'),
        polar2_radialaxis_showgrid=True,  
        polar2_angularaxis_showgrid=False,  
        polar2_angularaxis_direction='clockwise',  
        polar2_angularaxis_rotation=90,  
        polar2_radialaxis_tickformat='.0%',  # Display the radial axis labels as percentages
        polar2=dict(domain=dict(x=[0.54, 1])),  # Specify the domain of the second subplot
        template = template
    )

    return fig