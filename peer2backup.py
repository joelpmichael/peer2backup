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
                    type=argparse.FileType('r+'),
                    help='Configuration File',
                   )
args = parser.parse_args()

import config
configdb = config.db(config.file(args.config))
