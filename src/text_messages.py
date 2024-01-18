import requests
import numpy as np




def generate_dynamic_text(coords, avg_temp, avg_prec):
    url = f'https://api.open-elevation.com/api/v1/lookup?locations={coords.latitude},{coords.longitude}'
    response = requests.get(url)
    data = response.json()
    elevation = data['results'][0]['elevation']

    months = [
        "January", "February", "March", "April",
        "May", "June", "July", "August",
        "September", "October", "November", "December"
    ]
    text = (f"""
    {coords.address.split(',')[0].strip()}, is located at an altitude of {int(elevation)} m above sea level.
    {months[np.argmin(avg_temp.values)]} is the coldest month with an average of {int(min(avg_temp.values))} °C, while {months[np.argmax(avg_temp.values)]} is the hottest ({int(max(avg_temp.values))} °C).
    On average, {int(sum(avg_prec.values))} mm of rain falls every year, 
    with {months[np.argmax(avg_prec.values)]} beeing the wettest and {months[np.argmin(avg_prec.values)]} the driest month.    
    """)
    return text

def comm_temp_and_prec():
    title_t_and_p = """Temperature and precipitation"""
    comm_t_and_p = """This figure show the average monthly temperature and precipitation for the past 31 years and the forcasted
                      values for the next 31 years. Blue and lightblue bars represent precipitation,
                      red lines represent temperatures.
                      Hover over the bars and lines to see the values. Click on the legend to hide or show the data."""
    return comm_t_and_p, title_t_and_p

def comm_range_temp():
    title_r_t = """Average Temperature range"""
    comm_r_t = """This figure shows the average temperature range for each month of the year.
                    The top line shows the average maximum temperature of each month, the bottom line the averaged minima.
                    Keep in mind that these are averaged values, maximum and minimum temperatures can be outside of the plotted range.
                    When the range reaches 0 or below, a blue line highlights the freezing temperature.
                    Hover over the lines to see the values."""
    return comm_r_t, title_r_t

def comm_range_rh():
    title_rh = """Average Relative humidity range"""
    comm_rh = """This figure illustrates average humidity range for each month. 
                       Blue dolif and dotted line show the average relative and forecasted relative humidity.
                       The range delimiters show the mean of monhtly maximum and minimum relative humidity. 
                       Keep in mind that these are averaged values, maximum and minimum temperatures can be outside of the plotted range.
                       Hover over the lines to see the values.
                       """
    return comm_rh, title_rh


def comm_cloud_cover():
    title_cc = """Monthly hourly mean cloud cover with sunrise and sunset times"""
    comm_cc = """This plot shows cloud cover changes throughout the day and throughout the year.
                       The variaton of the grey colorscale on a column (month) shows the typical daily changes of cloud cover for that month (0% = clear sky, 100% = overcast).
                       The differences between the columns give an idea of which months are cloudier than others.
                       Keep in mind that we are looking at averages so even if the plot never shows clear skies (example: 12% cloud cover), clear skies are still possible.
                       The two lines show sunrise and sunset times, adjusted for the timezone of the location as well as daylight saving times.
                       Hover over the lines to see the values. Click on the legend to hide/show the data."""
    return comm_cc, title_cc

def comm_wind_rose():
    title_wr = """Wind rose"""
    comm_wr = """Each wind direction is represented by a bar. The length of the bars show how often the wind blows from that direction (in %).
                    The colours indicate the averaged wind speed in km/h. 
                    WATCH OUT: The radial scale is different for each subplot to make the differences more visible.
                    Keep in mind that these are averaged values and don't highlight particularly strong winds.
                    Hover over the lines to see the values. Click on the legend to hide/show the data."""
    return comm_wr, title_wr





