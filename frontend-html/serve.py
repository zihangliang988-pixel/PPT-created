"""
PPT 智造 — HTML 版本前端开发服务器
用法：python serve_html.py
服务在 http://localhost:5174
"""

import http.server
import socketserver
import os

PORT = 5174
DIR = os.path.dirname(os.path.abspath(__file__))

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIR, **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Serving at http://localhost:{PORT}")
    print(f"Backend at http://localhost:3000")
    print(f"Open http://localhost:{PORT} in your browser")
    httpd.serve_forever()
