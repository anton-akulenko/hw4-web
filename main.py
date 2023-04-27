import socket
import logging
import mimetypes
import json
import datetime
import pathlib

from urllib.parse import urlparse, unquote_plus
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread


HOME_DIR = pathlib.Path()
SOCKET_UDP_IP = "127.0.0.1"
DOCKER_IP = "0.0.0.0"
SOCKET_UDP_PORT = 5000
HTTP_PORT = 3000
PACKAGE_SIZE = 1024


class HttpHandler(BaseHTTPRequestHandler):

    def do_POST(self):

        data = self.rfile.read(int(self.headers["Content-Length"]))
        send_to_socket(data)
        self.send_response(302)
        self.send_header("Location", "/")
        self.end_headers()

    def do_GET(self):

        pr_url = urlparse(self.path)
        if pr_url.path == "/":
            self.send_html("index.html")
        elif pr_url.path == "/message":
            self.send_html("message.html")
        else:
            if pathlib.Path().joinpath(pr_url.path[1:]).exists():
                self.send_static()
            else:
                self.send_html("error.html", 404)

    def send_html(self, filename, status=200):

        self.send_response(status)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        with open(filename, "rb") as fd:
            self.wfile.write(fd.read())

    def send_static(self, status_code=200):

        self.send_response(status_code)
        mime_type = mimetypes.guess_type(self.path)
        if mime_type:
            self.send_header("Content-Type", mime_type)
        else:
            self.send_header("Content-Type", "text/plain")
        self.end_headers()
        with open(f".{self.path}", "rb") as f:
            self.wfile.write(f.read())


def send_to_socket(data):

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(data, (SOCKET_UDP_IP, SOCKET_UDP_PORT))
    sock.close()


def save_from_http_server(data_to_be_saved):

    clean_message = parse_data(data_to_be_saved)

    try:
        with open(TARGET_FILE, "r", encoding="utf-8") as f:
            all_records = json.load(f)
            new_record = {str(datetime.datetime.now()): clean_message}
            all_records.update(new_record)
            with open(TARGET_FILE, "w", encoding="utf-8") as file:
                json.dump(all_records, file, ensure_ascii=False, indent=4)

    except ValueError as err:
        logging.debug(f"for data {clean_message} error: {err}")
    except OSError as err:
        logging.debug(f"Write data {clean_message} error: {err}")


def parse_data(data):

    raw_data = unquote_plus(data.decode())
    data = {key: value for key, value in [
        param.split("=") for param in raw_data.split("&")]}

    return data


def run_socket_server(ip, port):

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server = ip, port
    logging.warning("/\nSocket server started.")
    sock.bind(server)
    try:
        while True:
            received, address = sock.recvfrom(PACKAGE_SIZE)
            save_from_http_server(received)
            logging.info(f"Received data: {received.decode()} from: {address}")
    except KeyboardInterrupt:
        print(f"Destroy server")
    finally:
        sock.close()


def run_http_server():

    host_addr = ('127.0.0.1', HTTP_PORT)  # for Docker use DOCKER_IP
    http_server = HTTPServer(host_addr, HttpHandler)
    logging.warning("/\nHTTP server started.")

    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        logging.warning("HTTP server is not running")
    finally:
        http_server.server_close()


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG,
                        format="%(threadName)s %(message)s -- [%(asctime)s]")

    FOLDER_TO_SAVE = pathlib.Path().joinpath("storage")
    TARGET_FILE = FOLDER_TO_SAVE.joinpath("data.json")
    if not TARGET_FILE.exists():
        with open(TARGET_FILE, "w", encoding="utf-8") as fd:
            json.dump({}, fd, ensure_ascii=False, indent=4)

    th_server = Thread(target=run_http_server)
    th_server.start()

    th_socket = Thread(target=run_socket_server,
                       args=(SOCKET_UDP_IP, SOCKET_UDP_PORT))
    th_socket.start()
