import os
import sys
import http.server
import socketserver

DIST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist")
PORT = 5173

class SPAHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIST_DIR, **kwargs)

    def do_GET(self):
        # If the requested file doesn't exist on disk, serve index.html for SPA routing
        local_path = self.translate_path(self.path)
        if not os.path.exists(local_path) or (os.path.isdir(local_path) and not os.path.exists(os.path.join(local_path, "index.html"))):
            self.path = "/index.html"
        return super().do_GET()

def main():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), SPAHandler) as httpd:
        print(f"Enterprise GreenCode Frontend serving at http://localhost:{PORT}")
        httpd.serve_forever()

if __name__ == "__main__":
    main()
