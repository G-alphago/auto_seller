from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto('https://www.musinsa.com/products/5253332', wait_until='domcontentloaded', timeout=30000)
    page.wait_for_timeout(4000)

    imgs = page.evaluate("""
        () => {
            const imgs = [];
            document.querySelectorAll('img').forEach(img => {
                const src = img.src || '';
                if (src && !src.startsWith('data:')) imgs.push(src);
            });
            return [...new Set(imgs)];
        }
    """)

    print(f'총 이미지 수: {len(imgs)}')
    for img in imgs:
        print(img)

    browser.close()