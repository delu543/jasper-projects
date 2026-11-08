#!/usr/bin/env python3
"""Loopback-only Mihomo hot-reload regression; never controls the installed core.

Two existing CONNECT streams must survive a force=false config reload with
the same connection IDs. This tests continuity, not real client isolation.
"""
import argparse
import json
from pathlib import Path
import socket
import socketserver
import subprocess
import tempfile
import threading
import time
import urllib.request

from integration import freeport


class Echo(socketserver.BaseRequestHandler):
    def handle(self):
        while True:
            data = self.request.recv(4096)
            if not data:
                return
            self.request.sendall(data)


class EchoServer(socketserver.ThreadingTCPServer):
    daemon_threads = True


def connect(port, target):
    sock = socket.create_connection(('127.0.0.1', port), timeout=5)
    try:
        sock.sendall(f'CONNECT 127.0.0.1:{target} HTTP/1.1\r\nHost: 127.0.0.1:{target}\r\n\r\n'.encode())
        header = b''
        while not header.endswith(b'\r\n\r\n') and len(header) < 8192:
            part = sock.recv(1)
            if not part:
                break
            header += part
        assert b' 200 ' in header.split(b'\r\n')[0], header
        return sock
    except BaseException:
        sock.close()
        raise


def roundtrip(sock, data):
    sock.sendall(data)
    received = b''
    while len(received) < len(data):
        part = sock.recv(len(data) - len(received))
        assert part, 'existing stream was closed'
        received += part
    assert received == data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mihomo', required=True)
    args = parser.parse_args()
    # Explicitly bypass environment HTTP proxies for our loopback controller.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with EchoServer(('127.0.0.1', 0), Echo) as echo, tempfile.TemporaryDirectory(prefix='network-reload-test-') as tmp:
        threading.Thread(target=echo.serve_forever, daemon=True).start()
        ports = set()
        while len(ports) < 3:
            ports.add(freeport())
        normal, dedicated, control = sorted(ports)
        folder = Path(tmp)
        cfg = {'mode': 'rule', 'mixed-port': normal, 'allow-lan': False,
               'bind-address': '127.0.0.1', 'external-controller': f'127.0.0.1:{control}',
               'tun': {'enable': False}, 'dns': {'enable': False}, 'log-level': 'warning',
               'listeners': [{'name': 'test-only', 'type': 'http', 'listen': '127.0.0.1',
                              'port': dedicated, 'proxy': 'DIRECT'}], 'rules': ['MATCH,DIRECT']}
        path = folder / 'config.json'
        path.write_text(json.dumps(cfg), encoding='utf-8')
        sockets = []
        proc = None
        def api(endpoint, body=None):
            req = urllib.request.Request(f'http://127.0.0.1:{control}{endpoint}',
                data=json.dumps(body).encode() if body is not None else None,
                method='PUT' if body is not None else 'GET', headers={'Content-Type': 'application/json'})
            with opener.open(req, timeout=5) as response:
                raw = response.read()
            return json.loads(raw) if raw else None
        try:
            with (folder / 'core.log').open('w') as log:
                proc = subprocess.Popen([args.mihomo, '-d', tmp, '-f', str(path)], stdout=log, stderr=log)
                deadline = time.monotonic() + 10
                while True:
                    try:
                        api('/version')
                        break
                    except OSError:
                        if proc.poll() is not None or time.monotonic() >= deadline:
                            raise RuntimeError((folder / 'core.log').read_text(encoding='utf-8'))
                        time.sleep(.1)
                for port in (normal, dedicated):
                    sock = connect(port, echo.server_address[1])
                    sockets.append(sock)
                    roundtrip(sock, b'before-reload')
                source_ports = {s.getsockname()[1] for s in sockets}
                def connection_ids():
                    return {c['id'] for c in api('/connections')['connections']
                            if int(c['metadata']['sourcePort']) in source_ports}
                before = connection_ids()
                assert len(before) == 2, 'both held streams must be observable'
                cfg['rules'].insert(0, 'DOMAIN,reload-check.invalid,REJECT')
                path.write_text(json.dumps(cfg), encoding='utf-8')
                api('/configs?force=false', {'path': str(path)})
                assert api('/rules')['rules'][0]['payload'] == 'reload-check.invalid'
                for sock in sockets:
                    roundtrip(sock, b'after-reload')
                assert connection_ids() == before, 'reload replaced held connections'
                assert proc.poll() is None
                print('PASS: force=false loads new rule; both CONNECT streams and IDs survive; no core restart.')
        finally:
            for sock in sockets:
                sock.close()
            if proc is not None and proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=5)
            echo.shutdown()


if __name__ == '__main__':
    main()
