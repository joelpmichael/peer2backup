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

import getpass
if not master_key_id:
    print("Creating new Master Key")
    master_password = keypw.SessionEncrypt(getpass.getpass(prompt='New Master Key Password: '))
    master_key_id = keydb.New(None, bits=4096, password=keypw.SessionDecrypt(master_password), expiry="+30 years")
    configdb.Set('keydb.master.id',str(master_key_id))
else:
    master_password = keypw.SessionEncrypt(getpass.getpass(prompt='Enter Master Key Password: '))

node_key_id = configdb.Get('keydb.node.id',None)
if not node_key_id:
    print("Creating new Node Key")
    node_password = keypw.SessionEncrypt(keypw.New())
    node_key_id = keydb.New(master_key_id, password=keypw.SessionDecrypt(node_password))
    configdb.Set('keydb.node.id',str(node_key_id))
else:
    node_password = keypw.SessionEncrypt(keydb.Decrypt(master_key_id,keypw.SessionDecrypt(master_password),keydb.KeyPassword(node_key_id)))

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
