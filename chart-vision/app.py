import base64, concurrent.futures, hashlib, json, os, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from consensus import summarize
ENGINES = ("ollama","trading_analyzer","chart_vision_mcp","screenchart","openchart")
def post(url, payload):
    req=urllib.request.Request(url,json.dumps(payload).encode(),{"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=90) as r: return json.load(r)
def run_one(name, raw):
    try:
        if name=="ollama":
            model=os.getenv("OLLAMA_VISION_MODEL","llava")
            output=post(os.getenv("OLLAMA_URL","http://127.0.0.1:11434").rstrip("/")+"/api/generate",{"model":model,"prompt":"Analyze the trading chart. State trend, evidence, levels, bias BUY/SELL/WAIT; do not invent unreadable prices.","images":[base64.b64encode(raw).decode()],"stream":False})
            return {"status":"OK","model":model,"report":output.get("response","")}
        endpoint=os.getenv("ADAPTER_"+name.upper()+"_URL")
        if not endpoint: return {"status":"NOT_CONFIGURED","report":"Requires verified independent adapter"}
        return {"status":"OK","report":post(endpoint,{"image_base64":base64.b64encode(raw).decode()})}
    except Exception as e: return {"status":"ERROR","error":str(e)[:300]}
def analyze(raw):
    if not raw or len(raw)>8*1024*1024: raise ValueError("Image size must be 1-8 MB")
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        futures={name:pool.submit(run_one,name,raw) for name in ENGINES}
        results={name:futures[name].result() for name in ENGINES}
    return {"sha256":hashlib.sha256(raw).hexdigest(),"results":results,"consensus":summarize(results)}
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path=="/healthz":
            body=json.dumps({"status":"ok","configured_engines":{n:(n=="ollama" or bool(os.getenv("ADAPTER_"+n.upper()+"_URL"))) for n in ENGINES}}).encode()
            self.send_response(200);self.send_header("Content-Type","application/json");self.end_headers();self.wfile.write(body);return
        if self.path!="/": self.send_error(404);return
        from pathlib import Path
        body=(Path(__file__).parent/"index.html").read_bytes()
        self.send_response(200);self.send_header("Content-Type","text/html; charset=utf-8");self.end_headers();self.wfile.write(body)
    def do_POST(self):
        if self.path!="/analyze": self.send_error(404);return
        token=os.getenv("AMOS_API_TOKEN","")
        if token and self.headers.get("Authorization")!="Bearer "+token:
            self.send_response(401);self.end_headers();return
        try:
            n=int(self.headers.get("Content-Length","0"))
            if not 0<n<=12*1024*1024: raise ValueError("Request too large")
            obj=json.loads(self.rfile.read(n))
            raw=base64.b64decode(obj["image_base64"],validate=True)
            if not (raw.startswith(b"\x89PNG\r\n\x1a\n") or raw.startswith(b"\xff\xd8\xff")): raise ValueError("PNG/JPEG required")
            result=analyze(raw);status=200
        except Exception as e: result={"error":str(e)};status=400
        body=json.dumps(result,ensure_ascii=False).encode()
        self.send_response(status);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)
if __name__=="__main__": ThreadingHTTPServer((os.getenv("AMOS_BIND","127.0.0.1"),int(os.getenv("PORT","8765"))),Handler).serve_forever()
