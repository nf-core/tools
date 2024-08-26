import json
import logging
import threading
import urllib.parse as urlparse
from http import HTTPStatus
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Dict
from urllib.parse import parse_qsl

import nf_core

log: logging.Logger = logging.getLogger(__name__)


def parse_qsld(query: str) -> Dict:
    return dict(parse_qsl(query))


class MyHandler(SimpleHTTPRequestHandler):
    status = "waiting_for_user"  # Default status

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(Path(nf_core.__file__).parent / "web-gui"), **kwargs)

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
                schema_path = data.get("schema_path", None)
                # write data to local schema_file
                open(schema_path, "w").write(json.dumps(data["schema"], indent=4))

            else:
                data = parse_qsld(post_data.decode())

                data["schema"] = json.loads(data.get("schema", None))
                schema_path = data.get("schema_path", None)
                # write data to local schema_file
                open(schema_path, "w").write(json.dumps(data["schema"], indent=4))
            status = data.get("status", "received")
            MyHandler.status = status
            if status == "waiting_for_user":
                status = "received"

            self._send_response(
                200,
                {
                    "message": "Data stored successfully",
                    "status": status,
                    "schema_path": schema_path,
                    "web_url": "http://localhost:8000/schema_builder.html?schema_path="
                    + urlparse.quote(schema_path, safe=""),
                    "api_url": "http://localhost:8000/process-schema?schema_path="
                    + urlparse.quote(schema_path, safe=""),
                },
            )
        else:
            self._send_response(404, {"error": "Not Found"})

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse.urlparse(self.path)
        if parsed.path == "/process-schema":
            schema_path: str | None = parse_qsld(parsed.query).get("schema_path", None)
            if schema_path is None:
                self._send_response(422, {"error": "schema_path parameter not found"})

            else:
                with open(schema_path) as file:
                    data = json.load(file)
                if data is None:
                    self._send_response(404, {"error": "Not Found"})
                else:
                    self._send_response(
                        200, {"message": "GET request received", "status": MyHandler.status, "data": data}
                    )
        else:
            super().do_GET()

    def log_message(self, format, *args):
        log.debug(format % args)


def run(
    server_class=HTTPServer,
    handler_class=MyHandler,
):
    global server_instance

    server_address = ("localhost", 8000)
    log.info(f"Starting server on http://{server_address[0]}:{server_address[1]}")
    server_instance = server_class(server_address, handler_class)

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
