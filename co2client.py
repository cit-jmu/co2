import urllib
from co2lib import create_db, get_conn
from simplejson import loads
from PIL import Image, ImageDraw, ImageFont
from dateutil import parser as dateparser
from datetime import datetime, date, timedelta
import StringIO
import csv


FETCH_URL = "http://localhost:8080/fetch/"
DB = 'clientsamples.sqlite'


def synchronize():
    conn = get_conn(DB)
    c = conn.cursor()
    c.execute("SELECT MAX(date) FROM samples")
    row = c.fetchone()
    date = row[0] or "0"
    print "Synchronizing starting with date %s" % date
    f = urllib.urlopen(FETCH_URL + date)
    result = f.read()
    rows = loads(result)
    for row in rows:
        c.execute("INSERT INTO samples (date, co2, co2abs, cellpres, celltemp, ivolt) VALUES(?,?,?,?,?,?)", row)
    conn.commit()
    c.close()
    print "Synchronized %s rows" % len(rows)


def generate_badge():
    conn = get_conn(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM samples ORDER BY DATE DESC LIMIT 1")
    row = c.fetchone()
    c.close()

    date = dateparser.parse(row[0])
    co2 = str(int(row[1]))

    timestamp = date.strftime("%I:%M%p")
    datestamp = date.strftime("%m/%d") if (datetime.now() - date).days > 0 else ""

    print "Generating badge: %s - %s %s" % (co2, timestamp, datestamp)

    image = Image.open("template.png")
    draw = ImageDraw.ImageDraw(image)
    font = ImageFont.truetype("arial.ttf", 10)
    draw.setfont(font)
    dw, dh = font.getsize(datestamp)
    draw.text((30 - dw / 2, 78 - dh), datestamp)
    tw, th = font.getsize(timestamp)
    draw.text((30 - tw / 2, 77 - th - dh), timestamp)
    font = ImageFont.truetype("arial.ttf", 26)
    draw.setfont(font)
    cw, ch = font.getsize(co2)
    draw.text((30 - cw / 2, 8), co2)
    image.save("webroot/badge.png")


def average_rows(sql, params, freq=timedelta(0, 60)):
    conn = get_conn(DB)
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
    if values:
        avg = sum(values) / len(values)
        data.append((time, avg))
    return data


def create_month_spreadsheet():
    today = date.today()
    start_date = date(today.year, today.month, 1)
    end_date = today + timedelta(1)

    print "Generating spreadsheet for current month"

    sql = "SELECT date,co2 FROM samples WHERE date>=? AND date<? ORDER BY date"
    params = (start_date.isoformat(), end_date.isoformat())
    output = StringIO.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Timestamp', 'Avg CO2'])
    for row in average_rows(sql, params, timedelta(0, 600)):
        writer.writerow(row)

    o = open('webroot/month.csv', 'wb')
    o.write(output.getvalue())
    o.close()

    o = open('webroot/month-%04d%02d.csv' % (today.year, today.month), 'wb')
    o.write(output.getvalue())
    o.close()


create_db(DB)
synchronize()
generate_badge()
create_month_spreadsheet()
