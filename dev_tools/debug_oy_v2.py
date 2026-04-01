import asyncio
from playwright.async_api import async_playwright

async def debug_oy():
    url = "https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo=A000000231499"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        
        # 1. 캡쳐 (클릭 전)
        await page.screenshot(path="/Users/summer/Desktop/사업/바이브코딩/큐텐 자동업로드/oy_before_click.png")
        
        # 2. 버튼 찾기 및 클릭
        print("Looking for option button...")
        clicked = await page.evaluate("""
            () => {
                const btns = Array.from(document.querySelectorAll('button'));
                const optBtn = btns.find(b => b.innerText && b.innerText.includes('선택해 주세요'));
                if (optBtn) {
                    console.log("Found button, clicking...");
                    optBtn.click();
                    return true;
                }
                return false;
            }
        """)
        print(f"Clicked: {clicked}")
        
        await page.wait_for_timeout(3000)
        
        # 3. 캡쳐 (클릭 후)
        await page.screenshot(path="/Users/summer/Desktop/사업/바이브코딩/큐텐 자동업로드/oy_after_click.png")
        
        # 4. 항목 추출 시도
        options = await page.evaluate("""
            () => {
                const btns = document.querySelectorAll('button.OptionSelector_option-item-btn__yq5_A');
                return Array.from(btns).map(b => b.innerText.trim());
            }
        """)
        print(f"Extracted Options ({len(options)}): {options}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_oy())
