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
configdb_path = config.file(args.config)
configdb = config.db(configdb_path)

import key
keydb_path = configdb.get('keydb.path',os.path.join(sys.path[0],'configdb.sqlite'))

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
