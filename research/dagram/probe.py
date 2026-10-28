import asyncio, json, os, re, hashlib
from pathlib import Path
from urllib.parse import urlparse
from playwright.async_api import async_playwright

TARGET="https://www.dagrammasterclass.com/"
OUT=Path("artifacts/dagram"); OUT.mkdir(parents=True,exist_ok=True)
HOST="www.dagrammasterclass.com"
async def main():
    events=[]; scripts=[]; failures=[]
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True)
        page=await browser.new_page()
        page.on("request",lambda req: events.append({"type":"request","method":req.method,"url":req.url.split("?")[0]}) if len(events)<1000 else None)
        page.on("websocket",lambda ws: events.append({"type":"websocket","url":ws.url.split("?")[0]}) if len(events)<1000 else None)
        page.on("requestfailed",lambda req: failures.append({"url":req.url.split("?")[0],"error":req.failure}))
        status=None
        try:
            response=await page.goto(TARGET,wait_until="domcontentloaded",timeout=45000)
            status=response.status if response else None
            await page.wait_for_timeout(12000)
            await page.screenshot(path=str(OUT/"screenshot.png"),full_page=True)
            for i,url in enumerate(await page.locator("script[src]").evaluate_all("(els)=>els.map(e=>e.src)")):
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
        (OUT/"summary.json").write_text(json.dumps({"http_status":status,"title":await page.title(),"scripts":scripts,"events":events,"failures":failures},ensure_ascii=False,indent=2))
        await browser.close()
asyncio.run(main())
