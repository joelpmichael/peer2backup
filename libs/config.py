# -*- coding: utf_8 -*-

import os
import sys

import configparser
import sqlite3

ConfigDbVersion = 2017090101

# reads config file to discover location of config database
# default configdb is ./configdb.sqlite
def file(configfile):

    config = configparser.ConfigParser()
    DefaultConfigDbPath = os.path.join(sys.path[0],'configdb.sqlite')

    config.read(configfile)

    if not 'db' in config:
        config['db'] = {}
        config['db']['path'] = DefaultConfigDbPath

    configdbpath = config['db'].get('path',DefaultConfigDbPath)
    with open(configfile, 'w') as cfgfile:
        config.write(cfgfile)
    cfgfile.close

    return configdbpath

def db(dbpath):

    if not os.path.isfile(dbpath):
        db_create(dbpath)

def db_create(dbpath):

    conn = sqlite3.connect(dbpath)
    c = conn.cursor()
    c.execute('PRAGMA user_version = 0')
    print(dbpath)

