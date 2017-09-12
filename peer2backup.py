#!/usr/bin/env python3
# -*- coding: utf_8 -*-

import sys
import os

# add ./libs/ to module path
sys.path.append(os.path.join(sys.path[0],'libs'))

# handle arguments
import argparse
parser = argparse.ArgumentParser(description='peer2backup background service')
parser.add_argument('-c', '--config',
                   default=os.path.join(sys.path[0],'peer2backup.ini'),
                   help='Configuration File',
                   )
args = parser.parse_args()

# load configuration
import config
configdb_path = config.File(args.config)
configdb = config.ConfigDb(configdb_path)

import key
keydb_path = configdb.Get('keydb.path',os.path.join(sys.path[0],'keydb.sqlite'))
keydb = key.KeyDb(keydb_path)

keypw = key.KeyPw()

master_key_id = configdb.Get('keydb.master.id',None)

if not master_key_id:
    master_key_id = keydb.New(None, bits=4096, password=None, expiry="+30 years")
    configdb.Set('keydb.master.id',str(master_key_id))

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
