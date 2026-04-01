import csv
import os
import re
import json
import google.generativeai as genai
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# Gemini API 설정
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# 브랜드 데이터를 담을 전역 변수
_BRAND_MAP = {}
_BRAND_NAMES_SORTED = []
_BRAND_CACHE_FILE = os.path.join(os.path.dirname(__file__), "brand_cache.json")
_BRAND_CACHE = {}

def load_brand_cache():
    global _BRAND_CACHE
    if not _BRAND_CACHE and os.path.exists(_BRAND_CACHE_FILE):
        try:
            with open(_BRAND_CACHE_FILE, "r", encoding="utf-8") as f:
                _BRAND_CACHE = json.load(f)
        except Exception as e:
            print(f"[BrandClassifier] 캐시 로드 오류: {e}")
            _BRAND_CACHE = {}
    return _BRAND_CACHE

def save_brand_cache():
    global _BRAND_CACHE
    try:
        with open(_BRAND_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(_BRAND_CACHE, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[BrandClassifier] 캐시 저장 오류: {e}")

def match_brand_with_gemini(scraped_name: str) -> str:
    """
    Gemini를 통해 한글 브랜드명을 글로벌 영문 브랜드명으로 변환 시도 (캐시 활용)
    """
    if not scraped_name:
        return None
        
    cache = load_brand_cache()
    if scraped_name in cache:
        return cache[scraped_name]

    if not GEMINI_API_KEY:
        return None
        
    prompt = f"""
    당신은 이커머스 전문가입니다. 
    다음 한국 브랜드명을 글로벌 이커머스(Qoo10, Amazon 등)에서 사용하는 공식 영문 브랜드명으로 변환해주세요.
    결과는 오직 영문 브랜드명만 출력하세요 (부가 설명 금지).
    
    한국 브랜드명: {scraped_name}
    영문 브랜드명:
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-flash') # 할당량이 넉넉한 안정적 모델로 변경
        response = model.generate_content(prompt)
        res = response.text.strip().upper()
        # 마크다운이나 따옴표 제거
        res = re.sub(r'[`"\'*]', '', res).strip()
        
        # 결과 캐싱
        _BRAND_CACHE[scraped_name] = res
        save_brand_cache()
        
        print(f"[Gemini Match] {scraped_name} -> {res}")
        return res
    except Exception as e:
        if "Quota exceeded" in str(e):
            print(f"[Gemini Match] Quota exceeded. Using original name as fallback.")
        else:
            print(f"[Gemini Brand Match Error] {e}")
        return None

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
        
        # [추가] 커스텀 브랜드 매칭 및 한글/영문 에일리어스 (매칭률 향상용)
        # 이미 CSV에 있는 경우 오버라이드하거나 보강
        _BRAND_ALIASES = {
            "컨버스": "CONVERSE",
            "나이키": "NIKE",
            "아디다스": "ADIDAS",
            "스파오": "SPAO",
            "올리브영": "OLIVE YOUNG",
            "무신사": "MUSINSA",
            "무신사 스탠다드": "MUSINSA STANDARD",
            "뉴발란스": "NEW BALANCE",
            "반스": "VANS",
            "푸마": "PUMA",
            "휠라": "FILA",
            "리복": "REEBOK",
            "커버낫": "COVERNAT",
            "에스쁘아": "ESPOIR",
            "롬앤": "ROMAND",
            "클리오": "CLIO",
            "페리페라": "PERIPERA",
            "닥터자르트": "DR.JART",
            "이니스프리": "INNISFREE",
            "더페이스샵": "THE FACE SHOP",
            "미샤": "MISSHA",
            "에뛰드": "ETUDE",
            "바닐라코": "BANILA CO",
            "투쿨포스쿨": "TOO COOL FOR SCHOOL",
            "비플레인": "BEPLAIN",
            "메디힐": "MEDIHEAL",
            "토리든": "TORRIDEN",
            "아누아": "ANUA",
            "라운드랩": "ROUND LAB",
            "구달": "GOODAL",
            "가히": "KAHI",
            "닥터지": "DR.G",
            "일리윤": "ILLIYOON",
            "브링그린": "BRING GREEN",
            "어누아": "ANUA",
            "아비브": "ABIB"
        }
        for kr, en in _BRAND_ALIASES.items():
            if en.upper() in _BRAND_MAP:
                _BRAND_MAP[kr.upper()] = _BRAND_MAP[en.upper()]
            else:
                # CSV에 영어 이름 가 없더라도 맵에는 등록 (나중에 찾기 위해)
                # 다만 코드가 없으므로 빈값일 수 있음. 
                # 여기서는 CSV에 있는 영문 키를 기준으로 코드를 가져옴.
                pass
        
        # 무신사 PB 등 특수 케이스 (Qoo10 브랜드 코드가 있다면 기입)
        _BRAND_MAP["MUSINSA STANDARD BEAUTY"] = "" # 필요시 코드 기입
        _BRAND_MAP["무신사 스탠다드 뷰티".upper()] = ""
        
        # 커스텀 브랜드 추가 후 정렬된 이름 목록을 다시 업데이트
        _BRAND_NAMES_SORTED = sorted(_BRAND_MAP.keys(), key=len, reverse=True)

    except Exception as e:
        print(f"[BrandClassifier] 로드 오류: {e}")
    
    return _BRAND_MAP, _BRAND_NAMES_SORTED

def extract_brand_info(title: str, scraped_brand: str = None):
    """
    제목에서 브랜드명을 감지하여 코드와 정제된 제목 반환.
    scraped_brand가 제공되면 이를 우선적으로 사용함.
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

    # 1. 외부에서 수집된 브랜드(scraped_brand)가 있는 경우 우선 처리
    if scraped_brand:
        norm_scraped = scraped_brand.strip().upper()
        # 직접 매칭 시도
        if norm_scraped in brand_map:
            best_brand_code = brand_map[norm_scraped]
            found_brand_names.append(scraped_brand)
        else:
            # 직접 매칭 실패 시 Gemini 폴백 사용
            gemini_name = match_brand_with_gemini(scraped_brand)
            if gemini_name and gemini_name in brand_map:
                best_brand_code = brand_map[gemini_name]
                found_brand_names.append(gemini_name)
            else:
                # 부분 매칭 시도 (scraped_brand가 리스트에 없을 때)
                for name in sorted_names:
                    if name == norm_scraped or name in norm_scraped:
                        best_brand_code = brand_map[name]
                        found_brand_names.append(name)
                        break

    # 2. 제목(title)에서 브랜드 검색 (아직 코드를 못 찾았거나 추가 정제가 필요한 경우)
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
            if name not in found_brand_names:
                found_brand_names.append(name)
            # 가장 먼저(길이순) 찾은 코드를 대표 브랜드 코드로 설정 (이미 있는 경우 제외)
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
