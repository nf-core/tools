import datetime
import json
import logging
import random
import shelve
import threading
import urllib.parse as urlparse
from http import HTTPStatus
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Dict
from urllib.parse import parse_qsl

from nf_core.utils import NFCORE_CACHE_DIR

# Global lock for shelve access
shelve_lock = threading.Lock()

log = logging.getLogger(__name__)


def parse_qsld(query: str) -> Dict:
    return dict(parse_qsl(query))


class MyHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory="web-gui", **kwargs)

    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "http://localhost:4321")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-Type, Accept, message")

    def do_OPTIONS(self):  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_cors_headers()
        self.end_headers()

    def _send_response(self, status_code: int, body: Dict) -> None:
        self.send_response(status_code)
        self.send_header("Content-type", "application/json")
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def do_POST(self) -> None:  # noqa: N802
        log.debug("POST request received")
        content_type = self.headers.get("Content-Type")
        content_length = int(str(self.headers.get("Content-Length")))
        post_data = self.rfile.read(content_length)
        if urlparse.urlparse(self.path).path == "/process-schema":
            if content_type == "application/json":
                data = json.loads(post_data.decode())
                key = parse_qsld(urlparse.urlparse(self.path).query).get("id", None)
                with shelve_lock:
                    with shelve.open("nf-core") as db:
                        db[key] = data

            else:
                data = parse_qsld(post_data.decode())

                data["schema"] = json.loads(data.get("schema", None))
                key = "schema_" + datetime.date.today().strftime("%Y-%m-%d") + "_" + str(random.randint(0, 1000))
                # write data to local cache
                with shelve_lock:
                    with shelve.open("nf-core") as db:
                        db[key] = data
            status = data.get("status", "received")
            if status == "waiting_for_user":
                status = "received"
            self._send_response(
                200,
                {
                    "message": "Data stored successfully",
                    "status": status,
                    "key": key,
                    "web_url": "http://localhost:8000/schema_builder.html?id=" + key,
                    "api_url": "http://localhost:8000/process-schema?id=" + key,
                },
            )
        else:
            self._send_response(404, {"error": "Not Found"})

    def do_GET(self):  # noqa: N802
        parsed = urlparse.urlparse(self.path)
        key: str | None = parse_qsld(parsed.query).get("id", None)
        if parsed.path == "/process-schema":
            if key is None:
                self._send_response(400, {"error": "Bad Request"})
                return

            with shelve_lock:
                with shelve.open("nf-core") as db:
                    data = db.get(key, None)

            if data is None:
                self._send_response(404, {"error": "Not Found"})
            else:
                self._send_response(200, {"message": "GET request received", "status": data["status"], "data": data})
        else:
            super().do_GET()


def run(
    server_class=HTTPServer,
    handler_class=MyHandler,
):
    global server_instance

    server_address = ("localhost", 8000)
    log.info(f"Starting server on http://{server_address[0]}:{server_address[1]}")
    server_instance = server_class(server_address, handler_class)
    Path(NFCORE_CACHE_DIR / "schema").mkdir(parents=True, exist_ok=True)

    try:
        server_instance.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        log.info("Server loop stopped")


def start_server():
    server_thread = threading.Thread(target=run, daemon=True)
    server_thread.start()
    return server_thread


def stop_server():
    global server_instance

    if server_instance:
        log.info("Stopping server...")
        server_instance.shutdown()
        server_instance.server_close()
        server_instance = None
        log.info("Server stopped")
    else:
        log.warning("No server instance to stop")
