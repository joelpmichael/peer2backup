# -*- coding: utf_8 -*-

# configdb
# database of key=value pairs for configuration
# values are stored as JSON for complex data type value storage

# FIXME - error handling!

import os
import sys

import configparser
import sqlite3

import shutil
import json

# increment configdb_version on DB schema changes
configdb_version = 2017090101

# reads config file to discover location of config database
# default configdb is ./configdb.sqlite

# db path should be only setting in config file
# everything else should be in configdb

def File(configfile):

    config = configparser.ConfigParser()

    # default path to config db is ./configdb.sqlite
    default_configdb_path = os.path.join(sys.path[0],'configdb.sqlite')

    config.read(configfile)

    if not 'db' in config:
        config['db'] = {}
        config['db']['path'] = default_configdb_path

    configdb_path = config['db'].get('path',default_configdb_path)
    with open(configfile, 'w') as cfgfile:
        config.write(cfgfile)
    cfgfile.close

    return configdb_path

# main config db
class ConfigDb:
    def __init__(self,dbpath):

        # create new DB if it doesn't exist
        if not os.path.isfile(dbpath):
            db_create(dbpath)

        # connect to db
        self._conn = sqlite3.connect(dbpath)
        self._conn.isolation_level = None
        c = self._conn.cursor()
        # enable cell size checking
        c.execute('PRAGMA cell_size_check = 1')
        # optimize and quick-check on open
        c.execute('PRAGMA quick_check')
        check_result = c.fetchone()[0]
        if check_result != 'ok':
            raise ValueError("DB Check failed: " + check_result)
        c.execute('PRAGMA optimize')

        # check current db version against code version
        # perform upgrade if necessary
        c.execute('PRAGMA user_version')
        current_db_version = c.fetchone()[0]
        if current_db_version < configdb_version:
            self._Upgrade(current_db_version)

    def Set(self,key,val):
        # set a configdb key to value
        # blind-delete and insert to ensure that
        # missing keys are added and duplicate keys (if any) are removed
        jsonval=json.dumps(val)
        c = self._conn.cursor()
        c.execute('DELETE FROM config WHERE cfg_key=?', (key,))
        c.execute('INSERT INTO config (cfg_key, cfg_value) VALUES (?, ?)', (key, jsonval,))

    def Get(self,key,defaultval):
        # get a configdb value
        # if the value doesn't exist, insert & return the default value
        c = self._conn.cursor()
        c.execute('SELECT cfg_value FROM config WHERE cfg_key=?', (key,))
        dbrow=c.fetchone()
        if dbrow:
            return json.loads(dbrow[0])
        else:
            self.Set(key,defaultval)
            return defaultval

    def _Upgrade(self,current_db_version):

        # connect to DB handle
        c = self._conn.cursor()

        # current_db_version == 0 means DB is brand new
        # If not brand new, back it up and perform full checks
        if current_db_version > 0:

            c.execute('PRAGMA database_list')
            dbpath = c.fetchone()[2]

            # back up DB before modifying
            # lock the entire DB
            # see https://sqlite.org/pragma.html#pragma_locking_mode

            c.execute('PRAGMA locking_mode = EXCLUSIVE')
            # write some data to obtain an exclusive lock
            c.execute('CREATE TABLE __temp_upgrade (temp INT)')
            c.execute('INSERT INTO __temp_upgrade (temp) values (1)')
            c.execute('DROP TABLE __temp_upgrade')
            c.execute('PRAGMA query_only = 1')

            # copy DB file while we have an exclusive lock
            backupdbpath = dbpath + '-backup-v' + str(current_db_version)
            shutil.copyfile(dbpath, backupdbpath)

            # unlock & write again to release exclusive lock
            c.execute('PRAGMA query_only = 0')
            c.execute('PRAGMA locking_mode = NORMAL')
            c.execute('CREATE TABLE __temp_upgrade (temp INT)')
            c.execute('INSERT INTO __temp_upgrade (temp) values (1)')
            c.execute('DROP TABLE __temp_upgrade')

            # perform integrity check
            c.execute('PRAGMA integrity_check')
            check_result = c.fetchone()[0]
            if check_result != 'ok':
                raise ValueError("DB Check failed: " + check_result)

        # perform upgrades
        # IMPORTANT: upgrades are performed IN ORDER
        # remember to set current_db_version to the new version
    
        # Example:
        #if current_db_version < 2017090101:
        #    c.execute('CREATE TABLE foo(bar INT, baz TEXT)')
        #    c.execute('PRAGMA user_version = 2017090101')
        #    current_db_version = 2017090101
        #
        #if current_db_version < 2017090102:
        #    c.execute('alter table foo add column blah text')
        #    c.execute('PRAGMA user_version = 2017090102')
        #    current_db_version = 2017090102

        # version 2017090101
        # initial version
        # simple key,value table
        if current_db_version < 2017090101:
            c.execute('CREATE TABLE config (cfg_key TEXT PRIMARY KEY NOT NULL, cfg_value TEXT)')
            c.execute('PRAGMA user_version = 2017090101')
            current_db_version = 2017090101

        # End of upgrades, run an optimize and vacuum too
        c.execute('PRAGMA optimize')
        c.execute('VACUUM')

def db_create(dbpath):

    conn = sqlite3.connect(dbpath)
    conn.isolation_level = None
    c = conn.cursor()
    # set initial version to 0
    # so first upgrade doesn't bother backing up
    c.execute('PRAGMA user_version = 0')
    # enable cell size checking
    c.execute('PRAGMA cell_size_check = 1')
    # set 4k page size
    c.execute('PRAGMA page_size = 4096')
    # set UTF-8 encoding
    c.execute('PRAGMA encoding = "UTF-8"')
    # vacuum to make page size stick
    c.execute('VACUUM')
    conn.close

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
