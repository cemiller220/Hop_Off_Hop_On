import pandas as pd
import numpy as np
import pickle
from bisect import bisect
from ast import literal_eval
import math
import time

stop_times = pd.read_csv('static/data/stop_times_updated2.txt',usecols=['trip_id','stop_id','stop_sequence','arrival_seconds','departure_seconds'])
calendar = pd.read_csv('static/data/calendar.txt', usecols=['service_id','monday','saturday','sunday']).rename(columns={'monday': 'weekday'})
trips = pd.read_csv('static/data/trips.txt',usecols=['route_id','service_id','trip_id'])
stops = pd.read_csv('static/data/stops_updated.txt',usecols=['stop_id','stop_name','stop_lat','stop_lon','location_type','parent_station','lines'])
stops['lines'] = stops['lines'].apply(literal_eval)
transfers = pd.read_csv('static/data/transfers_updated2.txt', usecols=['from_stop_id','to_stop_id','start_line','end_line'])
#with open('static/models/fit_dict_all.pkl','r') as f:
#fit = pickle.load(f)

trips_merged = pd.merge(trips,calendar, on='service_id')

def time_to_seconds(time):
    ''' convert time string HH:MM:SS to seconds '''
    am_pm = time.split()
    hr_min = map(int,am_pm[0].split(':'))
    if hr_min[0] == 12:
        hr_min[0] = 0
    if am_pm[1] == 'am':
        return hr_min[0]*3600 + hr_min[1]*60
    elif am_pm[1] == 'pm':
        return hr_min[0]*3600 + (12*3600) + hr_min[1]*60

def seconds_to_time(seconds):
    ''' convert seconds to time string HH:MM:SS '''
    hour = seconds // 3600
    minute = (seconds - hour*3600) // 60
    second = seconds - hour*3600 - minute*60
    if hour >= 24:
        hour = hour - 24
    return '%02d:%02d:%02d'%(hour,minute,second)

def find_transfer_stations(start_lines,end_lines):
    ''' find all stations to transfer between two lines '''
    transfer_stations = transfers[(transfers['start_line'].isin(start_lines)) & (transfers['end_line'].isin(end_lines))].drop_duplicates()
    return transfer_stations

def get_trip_direct(start,end,day,time):
    ''' find the schedule time closest to time wanted if line is not specified '''
    #get which trips are on specified day (weekday/saturday/sunday)
    trip_ids = trips_merged[(trips_merged[day] == 1)]['trip_id']
    
    #get all times up to 1 hour after wanted time 
    child_stops_start = stops[stops['parent_station']==start]['stop_id']
    start_times = stop_times[(stop_times['stop_id'].isin(child_stops_start)) & 
                             (stop_times['trip_id'].isin(trip_ids)) & 
                             (stop_times['departure_seconds'] >= time) &
                             (stop_times['departure_seconds'] <= time+3600)][['trip_id','stop_id','stop_sequence','departure_seconds']]
    
    child_stops_end = stops[stops['parent_station']==end]['stop_id']
    end_times = stop_times[(stop_times['stop_id'].isin(child_stops_end)) & 
                           (stop_times['trip_id'].isin(start_times['trip_id']))][['trip_id','stop_id','stop_sequence','arrival_seconds']]
    
    #pick correct direction
    trip_times = pd.merge(start_times,end_times, on='trip_id')
    trip_times = trip_times[trip_times['stop_sequence_x'] < trip_times['stop_sequence_y']]
    if not trip_times.empty:
        trip = trip_times.sort_values('departure_seconds').reset_index(drop=True).loc[0]
    else:
        trip = pd.DataFrame()
    
    return trip

def get_trip_line(start,end,line,day,time):
    ''' find the schedule time closest to time wanted with specified line '''
    #get which trips are on specified day (weekday/saturday/sunday)
    trip_ids = trips_merged[(trips_merged[day] == 1) & (trips_merged['route_id'] == line)]['trip_id']
    
    #get all times up to 1 hour after wanted time 
    child_stops_start = stops[stops['parent_station']==start]['stop_id']
    start_times = stop_times[(stop_times['stop_id'].isin(child_stops_start)) & 
                             (stop_times['trip_id'].isin(trip_ids)) & 
                             (stop_times['departure_seconds'] >= time) &
                             (stop_times['departure_seconds'] <= time+3600)][['trip_id','stop_id','stop_sequence','departure_seconds']]
    
    child_stops_end = stops[stops['parent_station']==end]['stop_id']
    end_times = stop_times[(stop_times['stop_id'].isin(child_stops_end)) & 
                           (stop_times['trip_id'].isin(start_times['trip_id']))][['trip_id','stop_id','stop_sequence','arrival_seconds']]
    
    #pick correct direction
    trip_times = pd.merge(start_times,end_times, on='trip_id')
    trip_times = trip_times[trip_times['stop_sequence_x'] < trip_times['stop_sequence_y']]
    if not trip_times.empty:
        trip = trip_times.sort_values('departure_seconds').reset_index(drop=True).loc[0]
    else:
        trip = pd.DataFrame()
    
    return trip

