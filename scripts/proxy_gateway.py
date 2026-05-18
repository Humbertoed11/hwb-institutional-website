import http.server
import http.client
import os
import sys

# SigmaFidelity™ Traffic Director - Institutional Proxy Gateway
# Version: 1.0.0 (Restored)

TARGET_APP = os.getenv('TARGET_APP', 'http://web:5000')
LISTEN_PORT = 8000

class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.handle_proxy()

    def do_POST(self):
        self.handle_proxy()

    def do_PUT(self):
        self.handle_proxy()

    def do_DELETE(self):
        self.handle_proxy()

    def handle_proxy(self):
        target_url = TARGET_APP.replace('http://', '').replace('https://', '')
        if ':' in target_url:
            host, port = target_url.split(':')
        else:
            host = target_url
            port = 80

        # Read the body if it exists
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else None

        # Prepare connection to target
        conn = http.client.HTTPConnection(host, int(port))
        
        # Filter headers
        headers = {k: v for k, v in self.headers.items() if k.lower() not in ['host', 'connection']}
        headers['Host'] = host

        try:
            conn.request(self.command, self.path, body, headers)
            res = conn.getresponse()

            self.send_response(res.status)
            for k, v in res.getheaders():
                if k.lower() not in ['transfer-encoding', 'content-length', 'connection']:
                    self.send_header(k, v)
            
            response_body = res.read()
            self.send_header('Content-Length', str(len(response_body)))
            self.end_headers()
            self.wfile.write(response_body)
        except Exception as e:
            self.send_response(502)
            self.end_headers()
            self.wfile.write(f"SigmaFidelity™ Gateway Error: {str(e)}".encode())
        finally:
            conn.close()

if __name__ == "__main__":
    print(f"--- SigmaFidelity™ Traffic Director Active ---")
    print(f"Target: {TARGET_APP}")
    print(f"Listening on Port: {LISTEN_PORT}")
    server = http.server.HTTPServer(('0.0.0.0', LISTEN_PORT), ProxyHandler)
    server.serve_forever()
