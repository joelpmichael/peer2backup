# -*- coding: utf_8 -*-

import os
import sys

import configparser
import sqlite3

import shutil
import json

# increment ConfigDbVersion on DB schema changes
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

class db:
    def __init__(self,dbpath):

        if not os.path.isfile(dbpath):
            db_create(dbpath)

        self._conn = sqlite3.connect(dbpath)
        c = self._conn.cursor()

        c.execute('PRAGMA user_version')
        CurrentDbVersion = c.fetchone()[0]
        if CurrentDbVersion < ConfigDbVersion:
            self._conn.close
            db_upgrade(dbpath, CurrentDbVersion)
            self._conn = sqlite3.connect(dbpath)
            c = self._conn.cursor()

    def set(self,key,val):
        jsonval=json.dumps(val)
        c = self._conn.cursor()
        c.execute('DELETE FROM config WHERE cfg_key=?', (key,))
        c.execute('INSERT INTO config (cfg_key, cfg_value) VALUES (?, ?)', (key, jsonval,))
        self._conn.commit()

    def get(self,key,defaultval):
        c = self._conn.cursor()
        c.execute('SELECT cfg_value FROM config WHERE cfg_key=?', (key,))
        dbrow=c.fetchone()
        if dbrow:
            return json.loads(dbrow[0])
        else:
            self.set(key,defaultval)
            return defaultval

def db_upgrade(dbpath, CurrentDbVersion):

    # CurrentDbVersion == 0 means DB is brand new
    # If not brand new, back it up and perform full checks
    if CurrentDbVersion > 0:

        # back up DB before modifying
        backupdbpath = dbpath + '-backup-v' + str(CurrentDbVersion)
        shutil.copyfile(dbpath, backupdbpath)

        # connect to DB
        conn = sqlite3.connect(dbpath)
        c = conn.cursor()

        # perform integrity check
        c.execute('PRAGMA integrity_check')
        CheckResult = c.fetchone()[0]
        if CheckResult != 'ok':
            raise ValueError("DB Check failed: " + CheckResult)

        conn.close

    # connect to DB to perform upgrades
    conn = sqlite3.connect(dbpath)
    c = conn.cursor()

    # perform upgrades
    # IMPORTANT: upgrades are performed IN ORDER
    # remember to set CurrentDbVersion to the new version
    
    # Example:
    #if CurrentDbVersion < 2017090101:
    #    c.execute('CREATE TABLE foo(bar INT, baz TEXT)')
    #    c.execute('PRAGMA user_version = 2017090101')
    #    CurrentDbVersion = 2017090101
    #
    #if CurrentDbVersion < 2017090102:
    #    c.execute('alter table foo add column blah text')
    #    c.execute('PRAGMA user_version = 2017090102')
    #    CurrentDbVersion = 2017090102

    if CurrentDbVersion < 2017090101:
        c.execute('CREATE TABLE config(cfg_key TEXT PRIMARY KEY NOT NULL, cfg_value TEXT)')
        c.execute('PRAGMA user_version = 2017090101')
        conn.commit()
        CurrentDbVersion = 2017090101

    # full vacuum of DB, while we're doing maintenance
    c.execute('VACUUM')
    conn.close


def db_create(dbpath):

    conn = sqlite3.connect(dbpath)
    c = conn.cursor()
    c.execute('PRAGMA user_version = 0')
    conn.commit()
    conn.close

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
