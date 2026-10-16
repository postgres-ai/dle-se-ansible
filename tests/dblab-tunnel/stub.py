"""Stand-ins for the integration test: the Platform's key rpc, a clone, the engine API and an
address outside the pool. The Platform's answer comes from /tmp/stub/state.json at each request."""

import http.server
import json
import socketserver
import sys
import threading

STATE = "/tmp/stub/state.json"


class Platform(http.server.BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        self.rfile.read(int(self.headers.get("Content-Length", "0")))
        with open(STATE, encoding="utf-8") as f:
            state = json.load(f)
        ok = (self.path == "/api/general/rpc/dblab_tunnel_keys_fetch"
              and self.headers.get("access-token") == "box-token")
        status = state["status"] if ok else 401
        body = json.dumps({"keys": state["keys"]} if status == 200 else {"code": "PT%d" % status}).encode()
        with open("/tmp/stub/calls", "a", encoding="utf-8") as f:
            f.write("%d\n" % status)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def banner(text):
    class Handler(socketserver.BaseRequestHandler):
        def handle(self):
            self.request.sendall(text.encode() + b"\n")
            # Hold the connection until the client closes it, so concurrent connections count.
            while self.request.recv(1024):
                pass
    return Handler


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    servers = [
        http.server.ThreadingHTTPServer(("127.0.0.1", 18080), Platform),
        Server(("127.0.0.1", 6000), banner("clone-6000")),
        Server(("127.0.0.1", 6100), banner("clone-6100")),
        Server(("127.0.0.1", 2345), banner("engine-api")),
        Server((sys.argv[1], 7777), banner("outside-pool")),
    ]
    for s in servers:
        threading.Thread(target=s.serve_forever, daemon=True).start()
    threading.Event().wait()


if __name__ == "__main__":
    main()
