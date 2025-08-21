# backend/mcp/oauth_callback.py
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse as urlparse

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        q = urlparse.urlparse(self.path).query
        params = urlparse.parse_qs(q)
        code = params.get("code", [""])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(f"Code alındı. Terminale kopyalayın:\n{code}".encode("utf-8"))
        print("\n🔑 OAuth CODE:", code, "\n")

def run():
    server = HTTPServer(("localhost", 8081), Handler)
    print("🌐 OAuth callback server http://localhost:8081/oauth2callback")
    server.serve_forever()

if __name__ == "__main__":
    run()
