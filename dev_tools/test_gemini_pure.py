from scraper import generate_product_description
import os
from dotenv import load_dotenv

load_dotenv()

def test_gemini_pure():
    title = "토리든 다이브인 저분자 히알루론산 세럼 50ml"
    print(f"Testing Gemini directly for: {title}")
    
    # 1. 제미나이 호출
    desc = generate_product_description(title)
    
    if desc:
        print("\n--- [Generated Description] ---")
        print(desc[:500] + "...")
        if "Noto Sans JP" in desc:
            print("\n✅ Success: Modern Theme CSS included.")
        else:
            print("\n❌ Failure: CSS not found.")
    else:
        print("\n❌ Error: No description generated.")

if __name__ == "__main__":
    test_gemini_pure()
