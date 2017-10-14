#!/usr/bin/env python3
# -*- coding: utf_8 -*-

# FIFO queue server for peer2backup
# JSON HTTP server for enqueue
# spawning process server for dequeue

import sys
import os
import threading
import multiprocessing
import queue

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
http_port = config.ConfigDb(configdb_path).Get('http.server.port',9336)
num_worker_threads = config.ConfigDb(configdb_path).Get('worker.threads.count',multiprocessing.cpu_count())

def _CreateWorkerQueueKey(self):
    keychars = list('! #$%&()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[]^_`abcdefghijklmnopqrstuvwxyz{|}~')
    new_key = []
    for i in range(16):
        new_key.append(random.choice(keychars))
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

# start threads
for i in range(num_worker_threads):
    t = threading.Thread(target=_Worker)
    t.daemon = True
    t.start()

# set up scheduled task queuing thread
def _Cron():
    while True:
        pass

# start scheduled task queuing thread
t = threading.Thread(target=_Cron)
t.daemon = True
t.start()

import socket
from socketserver import ThreadingMixIn
from http.server import SimpleHTTPRequestHandler, HTTPServer

class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
    pass

def status():
    pass

request_dictionary = {
    '/status': status,
}

class RequestHandler(SimpleHTTPRequestHandler):
    # handler for HTTP server
    def _handle_request(self):
        print('handle it!')
        request_path = self.path
        self.send_response(404)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        return

    def do_POST(self):
        self._handle_request()
        return

    def do_GET(self):
        self._handle_request()
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
