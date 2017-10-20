#!/usr/bin/env python3
# -*- coding: utf_8 -*-
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4


# FIFO queue server for peer2backup
# JSON HTTP server for enqueue
# spawning process server for dequeue

import sys
import os
import threading
import multiprocessing
import queue
import json

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
configdb_path = config.ConfigFile(args.config)
configdb = config.ConfigDb(configdb_path)
http_port = configdb.Get('http.server.port',9336)
num_worker_threads = configdb.Get('worker.threads.count',multiprocessing.cpu_count())

import key
keydb_path = configdb.Get('keydb.path',os.path.join(sys.path[0],'keydb.sqlite'))
keydb = key.KeyDb(keydb_path)

import auth
authdb_path = configdb.Get('authdb.path',os.path.join(sys.path[0],'authdb.sqlite'))
authdb = auth.AuthDb(authdb_path)

def _CreateWorkerQueueKey(self):
    keychars = list('~!@#$%^&*()_+1234567890-=QWERTYUIOP{}|qwertyuiop[]\\ASDFGHJKL:"asdfghjkl;\'ZXCVBNM<>?zxcvbnm,./ ') # typable ASCII characters
    new_key = []
    for i in range(16):
        new_key.append(random.choice(keychars)) # key just needs to be unique, isn't being used for auth
    key = ''.join(new_key)
    found_in_queue=0
    with worker_queue_lock:
        if key in worker_queue:
            found_in_queue=1
    if found_in_queue:
        return _CreateWorkerQueueKey() # self-recurse to generate a new key if one exists
    else:
        return key

# set up work queue
queue = queue.Queue()
worker_queue_lock = threading.Lock()
worker_queue = {}
worker_status_lock = threading.Lock()
worker_status = {}

# set up worker threads
def _Worker():
    # initial thread startup
    with worker_status_lock:
        worker_status[threading.current_thread().ident] = None

    # thread main loop
    while True:

        # dequeue item
        item = queue.get()
        queue_item = []

        # update worker status with item
        with worker_status_lock:
            worker_status[threading.current_thread().ident] = item

        # grab item from queue
        with worker_queue_lock:
            queue_item = worker_queue[item]

        # run item - item[0] is a bound method, item[1:] are its arguments
        queue_item[0](*queue_item[1:])

        # update worker status to idle
        with worker_status_lock:
            worker_status[threading.current_thread().ident] = None

        # delete item from queue
        with worker_queue_lock:
            del worker_queue[item]

        queue.task_done()

# start worker threads
for i in range(num_worker_threads):
    t = threading.Thread(target=_Worker)
    t.daemon = True
    t.start()

def http_status(data):
    # status handler
    # for now, just prints status, prints out data arguments, and says 200 ok
    print('status')
    print(data)
    return 200, None


# dictionary of URL: function mapping
# used by HTTP RequestHandler to determine valid paths
# used by Cron to run scheduled jobs
request_dictionary = {
    '/status': http_status,
    '/key/import': keydb.HttpImport,
    '/key/export': keydb.HttpExport,
    '/auth/token': authdb.HttpToken,
}

import scheduler
# set up scheduled task queuing thread
def _Cron():
    scheddb_path = configdb.Get('scheddb.path',os.path.join(sys.path[0],'scheddb.sqlite'))
    sched = scheduler.Scheduler(scheddb_path)
    while True:
        sched.Sleep()
        for job,data in sched.Tasks():
            code, response = request_dictionary[job](data)

# start scheduled task queuing thread
t = threading.Thread(target=_Cron)
t.daemon = True
t.start()

import socket
from socketserver import ThreadingMixIn
from http.server import SimpleHTTPRequestHandler, HTTPServer

class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
    pass

class RequestHandler(SimpleHTTPRequestHandler):
    # handler for HTTP server
    def _handle_request(self,data):

        request_path = self.path
        self.send_header('Content-Type', 'application/json') # we only speak JSON here

        # check that we know how to handle the requested URL
        if request_path not in request_dictionary.keys():
            self.send_response(404)
            self.end_headers()
            return

        code, response = request_dictionary[request_path](data)
        self.send_response(code)
        self.end_headers()
        self.wfile.write(json.dumps(response).encode('utf-8'))


    def do_POST(self):
        data_string = self.rfile.read(int(self.headers['Content-Length']))
        self._handle_request(json.loads(data_string.decode('utf-8')))
        return

    def do_GET(self):
        self._handle_request(None)
        return

    def do_HEAD(self):
        # we don't do head...
        self.send_response(405)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        return

server = ThreadingSimpleServer(('', http_port), RequestHandler)

addr, port = server.server_address
print("Serving HTTP on %s port %d ..." % (addr, port))

try:
    while 1:
        sys.stdout.flush()
        server.handle_request()
except KeyboardInterrupt:
    print("Finished")
