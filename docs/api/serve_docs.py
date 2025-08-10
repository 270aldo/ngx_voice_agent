#!/usr/bin/env python3
"""
Simple HTTP server to serve API documentation locally.

Usage:
    python serve_docs.py

Then open http://localhost:8080/swagger-ui.html in your browser.
"""

import http.server
import socketserver
import os
import sys
from pathlib import Path

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler to set correct MIME types."""
    
    def end_headers(self):
        # Add CORS headers for local development
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def guess_type(self, path):
        """Ensure correct MIME types for API documentation files."""
        mimetype = super().guess_type(path)
        if path.endswith('.yaml') or path.endswith('.yml'):
            return 'application/yaml'
        return mimetype

def serve_documentation(port=8080):
    """Serve API documentation on specified port."""
    # Change to the directory containing this script
    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)
    
    print(f"📚 NGX Voice Sales Agent API Documentation Server")
    print(f"="*60)
    print(f"Serving documentation from: {script_dir}")
    print(f"Server running at: http://localhost:{port}")
    print(f"\nAvailable endpoints:")
    print(f"  - Swagger UI: http://localhost:{port}/swagger-ui.html")
    print(f"  - OpenAPI Spec: http://localhost:{port}/openapi.yaml")
    print(f"  - README: http://localhost:{port}/README.md")
    print(f"\nPress Ctrl+C to stop the server")
    print(f"="*60)
    
    with socketserver.TCPServer(("", port), MyHTTPRequestHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n✅ Server stopped")
            sys.exit(0)

if __name__ == "__main__":
    # Check if port is provided as argument
    port = 8080
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Error: Invalid port number '{sys.argv[1]}'")
            print(f"Usage: {sys.argv[0]} [port]")
            sys.exit(1)
    
    serve_documentation(port)