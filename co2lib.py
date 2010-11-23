import sqlite3

def get_conn(db='samples.sqlite'):
    return sqlite3.connect(db)


def create_db(db='samples.sqlite'):
    conn = get_conn(db)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS samples (date text, co2 real, co2abs real, cellpres real, celltemp real, ivolt real)")
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS date_index ON samples (date)")
    conn.commit()
    c.close()

