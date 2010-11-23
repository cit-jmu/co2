import urllib
from co2lib import create_db, get_conn
from simplejson import loads
from PIL import Image, ImageDraw, ImageFont
from dateutil import parser as dateparser
from datetime import datetime


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


create_db(DB)
synchronize()
generate_badge()
