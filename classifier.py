import csv
import os
import re

# 카테고리 데이터를 담을 전역 변수 (캐싱)
_CATEGORIES = []

def load_categories():
    """Qoo10_CategoryInfo.csv 파일을 로드하여 메모리에 캐싱"""
    global _CATEGORIES
    if _CATEGORIES:
        return _CATEGORIES

    csv_path = os.path.join(os.path.dirname(__file__), "Qoo10_CategoryInfo.csv")
    if not os.path.exists(csv_path):
        print(f"[Classifier] 경고: {csv_path} 파일을 찾을 수 없습니다.")
        return []

    try:
        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                _CATEGORIES.append({
                    "large_code": row.get("대카테고리 코드", ""),
                    "large_name": row.get("대카테고리 명", ""),
                    "middle_code": row.get("중카테고리 코드", ""),
                    "middle_name": row.get("중카테고리 명", ""),
                    "small_code": row.get("소카테고리 코드", ""),
                    "small_name": row.get("소카테고리 명", "")
                })
        print(f"[Classifier] {len(_CATEGORIES)}개의 카테고리 로드 완료.")
    except Exception as e:
        print(f"[Classifier] 로드 오류: {e}")
    
    return _CATEGORIES

def match_category(product_title: str) -> str:
    """
    상품명을 분석하여 가장 적합한 소카테고리 코드 반환.
    """
    if not product_title:
        return ""

    categories = load_categories()
    if not categories:
        return ""

    # 상품명 정제 및 성별/연령대 키워드 추출
    clean_title = re.sub(r'[^\w\s]', ' ', product_title)
    tokens = [t.strip() for t in clean_title.split() if len(t.strip()) > 1]
    title_text = " ".join(tokens).upper()

    # 성별/연령대 가중치 키워드
    is_female = any(kw in title_text for kw in ["여성", "여자", "우먼", "여아", "LADY"])
    is_male   = any(kw in title_text for kw in ["남성", "남자", "맨즈", "남아", "MENS"])
    is_child  = any(kw in title_text for kw in ["아동", "키즈", "어린이", "유아", "베이비", "KIDS", "BABY"])

    # 핵심 카테고리 힌트
    is_smartphone = any(kw in title_text for kw in ["GALAXY", "IPHONE", "갤럭시", "아이폰", "스마트폰", "폰케이스"])
    is_beauty     = any(kw in title_text for kw in ["화장품", "코스메틱", "스킨케어", "로션", "에센스", "뷰티"])
    is_fashion    = any(kw in title_text for kw in ["의류", "원피스", "팬츠", "셔츠", "자켓", "코트", "정장"])

    best_match = None
    max_score = -1

    for cat in categories:
        score = 0
        s_name = cat["small_name"]
        m_name = cat["middle_name"]
        l_name = cat["large_name"]
        all_names = f"{l_name} {m_name} {s_name}".upper()

        # 1. 성별/연령대 필터링
        cat_is_female = any(kw in all_names for kw in ["여성", "여자"])
        cat_is_male   = any(kw in all_names for kw in ["남성", "남자", "멘즈"])
        cat_is_child  = any(kw in all_names for kw in ["임산부", "유아", "베이비", "키즈", "아동", "어린이"])

        if is_female and cat_is_female: score += 15
        if is_male   and cat_is_male:   score += 15
        if is_child  and cat_is_child:  score += 15
        
        # 불일치 시 페널티
        if is_female and cat_is_male and not is_male: score -= 30
        if is_male and cat_is_female and not is_female: score -= 30
        if not is_child and cat_is_child: score -= 25
        if is_child and not cat_is_child and (cat_is_female or cat_is_male): score -= 15

        # 2. 핵심 카테고리 힌트 가중치
        if is_smartphone and "스마트폰케이스" in all_names: score += 50
        if is_beauty     and any(kw in all_names for kw in ["스킨케어", "화장품", "뷰티"]): score += 50
        if is_fashion    and any(kw in l_name for kw in ["여성복", "남성 의류"]): score += 10
        
        # 취미/코스튬플레이 카테고리 기피 (일반 의류일 경우)
        if is_fashion and "취미" in l_name and not any(kw in title_text for kw in ["코스프레", "코스튬", "변장"]):
            score -= 40

        # 3. 키워드 매칭 (영어 키워드 대응 포함)
        for token in tokens:
            if token in s_name.upper():
                score += 20
            elif token in m_name.upper():
                score += 10
            elif token in l_name.upper():
                score += 5
        
        # 4. 소카테고리 명칭과 토큰이 일치하는 경우 추가 점수
        if any(token == s_name.replace(" ", "").upper() for token in tokens):
            score += 35

        if score > max_score:
            max_score = score
            # 소-중-대 순으로 유효한 코드 선택
            best_match = cat.get("small_code") or cat.get("middle_code") or cat.get("large_code") or ""


    # 최소 임계값 미만인 경우 기본 카테고리 (여성 패션 등 일반적인 곳) 반환
    if max_score < 10 or not best_match:
        # Qoo10_CategoryInfo.csv의 첫 번째 유효한 코드라도 반환 (절대 공백 금지)
        return categories[0].get("small_code") or categories[0].get("middle_code") or "100000001"

    return best_match


if __name__ == "__main__":
    # 간단 테스트
    test_titles = ["여성용 정장 바지 슬랙스", "나이키 운동화 스니커즈", "원피스 드레스"]
    for title in test_titles:
        code = match_category(title)
        print(f"Title: {title} -> Code: {code}")
