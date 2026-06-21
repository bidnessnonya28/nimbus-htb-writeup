from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os, socketserver
OUT = os.path.join(os.path.dirname(__file__), "exfil_out")
os.makedirs(OUT, exist_ok=True)
class H(BaseHTTPRequestHandler):
    def _h(self):
        cl = self.headers.get('Content-Length')
        body = self.rfile.read(int(cl)) if cl else b""
        tag = self.path.strip("/").replace("/", "_") or "root"
        with open(os.path.join(OUT, tag + ".txt"), "ab") as f:
            f.write(body + b"\n")
        print(f"{self.command} {self.path} {len(body)}B", flush=True)
        try:
            self.send_response(200); self.end_headers(); self.wfile.write(b"ok\n")
        except Exception: pass
    do_GET = _h
    do_POST = _h
    def log_message(self, *a): pass
srv = ThreadingHTTPServer(("0.0.0.0", 8001), H)
srv.request_queue_size = 256
srv.daemon_threads = True
srv.serve_forever()
