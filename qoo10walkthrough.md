# 큐텐 재팬 자동 업로드 파이프라인 작업 보고서 (qoo10walkthrough)

기존 시스템의 버그를 수정하고, 대량 업로드를 위한 다중 URL 처리 및 결과물 분리 기능을 완벽히 구현하였습니다.

## 1. 주요 구현 및 수정 사항

### 🛠 데이터 추출 및 필터링 (scraper.py)
*   **버그 수정**: 상세 페이지 본문이 스킵되던 원인인 `layout`, `commonLayout` 필터를 제거하여 모든 본문 데이터를 정상 추출하도록 개선했습니다.
*   **환경 최적화**: 서버/에이전트 환경에서 원활한 실행을 위해 Playwright를 `headless=True` 모드로 설정하고, 임시 폴더 권한 문제를 해결하는 로직을 적용했습니다.

### 🌐 자동 번역 및 HTML 보존 (converter.py)
*   **HTML 번역**: `BeautifulSoup`을 사용하여 상세 설명의 HTML 태그 구조는 그대로 유지하면서 내부에 포함된 한글 텍스트만 일본어로 번역하는 기능을 추가했습니다.
*   **이미지 규격화**: 메인 이미지를 중앙 정렬하고 흰색 배경으로 패딩 처리하여 큐텐 가이드(800x800 정사각형)에 맞게 자동 변환 후 `outputs/images/`에 저장합니다.

### 📊 엑셀 출력 및 결과 분리 (exporter.py)
*   **다중 행 지원**: 여러 상품 데이터를 한 번에 입력받아 하나의 업로드용 엑셀 파일로 통합 생성하도록 기능을 확장했습니다.
*   **요약 파일 생성**: 원본 URL과 주요 정보를 매칭하여 관리할 수 있는 `summary_날짜.xlsx` 별도 생성 기능을 추가했습니다.

### 💻 사용자 인터페이스 (Web UI & Batch)
*   **웹 UI 개편**: `index.html`을 수정하여 **10개의 URL 입력 칸**을 제공하며, 한 번에 2종의 엑셀 파일을 모두 다운로드할 수 있도록 했습니다.
*   **배치 스크립트**: 대량 처리를 위한 전용 파일(`test_batch.py`)을 생성하여 수십 개의 URL도 터미널에서 즉시 처리 가능하게 했습니다.

## 2. 프로젝트 실행 방법

### 환경 설정 (최초 1회)
```bash
# 필수 라이브러리 설치
python3 -m pip install -r requirements.txt
python3 -m pip install Pillow playwright deep-translator
python3 -m playwright install
```

### 방식 A: 웹 화면에서 사용 (추천)
1.  터미널에서 `python3 app.py` 실행
2.  브라우저에서 `http://127.0.0.1:8080` 접속
3.  10개의 입력창에 URL 입력 후 '실행' 버튼 클릭

### 방식 B: 터미널에서 배치 처리
1.  `test_batch.py` 하단의 `test_urls` 리스트에 URL 추가
2.  터미널에서 명령 실행: `python3 test_batch.py`

## 3. 결과물 저장 경로
*   **업로드용 엑셀**: `outputs/qoo10_upload_날짜.xlsx`
*   **관리용 요약본**: `outputs/summary_날짜.xlsx`
*   **정사각형 이미지**: `outputs/images/` 폴더 내 저장

## 4. 버전 관리 (GitHub)
*   **저장소**: [https://github.com/G-alphago/auto_seller](https://github.com/G-alphago/auto_seller)
*   **설정**: `.env` 파일과 결과물(`outputs/`)은 `.gitignore`를 통해 안전하게 보호됩니다.

---
**작업 일시**: 2026-03-24
**작성자**: Antigravity AI Assistant
