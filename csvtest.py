import csv
from urllib2 import urlopen
from urllib import urlencode

def format_row(row):
    precipitation = row['PREC.I-1 (in) ']
    return dict(
        timestamp='%sT%s' % (row['Report_date'], row['Time (EST)']),
        precipitation=float(precipitation) if precipitation != '-99.9' else None,
        temperature=float(row['TAVG.H-1 (degC) ']),
        radiation=float(row['SRADV.H-1 (watt/m2) ']),
    )

params = dict(
    format='copy',
    interval='DAY',
    intervalType='View Current',
    month='01',
    report='ALL',
    site_name='Shenandoah',
    site_network='scan',
    sitenum='2088',
    state_name='Virginia',
    time_zone='EST',
    timeseries='Hourly',
    userEmail='',
)

file = urlopen('http://www.wcc.nrcs.usda.gov/nwcc/view',
               urlencode(params))
file.readline()  # skip first header row
data = map(format_row, filter(None, csv.DictReader(file)))
file.close()

print data
