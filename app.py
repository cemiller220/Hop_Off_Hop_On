import pandas as pd
from bokeh.plotting import figure, output_file, show
from bokeh.charts import Bar
from bokeh.models import Range1d
from flask import Flask, render_template, request, redirect
from bokeh.embed import components
from flask_wtf import FlaskForm
from wtforms import SelectField
import subwayTripAnalysis as trip

app = Flask(__name__)
app.vars = {}

@app.route('/')
def main():
    return redirect('/home')
    
@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/data',methods=['GET','POST'])
def data():
    return render_template('data.html')

@app.route('/crowdedness')
def crowdedness():
    return render_template('crowdedness.html')

@app.route('/vis')
def vis():
    return render_template('vis.html')

@app.route('/get_data_map')
def get_data_map():
    with open('static/data/crowdedness.json') as f:
        crowdedness_json = f.read()
    return crowdedness_json

@app.route('/get_data_sample')
def get_data_sample():
    with open('static/data/sample_crowdedness.json') as f:
        crowdedness_json = f.read()
    return crowdedness_json

@app.route('/map',methods=['GET','POST'])
def map_plot():
    return render_template('map.html')

@app.route('/series',methods=['GET','POST'])
def series_plot():
    return render_template('series.html')

################################################################################

app.routes = {}
app.secret_key = 'development key'

class SelectForm(FlaskForm):
    lines1 = SelectField('Lines1', choices=[('Lines','Lines'),('1','1'),('2','2'),('3','3'),('4','4'),('5','5'),
                                            ('6','6'),('7','7'),('GS','GS'),('A','A'),('B','B'),('C','C'),('D','D'),('E','E'),('F','F'),
                                            ('FS','FS'),('G','G'),('J','J'),('L','L'),('M','M'),('N','N'),('Q','Q'),('R','R'),('Z','Z')])
    lines2 = SelectField('Lines2', choices=[('Lines','Lines'),('1','1'),('2','2'),('3','3'),('4','4'),('5','5'),
                                            ('6','6'),('7','7'),('GS','GS'),('A','A'),('B','B'),('C','C'),('D','D'),('E','E'),('F','F'),
                                            ('FS','FS'),('G','G'),('J','J'),('L','L'),('M','M'),('N','N'),('Q','Q'),('R','R'),('Z','Z')])
    days = SelectField('days', choices=[('sunday','Sunday'),('monday','Monday'),('tuesday','Tuesday'),('wednesday','Wednesday'),
                                        ('thursday','Thursday'),('friday','Friday'),('Saturday','Saturday')])

stops = pd.read_csv('static/data/stops_updated.txt',usecols=['stop_id','stop_name','stop_lat','stop_lon','location_type','parent_station','lines'])
stops = stops[stops['location_type']==1]
days = ['sunday','monday','tuesday','wednesday','thursday','friday','saturday']
hours = map('{:02d}'.format,range(1,13))
minutes = map('{:02d}'.format,range(0,60))
am_pm = ['am','pm']

@app.route('/input', methods=['GET','POST'])
def input():
    form = SelectForm()
    if request.method=='GET':
        return render_template('input.html',form=form)
    else:
        print request.form
        if 'lines1' in request.form:
            app.vars['line1'] = request.form['lines1']
            return render_template('input2.html',form=form,line1=app.vars['line1'])
        elif 'lines2' in request.form:
            app.vars['line2'] = request.form['lines2']
            app.stops1 = pd.DataFrame(stops[stops.lines.map(lambda x: app.vars['line1'] in x)])
            app.stops2 = pd.DataFrame(stops[stops.lines.map(lambda x: app.vars['line2'] in x)])
            return render_template('input3.html',line1=app.vars['line1'],line2=app.vars['line2'],data1=app.stops1['stop_name'],
                                   data2=app.stops2['stop_name'],form=form,hours=hours,minutes=minutes,am_pm=am_pm)
        elif 'start_station' in request.form:
            app.vars['date'] = request.form['days']
            app.vars['hour'] = request.form['hour']
            app.vars['minute'] = request.form['minute']
            app.vars['am_pm'] = request.form['am_pm']
            if request.form['hour']=='12' and request.form['am_pm']=='am':
                app.vars['time_wanted'] = '%02d:%02d %s'%(0,int(request.form['minute']),request.form['am_pm'])
            else:
                app.vars['time_wanted'] = '%02d:%02d %s'%(int(request.form['hour']),int(request.form['minute']),request.form['am_pm'])
            app.vars['start_name'] = request.form['start_station']
            app.vars['end_name'] = request.form['end_station']
            app.vars['start_id'] = app.stops1[app.stops1['stop_name'] == request.form['start_station']]['stop_id'].values[0]
            print app.vars['start_id']
            app.vars['end_id'] = app.stops2[app.stops2['stop_name'] == request.form['end_station']]['stop_id'].values[0]
            app.vars['titles'] = ['Depart from %s'%app.vars['start_name'],'Arrive at Transfer','Transfer From','Transfer Wait Time (mintues)',
                                  'Transfer Crowdedness','Transfer To', 'Depart from Transfer', 'Arrive at %s'%app.vars['end_name'], 'Total Time (minutes)']
            return redirect('/direct')

