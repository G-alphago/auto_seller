from brand_classifier import extract_brand_info, load_brands

def test_matching():
    # 브랜드 데이터 미리 로드 (캐싱)
    load_brands()
    
    test_cases = [
        # (scraped_brand, title)
        ("커버낫", "커버낫 C 로고 맨투맨 블랙"),
        ("스파오", "SPAO 쿨테크 반팔 티셔츠"),
        ("가히", "가히 멀티밤 9g"),
        ("무신사 스탠다드", "무신사 스탠다드 와이드 슬랙스"),
        ("에스쁘아", "에스쁘아 비글로우 쿠션"),
        ("나이키", "NIKE AIR MAX 97"),
        (None, "아디다스 슈퍼스타 화이트"), # Title 기반 매칭
        ("올리브영", "올리브영 단독 기획 세트"),
        ("라운드랩", "라운드랩 자작나무 수분 크림")
    ]
    
    print(f"{'Scraped':<15} | {'Title':<25} | {'Code':<10} | {'Cleaned Title'}")
    print("-" * 80)
    
    for scraped, title in test_cases:
        code, cleaned = extract_brand_info(title, scraped)
        print(f"{str(scraped):<15} | {title[:25]:<25} | {str(code):<10} | {cleaned}")

if __name__ == "__main__":
    test_matching()
