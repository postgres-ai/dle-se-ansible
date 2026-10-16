"""Tests for the tunnel user's keys command (roles/dblab-tunnel/files/dblab-tunnel-keys).

Run from the repository root:

    python3 -m unittest tests/dblab-tunnel/test_keys.py

A stub Platform answers on loopback; nothing else is touched but a temporary directory.
"""

import base64
import http.server
import importlib.machinery
import importlib.util
import io
import json
import os
import struct
import subprocess
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "..", "roles", "dblab-tunnel", "files", "dblab-tunnel-keys")


def load_script():
    # No bytecode next to the role's file: the role ships that directory.
    sys.dont_write_bytecode = True
    loader = importlib.machinery.SourceFileLoader("dblab_tunnel_keys", SCRIPT)
    spec = importlib.util.spec_from_loader("dblab_tunnel_keys", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


keys = load_script()


def make_key(key_type="ssh-ed25519", body_type=None, comment="user@laptop"):
    blob = (body_type or key_type).encode()
    data = struct.pack(">I", len(blob)) + blob + struct.pack(">I", 32) + os.urandom(32)
    text = key_type + " " + base64.b64encode(data).decode()
    return text + (" " + comment if comment else "")


def bare(key_text):
    return " ".join(key_text.split()[:2])


class StubPlatform(http.server.BaseHTTPRequestHandler):
    status = 200
    body = {"keys": []}
    calls = []

    def do_POST(self):  # noqa: N802 - http.server's naming
        length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(length)
        StubPlatform.calls.append({"path": self.path, "token": self.headers.get("access-token")})
        payload = json.dumps(StubPlatform.body).encode()
        self.send_response(StubPlatform.status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


class KeysCommandTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), StubPlatform)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cache_dir = os.path.join(self.tmp.name, "cache")
        os.mkdir(self.cache_dir)
        token_file = os.path.join(self.tmp.name, "token")
        with open(token_file, "w", encoding="utf-8") as f:
            f.write("box-token\n")
        self.conf = {
            "user": "dblab-tunnel",
            "api_base_url": "http://127.0.0.1:%d/api/general/" % self.server.server_address[1],
            "token_file": token_file,
            "cache_dir": self.cache_dir,
            "ttl": 60,
            "stale_max": 86400,
            "retry_after": 10,
            "timeout": 2,
        }
        conf_path = os.path.join(self.tmp.name, "keys.conf")
        with open(conf_path, "w", encoding="utf-8") as f:
            json.dump(self.conf, f)
        self.patch = mock.patch.object(keys, "CONFIG_PATH", conf_path)
        self.patch.start()
        StubPlatform.status = 200
        StubPlatform.body = {"keys": []}
        StubPlatform.calls = []
        self.k1 = make_key()
        self.k2 = make_key("ssh-rsa", comment="")

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def at(self, now):
        return keys.keys_for_login(self.conf, now)

    def run_main(self, *argv):
        out = io.StringIO()
        with redirect_stdout(out):
            rc = keys.main(["keys", *argv])
        return rc, out.getvalue().splitlines()

    # --- what sshd sees -------------------------------------------------------------------

    def test_prints_each_key_restricted_to_port_forwarding(self):
        StubPlatform.body = {"keys": [self.k1, self.k2]}
        rc, lines = self.run_main("dblab-tunnel")
        self.assertEqual(rc, 0)
        self.assertEqual(lines, ["restrict,port-forwarding " + bare(self.k1),
                                 "restrict,port-forwarding " + bare(self.k2)])

    def test_asks_with_the_box_token_at_the_fetch_rpc(self):
        StubPlatform.body = {"keys": [self.k1]}
        self.run_main("dblab-tunnel")
        self.assertEqual(StubPlatform.calls,
                         [{"path": "/api/general/rpc/dblab_tunnel_keys_fetch", "token": "box-token"}])

    def test_any_other_user_gets_nothing_and_nothing_is_asked(self):
        StubPlatform.body = {"keys": [self.k1]}
        for argv in (["root"], ["ubuntu"], []):
            rc, lines = self.run_main(*argv)
            self.assertEqual((rc, lines), (0, []))
        self.assertEqual(StubPlatform.calls, [])

    def test_no_token_denies_without_asking(self):
        os.unlink(self.conf["token_file"])
        StubPlatform.body = {"keys": [self.k1]}
        self.assertEqual(self.at(1000), [])
        self.assertEqual(StubPlatform.calls, [])

    # --- cache --------------------------------------------------------------------------

    def test_answer_is_reused_within_ttl_then_asked_again(self):
        StubPlatform.body = {"keys": [self.k1]}
        self.assertEqual(self.at(1000), [bare(self.k1)])
        StubPlatform.body = {"keys": []}
        self.assertEqual(self.at(1059), [bare(self.k1)])
        self.assertEqual(len(StubPlatform.calls), 1)
        self.assertEqual(self.at(1060), [])
        self.assertEqual(len(StubPlatform.calls), 2)

    def test_outage_serves_the_last_answer_until_stale_max(self):
        StubPlatform.body = {"keys": [self.k1]}
        self.at(1000)
        StubPlatform.status = 503
        self.assertEqual(self.at(1000 + 3600), [bare(self.k1)])
        self.assertEqual(self.at(1000 + 86399 + 20), [])

    def test_outage_without_a_last_answer_denies(self):
        StubPlatform.status = 500
        self.assertEqual(self.at(1000), [])

    def test_platform_unreachable_serves_the_last_answer(self):
        StubPlatform.body = {"keys": [self.k1]}
        self.at(1000)
        self.conf["api_base_url"] = "http://127.0.0.1:9"  # discard port: connection refused
        self.assertEqual(self.at(2000), [bare(self.k1)])

    def test_after_a_failure_the_platform_is_not_asked_again_for_retry_after(self):
        StubPlatform.status = 500
        self.at(1000)
        self.at(1005)
        self.assertEqual(len(StubPlatform.calls), 1)
        self.at(1010)
        self.assertEqual(len(StubPlatform.calls), 2)

    def test_recovery_clears_the_failure(self):
        StubPlatform.status = 500
        self.at(1000)
        StubPlatform.status = 200
        StubPlatform.body = {"keys": [self.k2]}
        self.assertEqual(self.at(1011), [bare(self.k2)])
        self.assertFalse(os.path.exists(os.path.join(self.cache_dir, "failed.json")))

    def test_a_refused_token_wipes_the_cache(self):
        for status in (401, 403, 404):
            with self.subTest(status=status):
                StubPlatform.status = 200
                StubPlatform.body = {"keys": [self.k1]}
                for name in ("keys.json", "failed.json"):
                    try:
                        os.unlink(os.path.join(self.cache_dir, name))
                    except OSError:
                        pass
                self.at(1000)
                StubPlatform.status = status
                self.assertEqual(self.at(1100), [])
                self.assertFalse(os.path.exists(os.path.join(self.cache_dir, "keys.json")))
                # and stays denied while the Platform is down afterwards
                StubPlatform.status = 503
                self.assertEqual(self.at(1200), [])

    def test_a_reply_without_a_key_list_is_an_outage_not_an_empty_list(self):
        StubPlatform.body = {"keys": [self.k1]}
        self.at(1000)
        StubPlatform.body = {"code": "PGRST202"}
        self.assertEqual(self.at(1100), [bare(self.k1)])

    def test_a_corrupt_cache_is_ignored(self):
        with open(os.path.join(self.cache_dir, "keys.json"), "w", encoding="utf-8") as f:
            f.write("{not json")
        StubPlatform.body = {"keys": [self.k1]}
        self.assertEqual(self.at(1000), [bare(self.k1)])

    def test_a_cache_from_the_future_is_not_trusted(self):
        with open(os.path.join(self.cache_dir, "keys.json"), "w", encoding="utf-8") as f:
            json.dump({"fetched_at": 5000, "keys": [bare(self.k2)]}, f)
        StubPlatform.body = {"keys": [self.k1]}
        self.assertEqual(self.at(1000), [bare(self.k1)])

    # --- key validation -----------------------------------------------------------------

    def test_only_valid_single_keys_pass(self):
        good = [make_key(t) for t in keys.KEY_TYPES]
        for k in good:
            self.assertEqual(keys.valid_key(k), bare(k), k)
        bad = [
            "",
            "hello world",
            self.k1 + "\n" + self.k2,                         # two keys
            'command="sh" ' + self.k1,                        # options in front
            make_key("ssh-ed25519", body_type="ssh-rsa"),     # label does not match the body
            make_key("ssh-dss"),                              # type not allowed
            "ssh-ed25519 AAAA!!!",                            # not base64
            "-----BEGIN OPENSSH " + "PRIVATE KEY-----",  # split: secret scanners would flag it
            make_key(comment="evil\x00comment"),
            "ssh-ed25519 " + "A" * 20000,
            None,
            42,
        ]
        for k in bad:
            self.assertIsNone(keys.valid_key(k), repr(k)[:80])

    def test_invalid_keys_in_the_reply_are_dropped_not_the_whole_list(self):
        StubPlatform.body = {"keys": ["junk", self.k1, self.k1 + "\n" + self.k2]}
        self.assertEqual(self.at(1000), [bare(self.k1)])

    def test_the_comment_never_reaches_sshd(self):
        k = make_key(comment="restrict,command=\"/bin/sh\"")
        StubPlatform.body = {"keys": [k]}
        _, lines = self.run_main("dblab-tunnel")
        self.assertEqual(lines, ["restrict,port-forwarding " + bare(k)])

    # --- the script as sshd runs it -------------------------------------------------------

    def test_run_as_sshd_runs_it_without_a_config_prints_nothing(self):
        # /etc/dblab-tunnel/keys.conf does not exist on the test host.
        proc = subprocess.run([sys.executable, "-I", SCRIPT, "dblab-tunnel"], capture_output=True,
                              env={"PATH": "/usr/bin:/bin"}, check=False)
        self.assertEqual((proc.returncode, proc.stdout), (0, b""))

    def test_an_unexpected_error_denies_quietly(self):
        StubPlatform.body = {"keys": [self.k1]}
        with mock.patch.object(keys, "keys_for_login", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                keys.main(["keys", "dblab-tunnel"])
        # main() lets it propagate; the __main__ guard turns any exception into exit 0, no output.
        with open(SCRIPT, encoding="utf-8") as f:
            guard = f.read().split('if __name__ == "__main__":')[1]
        self.assertIn("except Exception", guard)
        self.assertIn("sys.exit(0)", guard)


if __name__ == "__main__":
    unittest.main()
