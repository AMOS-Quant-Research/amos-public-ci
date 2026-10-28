import asyncio, json, os, re, hashlib
from pathlib import Path
from urllib.parse import urlparse
from playwright.async_api import async_playwright

TARGET="https://www.dagrammasterclass.com/"
OUT=Path("artifacts/dagram"); OUT.mkdir(parents=True,exist_ok=True)
HOST="www.dagrammasterclass.com"
def safe_event(event):
    # Whitelist schema/market fields only; do not persist raw frames or secrets.
    raw=event.get("data","")
    out={"event":str(event.get("eventName",""))[:50],"bytes":len(raw)}
    try:
        payload=json.loads(raw)
        if isinstance(payload,dict):
            out["keys"]=sorted(str(k)[:50] for k in payload.keys())[:30]
            candidates=[payload]+[payload[k] for k in ("publication","plan","data","payload","signal") if isinstance(payload.get(k),dict)]
            for item in candidates:
                for key in ("side","direction","symbol","timeframe","tf","issuedAt","timestamp","status"):
                    val=item.get(key)
                    if isinstance(val,(str,int,float)) and len(str(val))<90:
                        out.setdefault("public_fields",{})[key]=val
                for key in ("entry","sl","stopLoss","tp"):
                    val=item.get(key)
                    if isinstance(val,(int,float)) and abs(val)<1e12:
                        out.setdefault("public_fields",{})[key]=val
                if isinstance(item.get("tps"),list):
                    out.setdefault("public_fields",{})["tps"]=[x for x in item["tps"][:5] if isinstance(x,(int,float))]
    except (ValueError,TypeError): pass
    return out

async def main():
    events=[]; scripts=[]; failures=[]; responses=[]; sse_events=[]; ws_events=[]
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True)
        page=await browser.new_page()
        cdp=await page.context.new_cdp_session(page)
        await cdp.send("Network.enable")
        cdp.on("Network.eventSourceMessageReceived",lambda ev: sse_events.append(safe_event(ev)) if len(sse_events)<150 else None)
        cdp.on("Network.webSocketFrameReceived",lambda ev: ws_events.append(safe_event({"eventName":"websocket","data":ev.get("response",{}).get("payloadData","")})) if len(ws_events)<150 else None)
        page.on("request",lambda req: events.append({"type":"request","method":req.method,"url":req.url.split("?")[0]}) if len(events)<1000 else None)
        page.on("websocket",lambda ws: events.append({"type":"websocket","url":ws.url.split("?")[0]}) if len(events)<1000 else None)
        page.on("response",lambda resp: responses.append({"status":resp.status,"url":resp.url.split("?")[0],"type":resp.request.resource_type}) if len(responses)<1000 else None)
        page.on("requestfailed",lambda req: failures.append({"url":req.url.split("?")[0],"error":req.failure}))
        status=None
        try:
            response=await page.goto(TARGET,wait_until="domcontentloaded",timeout=45000)
            status=response.status if response else None
            await page.wait_for_timeout(25000)
            await page.screenshot(path=str(OUT/"screenshot.png"),full_page=True)
            for i,url in enumerate(sorted(set([e["url"] for e in events if e["url"].endswith(".js") and e["url"].startswith("https://www.dagrammasterclass.com/")]))):
                if urlparse(url).hostname != HOST: continue
                try:
                    resp=await page.request.get(url,timeout=15000)
                    body=await resp.body()
                    if len(body)>3000000: continue
                    name=f"script_{i}.js"
                    (OUT/name).write_bytes(body)
                    scripts.append({"url":url.split("?")[0],"file":name,"sha256":hashlib.sha256(body).hexdigest(),"matches":list(set(re.findall(r"(?i)buy|sell|stay|signal|entry|stoploss|takeprofit",body.decode("utf-8","replace"))))[:30]})
                except Exception as e: failures.append({"url":url.split("?")[0],"error":str(e)})
        except Exception as e: failures.append({"navigation":str(e)})
        (OUT/"summary.json").write_text(json.dumps({"http_status":status,"title":await page.title(),"scripts":scripts,"events":events,"responses":responses,"sse_events":sse_events,"websocket_events":ws_events,"event_count":{"sse":len(sse_events),"websocket":len(ws_events)},"failures":failures},ensure_ascii=False,indent=2))
        await browser.close()
asyncio.run(main())