@app.route('/direct', methods=['GET','POST'])
def direct():
    if request.method=='GET':
        app.routes, app.page = trip.calculate_routes(app.vars['start_id'],app.vars['end_id'],app.vars['date'],app.vars['time_wanted'])
        if app.page=='multiple':
            return render_template('multiple_transfers.html',start_name=app.vars['start_name'],end_name=app.vars['end_name'])
        else:
            return redirect('/all')

@app.route('/shortest',methods=['GET','POST'])
def shortest():
    min_total=100000
    i=0
    for route in app.routes:
        if route[8]<min_total:
            min_total = route[8]
            min_ind = i
        i+=1
    return render_template('results_transfer.html',start_name=app.vars['start_name'],end_name=app.vars['end_name'], titles=app.vars['titles'],
                           results=app.routes[min_ind], other_action='transfer', other_value='Shortest Transfer Time', padding=72.7)

@app.route('/crowded',methods=['GET','POST'])
def crowded():
    min_total=100000
    i=0
    min_inds = []
    for route in app.routes:
        if route[4]<=min_total:
            min_total = route[4]
            min_inds.append(i)
        i+=1
    
    crowd_routes = []
    for ind in min_inds:
        crowd_routes.append(app.routes[ind])
    return render_template('results_all_transfers.html',start_name=app.vars['start_name'],end_name=app.vars['end_name'], titles=app.vars['titles'],
                           results=crowd_routes, other_action='transfer', other_value='Shortest Transfer Time', padding=72.7)

@app.route('/transfer',methods=['GET','POST'])
def transfer():
    min_transfer=100000
    i=0
    for route in app.routes:
        if route[3]<min_transfer:
            min_transfer = route[3]
            min_ind = i
        i+=1
    return render_template('results_transfer.html',start_name=app.vars['start_name'],end_name=app.vars['end_name'], titles=app.vars['titles'],
                           results=app.routes[min_ind], other_action='shortest', other_value='Shortest Total Time', padding=75)

@app.route('/all',methods=['GET','POST'])
def all():
    if app.page == 'direct':
        return render_template('results_direct.html',start_name=app.vars['start_name'],end_name=app.vars['end_name'],
                               titles=app.vars['titles'],results=app.routes)
    else:
        return render_template('results_all_transfers.html',start_name=app.vars['start_name'],end_name=app.vars['end_name'],
                               titles=app.vars['titles'],results=app.routes)

@app.route('/example',methods=['GET','POST'])
def example():
    return render_template('sample_result.html')


