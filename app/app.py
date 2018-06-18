import os
import configparser

config = configparser.ConfigParser()
config.read('config.ini')

api_endpt = config['quandl.com']['api_endpt']
api_key = config['quandl.com']['api_key']

from flask import Flask, Blueprint, g, flash, redirect, render_template, request, url_for

from bokeh.embed import components
from bokeh.plotting import figure
from bokeh.resources import CDN

import requests
import zipfile
import pandas as pd
from math import pi

bokeh_css = CDN.render_css()
bokeh_js = CDN.render_js()

app = Flask(__name__, instance_relative_config=True)
app.config.from_mapping(SECRET_KEY=os.urandom(16))

def getTickerList():
    r = requests.get(api_endpt + 'databases/WIKI/codes', params={'api_key': api_key})
    os.makedirs(app.instance_path, exist_ok=True)
    with open(os.path.join(app.instance_path, 'WIKI-datasets-codes.zip'), mode='wb') as f:
        f.write(r.content)

    with zipfile.ZipFile(os.path.join(app.instance_path, 'WIKI-datasets-codes.zip')) as myzip:
        with myzip.open('WIKI-datasets-codes.csv') as myfile:
            df = pd.read_csv(myfile, header=None)
            return list(df[0].str.split('/', expand=True)[1].values)

tickerList = getTickerList()
# print(tickerList)

@app.route('/', methods=('GET', 'POST'))
def index():
    if request.method == 'POST':
        return redirect(url_for('graph', tickerSymbol=request.form['tickerSymbol']))
    """Show homepage."""
    return render_template('index.html')

@app.route('/<tickerSymbol>/', methods=('GET', 'POST'))
def graph(tickerSymbol):
    if request.method == 'POST':
        return redirect(url_for('graph', tickerSymbol=request.form['tickerSymbol']))

    if tickerSymbol in tickerList:
        r = requests.get(api_endpt + 'datatables/WIKI/PRICES', params={'ticker': tickerSymbol,'api_key': api_key})
        datatable_json = r.json()['datatable']
        df = pd.DataFrame(datatable_json['data'][::-1], columns=[col['name'] for col in datatable_json['columns']])
        df['date'] = pd.to_datetime(df['date'])

        p = figure(width=1200, sizing_mode='scale_width', x_axis_type='datetime', tools='xpan,xwheel_zoom,box_zoom,reset,save', title=tickerSymbol)
        p.xaxis.major_label_orientation = pi/6
        p.xaxis.axis_label = 'Date'
        p.yaxis.axis_label = 'Price'

        rise = df.close > df.open
        fall = df.close < df.open

        p.segment(df.date, df.low, df.date, df.high, color='black')
        vbar_xwidth = 16*3600*1000 # in ms
        p.vbar(df.date[rise], vbar_xwidth, df.open[rise], df.close[rise], fill_color='#00FF00', line_color='black')
        p.vbar(df.date[fall], vbar_xwidth, df.open[fall], df.close[fall], fill_color='#FF0000', line_color='black')

        plot_script, plot_div = components(p)
        return render_template('graph.html', tickerSymbol=tickerSymbol, bokeh_css=bokeh_css, bokeh_js=bokeh_js, plot_div=plot_div, plot_script=plot_script)
    else:
        flash(tickerSymbol + ' is not a valid ticker.')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run()
