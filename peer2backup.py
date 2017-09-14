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

# set up work queue
work_queue = queue.Queue()

# set up worker threads
def worker():
    while True:
        item = work_queue.get()
        do_work(item)
        work_queue.task_done()

for i in range(num_worker_threads):
    t = threading.Thread(target=worker)
    t.start()
    threads.append(t)

import socket
from socketserver import ThreadingMixIn
from http.server import SimpleHTTPRequestHandler, HTTPServer

class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
    pass

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