from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto('https://www.musinsa.com/products/5253332', wait_until='networkidle', timeout=30000)
    page.wait_for_timeout(3000)
    soup = BeautifulSoup(page.content(), 'html.parser')
    browser.close()

# id에 detail/desc 포함된 div 찾기
print("=== id 기준 ===")
for tag in soup.find_all(id=True):
    if any(kw in tag.get('id','').lower() for kw in ['detail','desc','goods','info','content']):
        print(f"  id={tag.get('id')} len={len(str(tag))}")

print("\n=== class 기준 ===")
for tag in soup.find_all(class_=True):
    cls = ' '.join(tag.get('class', []))
    if any(kw in cls.lower() for kw in ['detail','desc','goods','product-info']):
        if len(str(tag)) > 300:
            print(f"  class={cls[:60]} len={len(str(tag))}")
