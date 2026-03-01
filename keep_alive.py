from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
import os

class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot do Agente Crypto esta rodando e ouvindo o Telegram!")

    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()

    def log_message(self, format, *args):
        # Desativa os logs de acesso para não poluir o console
        pass

def run_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), RequestHandler)
    server.serve_forever()

def keep_alive():
    """Inicia um servidor web fásico em uma thread separada para enganar o Render."""
    t = Thread(target=run_server)
    t.daemon = True
    t.start()
