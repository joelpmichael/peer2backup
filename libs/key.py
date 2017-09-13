# -*- coding: utf_8 -*-

# Crypto Key Database

import os
import sqlite3
import shutil

import uuid
import random
import base64

import Crypto.PublicKey.RSA
import Crypto.Random.random
import Crypto.Cipher.PKCS1_OAEP
import Crypto.Hash.SHA256

# increment ConfigDbVersion on DB schema changes
keydb_version = 2017090101

# main key db
class KeyDb:
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
        if current_db_version < keydb_version:
            self._Upgrade(current_db_version)

    def New(self,parent_key_id=None,bits=2048,password=None,expiry='+2 years'):
        c = self._conn.cursor()
        new_uuid = str(uuid.uuid4())
        key_priv = Crypto.PublicKey.RSA.generate(bits)
        key_pub = key_priv.publickey()
        store_password = None
        if parent_key_id:
            store_password = base64.standard_b64encode(self.Encrypt(parent_key_id,password))

        c.execute('DELETE FROM pubkey WHERE key_id=?', (new_uuid,))
        c.execute('DELETE FROM privkey WHERE key_id=?', (new_uuid,))
        c.execute('INSERT INTO pubkey (key_id, key_expiry, key) \
                VALUES (?, datetime(\'now\', ?), ?)',
                (new_uuid, expiry, key_pub.exportKey(),)
                )
        c.execute('INSERT INTO privkey (key_id, key_unlock_key_id, key_unlock_password, key) \
                VALUES (?, ?, ?, ?)',
                (new_uuid, parent_key_id, store_password, key_priv.exportKey(passphrase=password),)
                )

        return new_uuid
    
    def Del(self,key_id):
        pass

    def Check(self,key_id):
        pass

    def ImportPubkey(self,key_id,key):
        pass

    def ExportPubkey(self,key_id):
        pass

    def Encrypt(self,key_id,data):
        # RSA PubKey Encryption of data

        # fetch public key
        c = self._conn.cursor()
        c.execute('SELECT key FROM pubkey WHERE key_id = ? AND key_expiry > datetime(\'now\')', (key_id,))
        row = c.fetchone()
        key_pub = None
        if not row:
            raise ValueError("Key not found in database")

        # create RSA key object
        key_pub = Crypto.PublicKey.RSA.importKey(row[0])

        # RSA encryption
        cipher = Crypto.Cipher.PKCS1_OAEP.new(key_pub, hashAlgo=Crypto.Hash.SHA256)
        message = cipher.encrypt(data.encode('utf-8'))
        return message

    def Decrypt(self,key_id,password,data):
        # RSA PubKey Decryption of data

        # fetch public key
        c = self._conn.cursor()
        c.execute('SELECT key FROM privkey WHERE key_id = ?', (key_id,))
        row = c.fetchone()
        key_priv = None
        if not row:
            raise ValueError("Key not found in database")

        # create RSA key object
        key = row[0]
        key_priv = Crypto.PublicKey.RSA.importKey(key,passphrase=password)
        if not key_priv:
            raise ValueError("Key could not be loaded, bad password?")

        # RSA encryption
        cipher = Crypto.Cipher.PKCS1_OAEP.new(key_priv, hashAlgo=Crypto.Hash.SHA256)
        message = cipher.decrypt(data)
        return message.decode('utf-8')

    def Sign(self,key_id,password,data):
        pass

    def Verify(self,key_id,data):
        pass

    def KeyPassword(self,key_id):
        # return the password stored in the db for the key (should be encrypted)
        c = self._conn.cursor()
        c.execute('SELECT key_unlock_password FROM privkey WHERE key_id = ?', (key_id,))
        row = c.fetchone()
        if not row:
            return None
        else:
            return base64.standard_b64decode(row[0])

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
        # simple key,value table
        if current_db_version < 2017090101:
            c.execute('CREATE TABLE privkey (key_id TEXT PRIMARY KEY NOT NULL, key TEXT, key_unlock_key_id TEXT, key_unlock_password TEXT)')
            c.execute('CREATE TABLE pubkey (key_id TEXT PRIMARY KEY NOT NULL, key TEXT, key_expiry TEXT)')
            c.execute('PRAGMA user_version = 2017090101')
            current_db_version = 2017090101

        # End of upgrades, run an optimize and vacuum too
        c.execute('PRAGMA optimize')
        c.execute('VACUUM')

# in-memory password storage scrambling function for key passwords
class KeyPw:
    def __init__(self):
        # possible characters for randomly-generated passwords (typable ASCII)
        self.pwchars = list('! #$%&()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[]^_`abcdefghijklmnopqrstuvwxyz{|}~')

        # create RSA key pair to use during this session to encrypt key passwords
        self._session_key_priv = Crypto.PublicKey.RSA.generate(1024)
        self._session_key_pub = self._session_key_priv.publickey()

    def New(self,length=32):
        # generate password of length (default 32) characters from list in self.pwchars
        # max length is 128 characters (1024 bits in session RSA key)
        maxbytes = self._session_key_priv.size() / 8
        if length > maxbytes:
            raise ValueError("Length must not be larger than RSA key size")

        new_password = []
        for i in range(length):
            new_password.append(Crypto.Random.random.choice(self.pwchars))
        newpw = ''.join(new_password)
        return newpw

    def SessionEncrypt(self,plainpw):
        cipher = Crypto.Cipher.PKCS1_OAEP.new(self._session_key_pub, hashAlgo=Crypto.Hash.SHA256)
        message = cipher.encrypt(plainpw.encode('utf-8'))
        return message

    def SessionDecrypt(self,encpw):
        cipher = Crypto.Cipher.PKCS1_OAEP.new(self._session_key_priv, hashAlgo=Crypto.Hash.SHA256)
        message = cipher.decrypt(encpw)
        return message.decode('utf-8')

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
