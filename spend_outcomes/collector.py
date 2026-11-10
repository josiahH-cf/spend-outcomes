"""Bounded, loopback-only OTLP/HTTP JSON receiver. No access or request logging."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import socket
import sqlite3
import threading
import time


MAX_BODY = 1024 * 1024


def make_server(store, host='127.0.0.1', port=4318, lifecycle=None):
    if host not in ('127.0.0.1', '::1'):
        raise ValueError('collector must bind a literal loopback address')

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(5)

        def log_message(self, *args):
            pass

        def reply(self, status, body):
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(data)

        def reject_post(self, status, body):
            # Closing with unread request bytes can reset TCP on Windows before
            # the peer receives our error. Drain only a bounded, unambiguous raw
            # body. Never parse, decompress, log, or retain rejected content.
            lengths = self.headers.get_all('Content-Length') or []
            if (len(lengths) == 1 and lengths[0].isascii() and lengths[0].isdecimal()
                    and len(lengths[0]) <= 10 and not self.headers.get('Transfer-Encoding')):
                size = int(lengths[0])
                if 0 <= size <= MAX_BODY:
                    deadline = time.monotonic() + 5
                    try:
                        while size:
                            remaining = deadline - time.monotonic()
                            if remaining <= 0:
                                break
                            self.connection.settimeout(remaining)
                            chunk = self.rfile.read1(min(size, 65536))
                            if not chunk:
                                break
                            size -= len(chunk)
                    except (OSError, TimeoutError):
                        pass
                    finally:
                        self.connection.settimeout(5)
            return self.reply(status, body)

        def do_POST(self):
            if self.path != '/v1/metrics':
                return self.reject_post(404, {'error': 'metrics endpoint only'})
            if (self.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json'
                    or self.headers.get('Content-Encoding') or self.headers.get('Transfer-Encoding')
                    or self.headers.get('Origin')):
                return self.reject_post(415, {'error': 'plain OTLP JSON metrics only'})
            try:
                lengths = self.headers.get_all('Content-Length') or []
                if len(lengths) != 1:
                    raise ValueError('one content length required')
                size = int(lengths[0])
                if not 0 < size <= MAX_BODY:
                    return self.reply(413, {'error': 'metrics request too large'})
                body = self.rfile.read(size)
                if len(body) != size:
                    raise ValueError('incomplete body')
                store.ingest(json.loads(body))
            except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError):
                return self.reply(400, {'error': 'invalid or unsupported metrics'})
            except (OSError, TimeoutError, sqlite3.Error):
                return self.reply(503, {'error': 'collector unavailable'})
            return self.reply(200, {})

        def do_GET(self):
            if self.path != '/health' or self.headers.get('Origin'):
                return self.reply(404, {'error': 'endpoint unavailable'})
            return self.reply(200, lifecycle.health() if lifecycle else {
                'service': 'cherry-meter', 'status': 'listening',
                'meaning': 'synthetic receiver; lifecycle tracking not configured'})

    class Server(ThreadingHTTPServer):
        daemon_threads = True
        request_queue_size = 8
        address_family = socket.AF_INET6 if host == '::1' else socket.AF_INET

        def __init__(self, *args, **kwargs):
            self.slots = threading.BoundedSemaphore(8)
            super().__init__(*args, **kwargs)

        def process_request(self, request, client_address):
            if not self.slots.acquire(blocking=False):
                self.shutdown_request(request)
                return
            try:
                super().process_request(request, client_address)
            except BaseException:
                self.slots.release()
                raise

        def process_request_thread(self, request, client_address):
            try:
                super().process_request_thread(request, client_address)
            finally:
                self.slots.release()

        def service_actions(self):
            if lifecycle is not None:
                lifecycle.heartbeat()

    return Server((host, port), Handler)
