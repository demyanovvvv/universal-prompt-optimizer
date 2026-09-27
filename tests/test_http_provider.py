import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from evals.http_provider import openai_compatible_provider


class HttpProviderTests(unittest.TestCase):
    def test_openai_compatible_provider_rejects_cross_origin_redirects(self):
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                self.send_response(302)
                self.send_header("Location", "http://other.example.test/collect")
                self.end_headers()

            def log_message(self, *args):
                return

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with self.assertRaisesRegex(RuntimeError, "redirect"):
                openai_compatible_provider(
                    f"http://127.0.0.1:{server.server_port}/chat",
                    "test-key",
                    {"model": "mock", "request": "hello"},
                    max_retries=0,
                )
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
    def test_openai_compatible_provider_rejects_non_local_http_endpoint(self):
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            openai_compatible_provider(
                "http://provider.example.test/chat",
                "test-key",
                {"model": "mock", "request": "hello"},
            )

    def test_openai_compatible_provider_rejects_non_finite_retry_configuration(self):
        with self.assertRaisesRegex(ValueError, "finite"):
            openai_compatible_provider(
                "https://provider.example.test/chat",
                "test-key",
                {"model": "mock", "request": "hello"},
                retry_backoff=float("inf"),
            )

    def test_openai_compatible_provider_retries_transient_http_failure(self):
        attempts = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                attempts.append(1)
                if len(attempts) == 1:
                    self.send_response(503)
                    self.send_header("Content-Length", "0")
                    self.send_header("Connection", "close")
                    self.end_headers()
                    return
                response = {"choices": [{"message": {"content": "recovered"}}]}
                encoded = json.dumps(response).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            def log_message(self, *args):
                return

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            result = openai_compatible_provider(
                f"http://127.0.0.1:{server.server_port}/chat",
                "test-key",
                {"model": "mock", "request": "hello"},
                max_retries=1,
                retry_backoff=0,
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

        self.assertEqual(len(attempts), 2)
        self.assertEqual(result["response"]["text"], "recovered")

    def test_openai_compatible_provider_does_not_retry_permanent_http_failure(self):
        attempts = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                attempts.append(1)
                self.send_response(400)
                self.end_headers()

            def log_message(self, *args):
                return

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with self.assertRaisesRegex(RuntimeError, "HTTP 400"):
                openai_compatible_provider(
                    f"http://127.0.0.1:{server.server_port}/chat",
                    "test-key",
                    {"model": "mock", "request": "hello"},
                    max_retries=3,
                    retry_backoff=0,
                )
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

        self.assertEqual(len(attempts), 1)

    def test_openai_compatible_provider_sends_bounded_json_request(self):
        received = {}

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                received["authorization"] = self.headers.get("Authorization")
                length = int(self.headers["Content-Length"])
                received["body"] = json.loads(self.rfile.read(length))
                response = {"choices": [{"message": {"content": "answer"}}], "usage": {"prompt_tokens": 3, "completion_tokens": 2}}
                encoded = json.dumps(response).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            def log_message(self, *args):
                return

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            result = openai_compatible_provider(
                f"http://127.0.0.1:{server.server_port}/v1/chat/completions",
                "test-key",
                {"model": "mock", "request": "hello"},
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

        self.assertEqual(received["authorization"], "Bearer test-key")
        self.assertEqual(received["body"]["messages"][0]["content"], "hello")
        self.assertEqual(result, {"response": {"text": "answer"}, "metrics": {"inputTokens": 3, "outputTokens": 2}})
