#!/usr/bin/env python3
"""Local OpenAI-compatible stub endpoint for the failover drill.
--die-after 0: accept no connections usefully (bind then close listener =
connection refused, the saturation stand-in for this drill)."""
import json, sys
from http.server import BaseHTTPRequestHandler, HTTPServer

die = len(sys.argv) > 3 and sys.argv[3] == '0'

class H(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.dumps({'choices': [{'message': {'content': 'stub-answer'}}]}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *a):
        pass

srv = HTTPServer(('127.0.0.1', int(sys.argv[1])), H)
if die:
    srv.socket.close()  # listener dead: connections refused, like a saturated route
    import time; time.sleep(30)
else:
    srv.serve_forever()
