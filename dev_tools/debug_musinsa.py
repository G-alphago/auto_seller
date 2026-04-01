from scraper import extract_product
import json

url = "https://www.musinsa.com/products/2407421"
print(f"Testing Musinsa: {url}")
result = extract_product(url)

# options가 비어있거나 엉뚱한게 나왔다면 js_data를 직접 확인하고 싶음.
# 하지만 extract_product는 js_data를 리턴하지 않음.
# scraper.py를 잠시 수정해서 js_data를 프린트하게 하거나, 여기서 직접 BeautifulSoup으로 확인.

from bs4 import BeautifulSoup
from scraper import extract_js_data_from_soup, parse_options
import requests

headers = {"User-Agent": "Mozilla/5.0"}
# requests로 한 번 시도 (403일 가능성 높음)
try:
    resp = requests.get(url, headers=headers)
    print(f"Requests Status: {resp.status_code}")
    soup = BeautifulSoup(resp.text, "html.parser")
    js = extract_js_data_from_soup(soup)
    print(f"JS Keys (Requests): {js.keys()}")
    if "__NEXT_DATA__" in js:
        # 파일로 저장해서 구조 확인
        with open("musinsa_next_data.json", "w") as f:
            json.dump(js["__NEXT_DATA__"], f, indent=2, ensure_ascii=False)
        print("Saved musinsa_next_data.json")
except Exception as e:
    print(f"Requests error: {e}")

# Playwright로 시도
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(url)
    page.wait_for_timeout(5000)
    html = page.content()
    soup = BeautifulSoup(html, "html.parser")
    
    scripts = soup.find_all("script")
    print(f"Total script tags: {len(scripts)}")
    for s in scripts:
        if s.get("id"):
            print(f"Script ID: {s.get('id')}")
        if s.string and "__NEXT_DATA__" in s.string:
            print("Found __NEXT_DATA__ in a script string!")
            print(f"Script ID of that script: {s.get('id')}")
            
    s = soup.find("script", id="__NEXT_DATA__")
    if s:
        print(f"NEXT_DATA script found. Length: {len(s.string or '')}")
        try:
            data = json.loads(s.string)
            print("Successfully parsed NEXT_DATA with json.loads!")
        except Exception as e:
            print(f"JSON loads error: {e}")
            # 일부 문자가 escape 되어 있을 수 있음
            try:
                import html
                unescaped = html.unescape(s.string)
                data = json.loads(unescaped)
                print("Successfully parsed after html.unescape!")
            except Exception as e2:
                print(f"JSON loads error after unescape: {e2}")

    js = extract_js_data_from_soup(soup)
    print(f"JS Keys (Playwright): {js.keys()}")
    browser.close()
