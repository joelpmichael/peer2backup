# -*- coding: utf_8 -*-
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# auth
# API access authentication token handling

# token request:
# master_key_id = master key ID
# nonce = random 32-character string
# signature = RSA signature of nonce using master key

import os
import sqlite3

# increment authdb_version on DB schema changes
authdb_version = 2017090101

class AuthDb:
    def __init__(self,dbpath):

        self._dbpath = dbpath

        # create new DB if it doesn't exist
        if not os.path.isfile(self._dbpath):
            db_create(self._dbpath)

        # connect to db
        conn = sqlite3.connect(self._dbpath)
        conn.isolation_level = None
        c = conn.cursor()
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
        conn.close()
        if current_db_version < authdb_version:
            self._Upgrade(current_db_version)

    def HttpToken():
        pass

    def _Upgrade(self,current_db_version):

        # connect to DB handle
        conn = sqlite3.connect(self._dbpath)
        conn.isolation_level = None
        c = conn.cursor()

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
            c.execute('SELECT * FROM __temp_upgrade')
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
            c.execute('SELECT * FROM __temp_upgrade')
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
        if current_db_version < 2017090101:
            c.execute('CREATE TABLE cron (cron_id TEXT PRIMARY KEY NOT NULL, cron_minute TEXT, cron_hour TEXT, cron_mday TEXT, cron_month TEXT, cron_wday TEXT, cron_command TEXT, cron_args TEXT)')
            c.execute('CREATE TABLE at (at_id TEXT PRIMARY KEY NOT NULL, at_time TEXT, at_command TEXT, at_args TEXT)')
            c.execute('PRAGMA user_version = 2017090101')
            current_db_version = 2017090101

        # End of upgrades, run an optimize and vacuum too
        c.execute('PRAGMA optimize')
        c.execute('VACUUM')
        conn.close()

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
    conn.close()

