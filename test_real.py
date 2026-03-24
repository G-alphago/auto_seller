from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto('https://item.gmarket.co.kr/Item?goodsCode=2518480298', wait_until='networkidle', timeout=30000)
    page.wait_for_timeout(2000)
    soup = BeautifulSoup(page.content(), 'html.parser')
    browser.close()

# 가격 관련 태그 전체 출력
print("=== strong 태그 ===")
for el in soup.find_all('strong'):
    txt = el.get_text(strip=True)
    if re.search(r'\d{3,}', txt) and len(txt) < 30:
        print(f'  class:{el.get("class")} txt:{txt}')

print("\n=== span 태그 ===")
for el in soup.find_all('span'):
    txt = el.get_text(strip=True)
    if re.search(r'\d{3,}원', txt) and len(txt) < 20:
        print(f'  class:{el.get("class")} txt:{txt}')