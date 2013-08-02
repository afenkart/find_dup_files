#!/usr/bin/env python
import sqlite3 as lite
import sys


class Storage:
    def __init__(self):
        self.con = lite.connect('files.db')

    def create_db(self):
        cur = self.con.cursor()    
        cur.execute("DROP TABLE IF EXISTS Cars")
        cur.execute("CREATE TABLE Cars(Id INT, Name TEXT, Price INT)")
        self.con.commit();

    def add_file(self, key, brand, price):
        cur = self.con.cursor()    
        cur.execute("INSERT INTO Cars VALUES(?, ?, ?)", (key, brand, price))
        self.con.commit();

db = Storage()

db.create_db();
db.add_file(2,'Mercedes',57127)
db.add_file(3,'Skoda',9000)
db.add_file(4,'Volvo',29000)
db.add_file(5,'Bentley',350000)
db.add_file(6,'Citroen',21000)
db.add_file(7,'Hummer',41400)
db.add_file(8,'Volkswagen',21600)
#con.commit()

#except lite.Error e:
#    print "Error %s:" % e.args[0]
    #.con.rollback()