################################################################################
'''
transfers_all = pd.read_csv('transfers_all_nodirect.csv',usecols=['start','end','count'])

@app.route('/route',methods=['GET','POST'])
def route():
    try:
        app.vars['line'] = request.args.get('Name')
        transfers = transfers_all[transfers_all['start']==app.vars['line']]
        p = Bar(transfers, values='count', label=['end'], xlabel='Line Transfered To ', ylabel='Number of Trips',legend=False,width=1000)
        p.xaxis.major_label_text_font_size = '14pt'
        p.yaxis.major_label_text_font_size = '14pt'
        p.xaxis.axis_label_text_font_size = '20pt'
        p.yaxis.axis_label_text_font_size = '20pt'
        script, div = components(p)
        return render_template('route_plot.html',script=script,div=div,lines=lines,line=app.vars['line'])
    except:
        return render_template('route_blank.html')



transfer1AN_112_A09 = pd.read_csv('transferTimes/transfer1AN_112_A09.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transfer1AN_125_A24 = pd.read_csv('transferTimes/transfer1AN_125_A24.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transfer1AN_127_A27 = pd.read_csv('transferTimes/transfer1AN_127_A27.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transfer1CN_112_A09 = pd.read_csv('transferTimes/transfer1CN_112_A09.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transfer1CN_125_A24 = pd.read_csv('transferTimes/transfer1CN_125_A24.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transfer1CN_127_A27 = pd.read_csv('transferTimes/transfer1CN_127_A27.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transfer1EN_127_A27 = pd.read_csv('transferTimes/transfer1EN_127_A27.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transfer2AN_125_A24 = pd.read_csv('transferTimes/transfer2AN_125_A24.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transfer2AN_127_A27 = pd.read_csv('transferTimes/transfer2AN_127_A27.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transfer2AN_228_A36 = pd.read_csv('transferTimes/transfer2AN_228_A36.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transfer2AN_229_A38 = pd.read_csv('transferTimes/transfer2AN_229_A38.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transfer2CN_125_A24 = pd.read_csv('transferTimes/transfer2CN_125_A24.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transfer2CN_127_A27 = pd.read_csv('transferTimes/transfer2CN_127_A27.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transfer2CN_228_A36 = pd.read_csv('transferTimes/transfer2CN_228_A36.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transfer2CN_229_A38 = pd.read_csv('transferTimes/transfer2CN_229_A38.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transfer2EN_127_A27 = pd.read_csv('transferTimes/transfer2EN_127_A27.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transfer2EN_228_E01 = pd.read_csv('transferTimes/transfer2EN_228_E01.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transferA1N_A09_112 = pd.read_csv('transferTimes/transferA1N_A09_112.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transferA1N_A24_125 = pd.read_csv('transferTimes/transferA1N_A24_125.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transferA1N_A27_127 = pd.read_csv('transferTimes/transferA1N_A27_127.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transferC1N_A09_112 = pd.read_csv('transferTimes/transferC1N_A09_112.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transferC1N_A24_125 = pd.read_csv('transferTimes/transferC1N_A24_125.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transferC1N_A27_127 = pd.read_csv('transferTimes/transferC1N_A27_127.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transferE1N_A27_127 = pd.read_csv('transferTimes/transferE1N_A27_127.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transferA2N_A24_125 = pd.read_csv('transferTimes/transferA2N_A24_125.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transferA2N_A27_127 = pd.read_csv('transferTimes/transferA2N_A27_127.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transferA2N_A36_228 = pd.read_csv('transferTimes/transferA2N_A36_228.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transferA2N_A38_229 = pd.read_csv('transferTimes/transferA2N_A38_229.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transferC2N_A24_125 = pd.read_csv('transferTimes/transferC2N_A24_125.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transferC2N_A27_127 = pd.read_csv('transferTimes/transferC2N_A27_127.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transferC2N_A36_228 = pd.read_csv('transferTimes/transferC2N_A36_228.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transferC2N_A38_229 = pd.read_csv('transferTimes/transferC2N_A38_229.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transferE2N_A27_127 = pd.read_csv('transferTimes/transferE2N_A27_127.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transferE2N_E01_228 = pd.read_csv('transferTimes/transferE2N_E01_228.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)

transfer1AS_112_A09 = pd.read_csv('transferTimes/transfer1AS_112_A09.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transfer1AS_125_A24 = pd.read_csv('transferTimes/transfer1AS_125_A24.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transfer1AS_127_A27 = pd.read_csv('transferTimes/transfer1AS_127_A27.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transfer1CS_112_A09 = pd.read_csv('transferTimes/transfer1CS_112_A09.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transfer1CS_125_A24 = pd.read_csv('transferTimes/transfer1CS_125_A24.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transfer1CS_127_A27 = pd.read_csv('transferTimes/transfer1CS_127_A27.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transfer1ES_127_A27 = pd.read_csv('transferTimes/transfer1ES_127_A27.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transfer2AS_125_A24 = pd.read_csv('transferTimes/transfer2AS_125_A24.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transfer2AS_127_A27 = pd.read_csv('transferTimes/transfer2AS_127_A27.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transfer2AS_228_A36 = pd.read_csv('transferTimes/transfer2AS_228_A36.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transfer2AS_229_A38 = pd.read_csv('transferTimes/transfer2AS_229_A38.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transfer2CS_125_A24 = pd.read_csv('transferTimes/transfer2CS_125_A24.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transfer2CS_127_A27 = pd.read_csv('transferTimes/transfer2CS_127_A27.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transfer2CS_228_A36 = pd.read_csv('transferTimes/transfer2CS_228_A36.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transfer2CS_229_A38 = pd.read_csv('transferTimes/transfer2CS_229_A38.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transfer2ES_127_A27 = pd.read_csv('transferTimes/transfer2ES_127_A27.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transfer2ES_228_E01 = pd.read_csv('transferTimes/transfer2ES_228_E01.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transferA1S_A09_112 = pd.read_csv('transferTimes/transferA1S_A09_112.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transferA1S_A24_125 = pd.read_csv('transferTimes/transferA1S_A24_125.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transferA1S_A27_127 = pd.read_csv('transferTimes/transferA1S_A27_127.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transferC1S_A09_112 = pd.read_csv('transferTimes/transferC1S_A09_112.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transferC1S_A24_125 = pd.read_csv('transferTimes/transferC1S_A24_125.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transferC1S_A27_127 = pd.read_csv('transferTimes/transferC1S_A27_127.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transferE1S_A27_127 = pd.read_csv('transferTimes/transferE1S_A27_127.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transferA2S_A24_125 = pd.read_csv('transferTimes/transferA2S_A24_125.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transferA2S_A27_127 = pd.read_csv('transferTimes/transferA2S_A27_127.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transferA2S_A36_228 = pd.read_csv('transferTimes/transferA2S_A36_228.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transferA2S_A38_229 = pd.read_csv('transferTimes/transferA2S_A38_229.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transferC2S_A24_125 = pd.read_csv('transferTimes/transferC2S_A24_125.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transferC2S_A27_127 = pd.read_csv('transferTimes/transferC2S_A27_127.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transferC2S_A36_228 = pd.read_csv('transferTimes/transferC2S_A36_228.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transferC2S_A38_229 = pd.read_csv('transferTimes/transferC2S_A38_229.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transferE2S_A27_127 = pd.read_csv('transferTimes/transferE2S_A27_127.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)
transferE2S_E01_228 = pd.read_csv('transferTimes/transferE2S_E01_228.txt',parse_dates=['arrival_time','departure_time'],infer_datetime_format=True)

@app.route('/transfers')
def transfers():
    p1 = figure(title="168th St Station", x_axis_type='datetime', x_axis_label='Arrival Time', y_axis_label='Wait Time',plot_width=1000) 
    p1.circle(transferA1N_A09_112['arrival_time'],transferA1N_A09_112['transfer'],color='blue',legend='A -> 1 (N)')
    p1.circle(transferA1S_A09_112['arrival_time'],transferA1S_A09_112['transfer'],color='aqua',legend='A -> 1 (S)')
    p1.circle(transferC1N_A09_112['arrival_time'],transferC1N_A09_112['transfer'],color='green',legend='C -> 1 (N)')
    p1.circle(transferC1S_A09_112['arrival_time'],transferC1S_A09_112['transfer'],color='lawngreen',legend='C -> 1 (S)')
    p1.circle(transfer1AN_112_A09['arrival_time'],transfer1AN_112_A09['transfer'],color='dimgray',legend='1 -> A (N)')
    p1.circle(transfer1AS_112_A09['arrival_time'],transfer1AS_112_A09['transfer'],color='lightgray',legend='1 -> A (S)')
    p1.circle(transfer1CN_112_A09['arrival_time'],transfer1CN_112_A09['transfer'],color='maroon',legend='1 -> C (N)')
    p1.circle(transfer1CS_112_A09['arrival_time'],transfer1CS_112_A09['transfer'],color='red',legend='1 -> C (S)')
    p1.y_range = Range1d(0,20)
    p1.xaxis.major_label_text_font_size = '14pt'
    p1.yaxis.major_label_text_font_size = '14pt'
    p1.xaxis.axis_label_text_font_size = '20pt'
    p1.yaxis.axis_label_text_font_size = '20pt'
    p1.legend.legend_spacing = 0
    p1.legend.legend_padding = 1
    p1.legend.glyph_height = 15
    p1.legend.label_height = 15
    p1.title.text_font_size = '20pt'
    script1, div1 = components(p1)
    
    p2 = figure(title="59th St - Columbus Circle Station", x_axis_type='datetime', x_axis_label='Arrival Time', y_axis_label='Wait Time',width=1000) 
    p2.circle(transferA1N_A24_125['arrival_time'],transferA1N_A24_125['transfer'],color='blue',legend='A -> 1 (N)')
    p2.circle(transferA1S_A24_125['arrival_time'],transferA1S_A24_125['transfer'],color='aqua',legend='A -> 1 (S)')
    p2.circle(transferC1N_A24_125['arrival_time'],transferC1N_A24_125['transfer'],color='green',legend='C -> 1 (N)')
    p2.circle(transferC1S_A24_125['arrival_time'],transferC1S_A24_125['transfer'],color='lawngreen',legend='C -> 1 (S)')
    p2.circle(transferA2N_A24_125['arrival_time'],transferA2N_A24_125['transfer'],color='dimgray',legend='A -> 2 (N)')
    p2.circle(transferA2S_A24_125['arrival_time'],transferA2S_A24_125['transfer'],color='lightgray',legend='A -> 2 (S)')
    p2.circle(transferC2N_A24_125['arrival_time'],transferC2N_A24_125['transfer'],color='maroon',legend='C -> 2 (N)')
    p2.circle(transferC2S_A24_125['arrival_time'],transferC2S_A24_125['transfer'],color='red',legend='C -> 2 (S)')
    p2.circle(transfer1AN_125_A24['arrival_time'],transfer1AN_125_A24['transfer'],color='purple',legend='1 -> A (N)')
    p2.circle(transfer1AS_125_A24['arrival_time'],transfer1AS_125_A24['transfer'],color='plum',legend='1 -> A (S)')
    p2.circle(transfer1CN_125_A24['arrival_time'],transfer1CN_125_A24['transfer'],color='orangered',legend='1 -> C (N)')
    p2.circle(transfer1CS_125_A24['arrival_time'],transfer1CS_125_A24['transfer'],color='orange',legend='1 -> C (S)')
    p2.circle(transfer2AN_125_A24['arrival_time'],transfer2AN_125_A24['transfer'],color='brown',legend='2 -> A (N)')
    p2.circle(transfer2AS_125_A24['arrival_time'],transfer2AS_125_A24['transfer'],color='peru',legend='2 -> A (S)')
    p2.circle(transfer2CN_125_A24['arrival_time'],transfer2CN_125_A24['transfer'],color='deeppink',legend='2 -> C (N)')
    p2.circle(transfer2CS_125_A24['arrival_time'],transfer2CS_125_A24['transfer'],color='pink',legend='2 -> C (S)')
    p2.y_range = Range1d(0,20)
    p2.xaxis.major_label_text_font_size = '14pt'
    p2.yaxis.major_label_text_font_size = '14pt'
    p2.xaxis.axis_label_text_font_size = '20pt'
    p2.yaxis.axis_label_text_font_size = '20pt'
    p2.legend.legend_spacing = 0
    p2.legend.legend_padding = 1
    p2.legend.glyph_height = 15
    p2.legend.label_height = 15
    p2.title.text_font_size = '20pt'
    script2, div2 = components(p2)
    
    p3 = figure(title="Times Sq - 42nd St Station", x_axis_type='datetime', x_axis_label='Arrival Time', y_axis_label='Wait Time',width=1000) 
    p3.circle(transferA1N_A27_127['arrival_time'],transferA1N_A27_127['transfer'],color='blue',legend='A -> 1 (N)')
    p3.circle(transferA1S_A27_127['arrival_time'],transferA1S_A27_127['transfer'],color='aqua',legend='A -> 1 (S)')
    p3.circle(transferC1N_A27_127['arrival_time'],transferC1N_A27_127['transfer'],color='green',legend='C -> 1 (N)')
    p3.circle(transferC1S_A27_127['arrival_time'],transferC1S_A27_127['transfer'],color='lawngreen',legend='C -> 1 (S)')
    p3.circle(transferA2N_A27_127['arrival_time'],transferA2N_A27_127['transfer'],color='dimgray',legend='A -> 2 (N)')
    p3.circle(transferA2S_A27_127['arrival_time'],transferA2S_A27_127['transfer'],color='lightgray',legend='A -> 2 (S)')
    p3.circle(transferC2N_A27_127['arrival_time'],transferC2N_A27_127['transfer'],color='maroon',legend='C -> 2 (N)')
    p3.circle(transferC2S_A27_127['arrival_time'],transferC2S_A27_127['transfer'],color='red',legend='C -> 2 (S)')
    p3.circle(transferE1N_A27_127['arrival_time'],transferE1N_A27_127['transfer'],color='purple',legend='E -> 1 (N)')
    p3.circle(transferE1S_A27_127['arrival_time'],transferE1S_A27_127['transfer'],color='plum',legend='E -> 1 (S)')
    p3.circle(transferE2N_A27_127['arrival_time'],transferE2N_A27_127['transfer'],color='orangered',legend='E -> 2 (N)')
    p3.circle(transferE2S_A27_127['arrival_time'],transferE2S_A27_127['transfer'],color='orange',legend='E -> 2 (S)')
    p3.circle(transfer1AN_127_A27['arrival_time'],transfer1AN_127_A27['transfer'],color='brown',legend='1 -> A (N)')
    p3.circle(transfer1AS_127_A27['arrival_time'],transfer1AS_127_A27['transfer'],color='peru',legend='1 -> A (S)')
    p3.circle(transfer1CN_127_A27['arrival_time'],transfer1CN_127_A27['transfer'],color='deeppink',legend='1 -> C (N)')
    p3.circle(transfer1CS_127_A27['arrival_time'],transfer1CS_127_A27['transfer'],color='pink',legend='1 -> C (S)')
    p3.circle(transfer2AN_127_A27['arrival_time'],transfer2AN_127_A27['transfer'],color='darkolivegreen',legend='2 -> A (N)')
    p3.circle(transfer2AS_127_A27['arrival_time'],transfer2AS_127_A27['transfer'],color='olivedrab',legend='2 -> A (S)')
    p3.circle(transfer2CN_127_A27['arrival_time'],transfer2CN_127_A27['transfer'],color='yellow',legend='2 -> C (N)')
    p3.circle(transfer2CS_127_A27['arrival_time'],transfer2CS_127_A27['transfer'],color='palegoldenrod',legend='2 -> C (S)')
    p3.circle(transfer1EN_127_A27['arrival_time'],transfer1EN_127_A27['transfer'],color='slateblue',legend='1 -> E (N)')
    p3.circle(transfer1ES_127_A27['arrival_time'],transfer1ES_127_A27['transfer'],color='skyblue',legend='1 -> E (S)')
    p3.circle(transfer2EN_127_A27['arrival_time'],transfer2EN_127_A27['transfer'],color='indigo',legend='2 -> E (N)')    
    p3.circle(transfer2ES_127_A27['arrival_time'],transfer2ES_127_A27['transfer'],color='violet',legend='2 -> E (S)')
    p3.y_range = Range1d(0,20)
    p3.xaxis.major_label_text_font_size = '14pt'
    p3.yaxis.major_label_text_font_size = '14pt'
    p3.xaxis.axis_label_text_font_size = '20pt'
    p3.yaxis.axis_label_text_font_size = '20pt'
    p3.legend.legend_spacing = 0
    p3.legend.legend_padding = 1
    p3.legend.glyph_height = 15
    p3.legend.label_height = 15
    p3.title.text_font_size = '20pt'
    script3, div3 = components(p3)
    
    p4 = figure(title="Park Pl - Chambers St - World Trade Ctr Station", x_axis_type='datetime', x_axis_label='Arrival Time', y_axis_label='Wait Time',width=1000) 
    p4.circle(transferA2N_A36_228['arrival_time'],transferA2N_A36_228['transfer'],color='blue',legend='A -> 2 (N)')
    p4.circle(transferA2S_A36_228['arrival_time'],transferA2S_A36_228['transfer'],color='aqua',legend='A -> 2 (S)')
    p4.circle(transferC2N_A36_228['arrival_time'],transferC2N_A36_228['transfer'],color='green',legend='C -> 2 (N)')
    p4.circle(transferC2S_A36_228['arrival_time'],transferC2S_A36_228['transfer'],color='lawngreen',legend='C -> 2 (S)')
    p4.circle(transferE2N_E01_228['arrival_time'],transferE2N_E01_228['transfer'],color='dimgray',legend='E -> 2 (N)')
    p4.circle(transferE2S_E01_228['arrival_time'],transferE2S_E01_228['transfer'],color='lightgray',legend='E -> 2 (S)')
    p4.circle(transfer2AN_228_A36['arrival_time'],transfer2AN_228_A36['transfer'],color='maroon',legend='2 -> A (N)')
    p4.circle(transfer2AS_228_A36['arrival_time'],transfer2AS_228_A36['transfer'],color='red',legend='2 -> A (S)')
    p4.circle(transfer2CN_228_A36['arrival_time'],transfer2CN_228_A36['transfer'],color='purple',legend='2 -> C (N)')
    p4.circle(transfer2CS_228_A36['arrival_time'],transfer2CS_228_A36['transfer'],color='plum',legend='2 -> C (S)')
    p4.circle(transfer2EN_228_E01['arrival_time'],transfer2EN_228_E01['transfer'],color='orangered',legend='2 -> E (N)')
    p4.circle(transfer2ES_228_E01['arrival_time'],transfer2ES_228_E01['transfer'],color='orange',legend='2 -> E (S)')
    p4.y_range = Range1d(0,20)
    p4.xaxis.major_label_text_font_size = '14pt'
    p4.yaxis.major_label_text_font_size = '14pt'
    p4.xaxis.axis_label_text_font_size = '20pt'
    p4.yaxis.axis_label_text_font_size = '20pt'
    p4.legend.legend_spacing = 0
    p4.legend.legend_padding = 1
    p4.legend.glyph_height = 15
    p4.legend.label_height = 15
    p4.title.text_font_size = '20pt'
    script4, div4 = components(p4)
    
    p5 = figure(title="Fulton St Station", x_axis_type='datetime', x_axis_label='Arrival Time', y_axis_label='Wait Time',width=1000) 
    p5.circle(transferA2N_A38_229['arrival_time'],transferA2N_A38_229['transfer'],color='blue',legend='A -> 2 (N)')
    p5.circle(transferA2S_A38_229['arrival_time'],transferA2S_A38_229['transfer'],color='aqua',legend='A -> 2 (S)')
    p5.circle(transferC2N_A38_229['arrival_time'],transferC2N_A38_229['transfer'],color='green',legend='C -> 2 (N)')
    p5.circle(transferC2S_A38_229['arrival_time'],transferC2S_A38_229['transfer'],color='lawngreen',legend='C -> 2 (S)')
    p5.circle(transfer2AN_229_A38['arrival_time'],transfer2AN_229_A38['transfer'],color='dimgray',legend='2 -> A (N)')
    p5.circle(transfer2AS_229_A38['arrival_time'],transfer2AS_229_A38['transfer'],color='lightgray',legend='2 -> A (S)')
    p5.circle(transfer2CN_229_A38['arrival_time'],transfer2CN_229_A38['transfer'],color='maroon',legend='2 -> C (N)')
    p5.circle(transfer2CS_229_A38['arrival_time'],transfer2CS_229_A38['transfer'],color='red',legend='2 -> C (S)')
    p5.y_range = Range1d(0,20)
    p5.xaxis.major_label_text_font_size = '14pt'
    p5.yaxis.major_label_text_font_size = '14pt'
    p5.xaxis.axis_label_text_font_size = '20pt'
    p5.yaxis.axis_label_text_font_size = '20pt'
    p5.legend.legend_spacing = 0
    p5.legend.legend_padding = 1
    p5.legend.glyph_height = 15
    p5.legend.label_height = 15
    p5.title.text_font_size = '20pt'
    script5, div5 = components(p5)
    
    return render_template('transfers.html',lines=lines,script=script1,div=div1,script2=script2,div2=div2,script3=script3,div3=div3,script4=script4,div4=div4,script5=script5,div5=div5)



 
'''
if __name__ == '__main__':
    app.run(port=33507,debug=True)