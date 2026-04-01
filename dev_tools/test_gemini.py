from scraper import extract_product_data
from converter import convert_to_qoo10_row
import json

def test_gemini_description():
    # 무신사 샘플 URL
    url = "https://www.musinsa.com/products/4397792"
    print(f"Testing Gemini Description for: {url}")
    
    # 1. 스크래핑
    product_data = extract_product_data(url)
    
    # 2. 변환 (여기서 Gemini 호출됨)
    row = convert_to_qoo10_row(product_data)
    
    # 3. 결과 확인
    description = row.get("item_description", "")
    print("\n--- [Generated Description Snippet] ---")
    print(description[-1000:]) # 마지막 1000자만 출력 (Gemini 설명이 하단에 있으므로)
    
    if "Noto Sans JP" in description:
        print("\n✅ Success: Modern Theme CSS found in description.")
    else:
        print("\n❌ Failure: CSS not found.")

if __name__ == "__main__":
    test_gemini_description()
