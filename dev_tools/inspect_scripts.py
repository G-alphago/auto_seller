import json
import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

url = "https://www.musinsa.com/products/2407421"
print(f"Inspecting scripts for: {url}")

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(url)
    page.wait_for_timeout(5000)
    html = page.content()
    soup = BeautifulSoup(html, "html.parser")
    
    scripts = soup.find_all("script")
    print(f"Total script tags found: {len(scripts)}")
    
    for i, s in enumerate(scripts):
        sid = s.get("id", "NO_ID")
        stype = s.get("type", "NO_TYPE")
        content = (s.string or "")[:200].replace("\n", " ")
        print(f"[{i}] ID: {sid} | Type: {stype} | Content Start: {content}...")
        
        if sid == "pdp-data":
            print(f"  FULL PDP-DATA START: {s.string[:1000]}")
        if sid == "__NEXT_DATA__":
            try:
                data = json.loads(s.string)
                def find_key_recursive(d, target, path=""):
                    if isinstance(d, dict):
                        if target in d: return f"{path}.{target}"
                        for k, v in d.items():
                            res = find_key_recursive(v, target, f"{path}.{k}")
                            if res: return res
                    elif isinstance(d, list):
                        for i, v in enumerate(d):
                            res = find_key_recursive(v, target, f"{path}[{i}]")
                            if res: return res
                    return None
                
                path = find_key_recursive(data, "options")
                print(f"  Detected Options Path: {path}")
                if path:
                    # 해당 경로의 데이터 일부 출력
                    # (간단하게 eval-like 접근)
                    curr = data
                    for part in path.strip(".").split("."):
                        if "[" in part:
                            p, idx = part.split("[")
                            idx = int(idx.rstrip("]"))
                            curr = curr[p][idx]
                        else:
                            curr = curr[part]
                    print(f"  Options Data Sample: {str(curr)[:500]}")
            except Exception as e:
                print(f"  Search error: {e}")
    
    browser.close()
