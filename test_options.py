import os
from scraper import extract_product
from converter import format_options_qoo10

def test_url(url, label):
    print(f"\n--- Testing {label} ---")
    print(f"URL: {url}")
    try:
        # 1. Scraping (using the wrapper that has Playwright fallback)
        result = extract_product(url)
        
        options = result.get("options", [])
        print(f"Scraped Options: {options}")
        
        # 2. Formatting
        qoo10_str = format_options_qoo10(options)
        print(f"Qoo10 Option String (Sample, first 500 chars):")
        print(qoo10_str[:500] + "..." if len(qoo10_str) > 500 else qoo10_str)
        
    except Exception as e:
        print(f"Error testing {label}: {e}")

if __name__ == "__main__":
    test_cases = []

    # Test Musinsa (2-level: Color/Size)
    test_cases.append({
        "url": "https://www.musinsa.com/products/2407421",
        "label": "Musinsa (2-level)"
    })
    
    # Test Olive Young (1-level: Color)
    test_cases.append({
        "url": "https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo=A000000231499",
        "label": "Olive Young (1-level)"
    })
    
    # Test 11st (1-level: Color selection in sidebar)
    test_cases.append({
        "url": "https://www.11st.co.kr/products/9057736472",
        "label": "11st (1-level)"
    })

    for case in test_cases:
        test_url(case["url"], case["label"])
