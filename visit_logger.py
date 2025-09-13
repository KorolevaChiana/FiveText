import http.server
import socketserver
import logging

LOG_FILE = "visits.log"
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(message)s")

class LoggingHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        logging.info("%s - - [%s] %s" % (self.client_address[0], self.log_date_time_string(), format % args))

if __name__ == "__main__":
    with socketserver.TCPServer(("0.0.0.0", 8000), LoggingHandler) as httpd:
        print("Serving on port 8000")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
