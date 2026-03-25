import csv
import os
import re

# 브랜드 데이터를 담을 전역 변수
_BRAND_MAP = {}
_BRAND_NAMES_SORTED = []

def load_brands():
    """BrandList.csv 파일을 로드하여 매핑 생성"""
    global _BRAND_MAP, _BRAND_NAMES_SORTED
    if _BRAND_MAP:
        return _BRAND_MAP, _BRAND_NAMES_SORTED

    csv_path = os.path.join(os.path.dirname(__file__), "BrandList.csv")
    if not os.path.exists(csv_path):
        print(f"[BrandClassifier] 경고: {csv_path} 파일을 찾을 수 없습니다.")
        return {}, []

    try:
        with open(csv_path, mode='r', encoding='utf-8-sig') as f:
            # 헤더: Brand No.,Brand Title,English,Japanese,Maker title 
            reader = csv.DictReader(f)
            # 모든 키에서 앞뒤 공백을 제거한 맵을 사용하기 위해 헤더 재정의 (필요시)
            for row in reader:
                # 키 정규화 (공백 제거)
                normalized_row = {k.strip(): v for k, v in row.items() if k}
                
                code = (normalized_row.get("Brand No.") or normalized_row.get("Brand No") or "").strip()
                if not code: continue
                
                # 매칭 후보 이름들 (영어, 일어, 공통 타이틀, 메이커 타이틀)
                names = [
                    (normalized_row.get("English") or "").strip(),
                    (normalized_row.get("Japanese") or "").strip(),
                    (normalized_row.get("Brand Title") or "").strip(),
                    (normalized_row.get("Maker title") or "").strip()
                ]
                
                for name in names:
                    if name and len(name) >= 2: # 최소 2글자 이상만 브랜드로 인정
                        norm_name = name.upper()
                        if norm_name not in _BRAND_MAP:
                            _BRAND_MAP[norm_name] = code
            
            # 매칭 시 긴 이름부터 확인하기 위해 길이순 정렬
            _BRAND_NAMES_SORTED = sorted(_BRAND_MAP.keys(), key=len, reverse=True)
            
        print(f"[BrandClassifier] {len(_BRAND_MAP)}개의 브랜드 키워드 로드 완료.")
        
        # [추가] 커스텀 브랜드 매칭 (예외 처리 및 일본어 오표기 대응)
        # 이 부분은 _BRAND_MAP의 기존 구조(key: brand_name_upper, value: brand_code)와 일치하도록 수정되었습니다.
        # '무신사 스탠다드 뷰티'의 브랜드 코드를 'MSB'로 가정하고 추가합니다.
        # 실제 코드에 맞게 'MSB'를 적절한 브랜드 코드로 변경해야 합니다.
        custom_brand_code = _BRAND_MAP.get("MUSINSA STANDARD BEAUTY", "MSB") # 기존에 있으면 그 코드를 사용, 없으면 'MSB' 사용
        _BRAND_MAP["MUSINSA STANDARD BEAUTY"] = custom_brand_code
        _BRAND_MAP["무신사 스탠다드 뷰티".upper()] = custom_brand_code
        _BRAND_MAP["ム신사스탠다드뷰티".upper()] = custom_brand_code
        _BRAND_MAP["無神社スタンダードビューティー".upper()] = custom_brand_code
        # 커스텀 브랜드 추가 후 정렬된 이름 목록을 다시 업데이트
        _BRAND_NAMES_SORTED = sorted(_BRAND_MAP.keys(), key=len, reverse=True)

    except Exception as e:
        print(f"[BrandClassifier] 로드 오류: {e}")
    
    return _BRAND_MAP, _BRAND_NAMES_SORTED

def extract_brand_info(title: str):
    """
    제목에서 브랜드명을 감지하여 코드와 정제된 제목 반환.
    반환값: (brand_code, cleaned_title)
    """
    if not title:
        return "", ""

    brand_map, sorted_names = load_brands()
    if not brand_map:
        return "", title

    upper_title = title.upper()
    found_brand_names = []
    best_brand_code = ""

    # 모든 브랜드 이름을 검색하여 리스트업
    for name in sorted_names:
        is_match = False
        # 영문/숫자로만 이루어진 경우 단어 경계 체크 
        if re.match(r'^[A-Z0-9\s\.]+$', name):
            pattern = re.compile(r'\b' + re.escape(name) + r'\b', re.IGNORECASE)
            if pattern.search(title):
                is_match = True
        else:
            # 한글/일어 등은 포함 여부로 체크
            if name in upper_title:
                is_match = True

        if is_match:
            found_brand_names.append(name)
            # 가장 먼저(길이순) 찾은 코드를 대표 브랜드 코드로 설정
            if not best_brand_code:
                best_brand_code = brand_map[name]

    cleaned_title = title
    # 발견된 모든 브랜드명을 제목에서 제거
    for b_name in found_brand_names:
        if re.match(r'^[A-Z0-9\s\.]+$', b_name):
            pattern = re.compile(r'\b' + re.escape(b_name) + r'\b', re.IGNORECASE)
        else:
            pattern = re.compile(re.escape(b_name), re.IGNORECASE)
        cleaned_title = pattern.sub("", cleaned_title).strip()

    # 제거 후 남은 공백이나 특수문자 정제
    cleaned_title = re.sub(r'^[ \t\n\r\f\v\-_|,/]+', '', cleaned_title) # 불필요한 공백 및 특수문자 정리
    cleaned_title = re.sub(r'\s+', ' ', cleaned_title) # 2개 이상의 공백을 1개로
    # 빈 괄호 제거 (예: 브랜드명 제거 후 남은 괄호)
    cleaned_title = re.sub(r'\(\s*\)|\[\s*\]|\{\s*\}|（\s*）|【\s*】', '', cleaned_title)
    cleaned_title = cleaned_title.strip()

    return best_brand_code, cleaned_title



if __name__ == "__main__":
    # 테스트
    test_titles = [
        "NIKE AIR FORCE 1 LOW WHITE",
        "SAMSUNG GALAXY S24 ULTRA CASE",
        "ADIDAS SUPERSTAR SHOES",
        "무신사 스탠다드 슬랙스" # 한국어 브랜드는 CSV에 없으면 매칭 안됨
    ]
    for t in test_titles:
        code, cleaned = extract_brand_info(t)
        print(f"Original: {t}")
        print(f"  -> Code: {code}, Cleaned: {cleaned}\n")
