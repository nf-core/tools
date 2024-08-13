import concurrent.futures
import json
import shelve
import urllib.parse as urlparse
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs


class MyHandler(BaseHTTPRequestHandler):
    def _send_response(self, status_code, body):
        self.send_response(status_code)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def do_POST(self):
        print("POST request received")
        content_type = self.headers.get("Content-Type")
        content_length = int(self.headers.get("Content-Length"))
        post_data = self.rfile.read(content_length)
        if content_type == "application/json":
            data = json.loads(post_data.decode())
        else:
            parsed = urlparse.urlparse(post_data.decode())
            data = parse_qs(parsed.query)
            data["schema"] = json.loads(data.get("schema", [None])[0])

        with shelve.open("mydatabase") as db:
            db["data"] = data

        self._send_response(200, {"message": "Data stored successfully"})

    def do_GET(self):
        print("GET request received")
        print(self.path)
        parsed = urlparse.urlparse(self.path)
        id = parse_qs(parsed.query).get("id", [None])[0]
        if id is None:
            self._send_response(400, {"error": "Bad Request"})
            return

        with shelve.open("mydatabase") as db:
            data = db.get("data", None)

        if data is None:
            self._send_response(404, {"error": "Not Found"})
        else:
            self._send_response(200, {"message": "GET request received", "data": data})


def run(server_class=HTTPServer, handler_class=MyHandler):
    server_address = ("http://localhost:8000", 8888)
    httpd = server_class(server_address, handler_class)
    httpd.serve_forever()


def start_server():
    executor = concurrent.futures.ThreadPoolExecutor()
    executor.submit(run)
    executor.shutdown(wait=False)
    print("Server started")


if __name__ == "__main__":
    run()
