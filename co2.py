from bottle import route, run, response, request
from datetime import datetime, timedelta, date
from getopt import getopt, GetoptError
from serial import Serial, SerialException
from simplejson import dumps
from threading import Thread
from xml.dom.minidom import parseString
from xml.parsers.expat import ExpatError
import os
import sqlite3
import sys
import time
import random
import gviz_api
import csv
import StringIO
from dateutil import parser as dateparser
from co2lib import create_db, get_conn

simulate = True


class Samples(Thread):

    lastsample = None
    lastsampletime = None

    def __init__(self, simulate=False, *args, **kwargs):
        super(Samples, self).__init__(*args, **kwargs)
        self.simulate = simulate

    def run(self):
        conn = get_conn()
        while True:
            try:
                if not self.simulate:
                    print "Reading sample"
                    ser = Serial(2, 9600)
                    ser.readline()  # first line may be incomplete, read and discard
                    line = ser.readline()  # second line should be good
                    ser.close()
                else:
                    # simluation mode, make up some data
                    print "Simulating sample"
                    line = "<s><t><co2>%s</co2><co2abs>-1</co2abs><cellpres>-1</cellpres><celltemp>-1</celltemp><ivolt>-1</ivolt></t></s>" % random.randint(200, 500)
            except SerialException:
                # port is not available right now, try again later
                line = None
            try:
                if line:
                    x = parseString(line)
                    self.lastsample = dict((n.nodeName, float(n.firstChild.data)) for n in x.firstChild.firstChild.childNodes if n.nodeName != 'raw')
                    self.lastsampletime = datetime.now()
                    c = conn.cursor()
                    c.execute("INSERT INTO samples (date, co2, co2abs, cellpres, celltemp, ivolt) VALUES(?,?,?,?,?,?)",
                          (self.lastsampletime.isoformat(),
                           self.lastsample['co2'],
                           self.lastsample['co2abs'],
                           self.lastsample['cellpres'],
                           self.lastsample['celltemp'],
                           self.lastsample['ivolt'])
                          )
                    try:
                        conn.commit()
                    except OperationalError:
                        print "Could not commit sample - database locked?"
                        pass # Ignore locked database error
                    c.close()
            except ExpatError, err:
                # line was invalid, try again later
                print err
            time.sleep(10)


@route('/')
def current():
    global samples
    result = dict(result='ok',
                  data=samples.lastsample,
                  timestamp=samples.lastsampletime.isoformat())
    callback = request.GET.get('callback')
    if callback:
        return '%s(%s)' % (callback, dumps(result))
    else:
        return result


@route('/stats')
def stats():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*),MIN(date),MAX(date) FROM samples")
    stats = c.fetchone()
    c.close()
    return dict(count=stats[0], earliest=stats[1], latest=stats[2])


@route('/fetch/:date')
def fetch(date):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM samples WHERE date>? ORDER BY date LIMIT 1000", (date,))
    rows = c.fetchall()
    c.close()
    return dumps(rows)



def average_rows(sql, params, freq=timedelta(0, 60)):
    conn = get_conn()
    c = conn.cursor()
    c.execute(sql, params)
    rows = c.fetchall()
    values = [float(rows[0][1])]
    time = dateparser.parse(rows[0][0])
    data = []
    for row in rows[1:]:
        if dateparser.parse(row[0]) - time > freq:
            avg = sum(values) / len(values)
            data.append((time, avg))
            time = dateparser.parse(row[0])
            values = [float(row[1])]
        else:
            values.append(float(row[1]))
    c.close()
    return data


@route('/csv')
def download_csv():
    try:
        start_date = dateparser.parse(request.GET.get('from')).date()
    except:
        start_date = date.today()
    try:
        end_date = dateparser.parse(request.GET.get('until')).date()
    except:
        end_date = date.today() + timedelta(1)
    if end_date <= start_date:
        end_date = start_date + timedelta(1)
    sql = "SELECT date,co2 FROM samples WHERE date>=? AND date<? ORDER BY date"
    params = (start_date.isoformat(), end_date.isoformat())

    output = StringIO.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Timestamp', 'Avg CO2'])
    for row in average_rows(sql, params, timedelta(0, 600)):
        writer.writerow(row)

    response.header['Content-type'] = 'text/csv'
    response.header['Content-disposition'] = 'attachment; filename="co2.csv"'
    return output.getvalue()


@route('/recent')
def recent():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT date,co2 FROM samples WHERE date>? ORDER BY date",
              ((datetime.now() - timedelta(1)).isoformat(),))
    rows = c.fetchall()
    values = [float(rows[0][1])]
    time = dateparser.parse(rows[0][0])
    data = []
    for row in rows[1:]:
        if dateparser.parse(row[0]) - time > timedelta(0, 60):
            avg = sum(values) / len(values)
            data.append((time, avg))
            time = dateparser.parse(row[0])
            values = [float(row[1])]
        else:
            values.append(float(row[1]))

    c.close()

    datatable = gviz_api.DataTable([("time", "datetime"), ("CO2", "number")], data=data)

    callback = request.GET.get('responseHandler', 'google.visualization.Query.setResponse')
    return datatable.ToJSonResponse(response_handler=callback)



if os.environ.get('BOTTLE_CHILD'):

    print "Simulation mode is %s" % ("on" if simulate else "off")
    create_db()
    samples = Samples(simulate=simulate)
    samples.setDaemon(True)
    samples.start()


run(host='0.0.0.0', port=8080, reloader=True)
