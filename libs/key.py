# -*- coding: utf_8 -*-

# Crypto Key Database

import os
import sqlite3
import shutil
import gnupg

# increment ConfigDbVersion on DB schema changes
KeyDbVersion = 2017090101

# main key db
class keydb:
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
        CheckResult = c.fetchone()[0]
        if CheckResult != 'ok':
            raise ValueError("DB Check failed: " + CheckResult)
        c.execute('PRAGMA optimize')

        # check current db version against code version
        # perform upgrade if necessary
        c.execute('PRAGMA user_version')
        CurrentDbVersion = c.fetchone()[0]
        if CurrentDbVersion < ConfigDbVersion:
            self._upgrade(CurrentDbVersion)

    def _upgrade(self,CurrentDbVersion):

        # connect to DB handle
        c = self._conn.cursor()

        # CurrentDbVersion == 0 means DB is brand new
        # If not brand new, back it up and perform full checks
        if CurrentDbVersion > 0:

            c.execute('PRAGMA database_list')
            dbpath = c.fetchone()[2]
            print(dbpath)

            # back up DB before modifying
            # lock the entire DB
            # see https://sqlite.org/pragma.html#pragma_locking_mode

            c.execute('PRAGMA locking_mode = EXCLUSIVE')
            # write some data to obtain an exclusive lock
            c.execute('CREATE TABLE __temp_upgrade (temp INT)')
            c.execute('INSERT INTO __temp_upgrade (temp) values (1)')
            c.execute('SELECT * FROM __temp_upgrade')
            c.execute('DROP TABLE __temp_upgrade')
            c.execute('PRAGMA query_only = 1')

            # copy DB file while we have an exclusive lock
            backupdbpath = dbpath + '-backup-v' + str(CurrentDbVersion)
            shutil.copyfile(dbpath, backupdbpath)

            # unlock & write again to release exclusive lock
            c.execute('PRAGMA query_only = 0')
            c.execute('PRAGMA locking_mode = NORMAL')
            c.execute('CREATE TABLE __temp_upgrade (temp INT)')
            c.execute('INSERT INTO __temp_upgrade (temp) values (1)')
            c.execute('SELECT * FROM __temp_upgrade')
            c.execute('DROP TABLE __temp_upgrade')

            # perform integrity check
            c.execute('PRAGMA integrity_check')
            CheckResult = c.fetchone()[0]
            if CheckResult != 'ok':
                raise ValueError("DB Check failed: " + CheckResult)

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

        # version 2017090101
        # initial version
        # simple key,value table
        if CurrentDbVersion < 2017090101:
            c.execute('CREATE TABLE privkey (key_id TEXT PRIMARY KEY NOT NULL, key TEXT, key_unlock_key_id TEXT, key_unlock_password TEXT, key_unlock_salt TEXT)')
            c.execute('CREATE TABLE pubkey (key_id TEXT PRIMARY KEY NOT NULL, key TEXT, key_expiry TEXT)')
            c.execute('PRAGMA user_version = 2017090101')
            CurrentDbVersion = 2017090101

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