def get_stop_name(stop_id):
    '''return stop name from stop id number'''
    return stops[stops['stop_id'] == stop_id]['stop_name'].values[0]

def get_line(trip_id):
    ''' return train line from trip id '''
    return trip_id.split('_')[2].split('..')[0]

def predict_crowdedness(stop_id,day,time):
    ''' predict crowdedness value between 1-10 from model '''
    if day == 'Saturday' or day == 'Sunday':
        day = 'Weekend'
    ranges = np.logspace(0,2.65,9)
    with open('static/models/fit_dict%s.pkl'%stop_id[0],'r') as f:
        fit = pickle.load(f)

    return bisect(ranges,fit[(stop_id,day)].predict(time)[0])+1

################################################################################################

def calculate_routes(start,end,day,time_wanted):
    ''' calculate all possible routes from start to end '''
    weekdays = ['monday','tuesday','wednesday','thursday','friday']
    if day in weekdays:
        day = 'weekday'
    
    time = time_to_seconds(time_wanted)
    
    #are there any direct routes between start and end within an hour of the time wanted
    #checks for any weird/atypical routes a train may take
    direct_route = get_trip_direct(start,end,day,time)

    routes = []
    if direct_route.empty:
        #if no direct routes, find which lines normally come to start and end stations and all transfer stations between them
        start_lines = stops[stops['stop_id'] == start]['lines'].values[0]
        end_lines = stops[stops['stop_id'] == end]['lines'].values[0]
        transfer_stations = find_transfer_stations(start_lines,end_lines)
        
        if transfer_stations.empty: #multiple transfers needed
            page='multiple'
        
        else:
            for transfer in transfer_stations.values: #0: from_stop_id, 1: to_stop_id, 2: from_line, 3: to_line
                #get schedule time from start to beginning of transfer
                trip1 = get_trip_line(start,transfer[0],transfer[2],day,time)
                if trip1.empty:
                    #no times within an hour of time wanted, skip to next station
                    continue

                trip2 = get_trip_line(transfer[1],end,transfer[3],day,trip1['arrival_seconds'])
                if trip2.empty:
                    #no times within an hour of time wanted, skip to next station
                    continue
                
                #average crowdedness of two transfer points
                crowd1 = predict_crowdedness(transfer[0],day.title(),trip1['arrival_seconds'])
                crowd2 = predict_crowdedness(transfer[0],day.title(),trip1['departure_seconds'])
                crowd_value = int(math.ceil((crowd1 + crowd2) / 2.0))

                #convert results to format for webpage
                departure_time = seconds_to_time(trip1['departure_seconds'])
                start_transfer_time = seconds_to_time(trip1['arrival_seconds'])
                end_transfer_time = seconds_to_time(trip2['departure_seconds'])
                arrival_time = seconds_to_time(trip2['arrival_seconds'])
                start_transfer_station = get_stop_name(transfer[0]) + ', ' + get_line(trip1['trip_id']) + ' Train'
                end_transfer_station = get_stop_name(transfer[1]) + ', ' + get_line(trip2['trip_id']) + ' Train'
                wait_time = (trip2['departure_seconds'] - trip1['arrival_seconds']) / 60.0
                total_time = (trip2['arrival_seconds'] - trip1['departure_seconds']) / 60.0
                
                #append to results
                routes.append([departure_time, start_transfer_time, start_transfer_station, wait_time, crowd_value, end_transfer_station, end_transfer_time, arrival_time, total_time])
                page = 'transfer'
    else:
        #convert results to format for webpage
        departure_time = seconds_to_time(direct_route['departure_seconds'])
        arrival_time = seconds_to_time(direct_route['arrival_seconds'])
        total_time = (direct_route['arrival_seconds'] - direct_route['departure_seconds']) / 60.0
        
        #append to results
        routes.append([departure_time,'','','','','','',arrival_time,total_time])
        page = 'direct'

    return routes, page


####################################################################################
#test case
'''
start = '121'
end = '217'
day='sunday'
time_wanted = '8:00 am'
print calculate_routes(start,end,day,time_wanted)
'''