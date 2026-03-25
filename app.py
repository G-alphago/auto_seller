from flask import Flask, render_template, request, jsonify, send_file
import os
import traceback
from datetime import datetime

from scraper import extract_product
from converter import convert_to_qoo10_row
from exporter import save_to_excel, save_summary_excel

app = Flask(__name__)
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/process", methods=["POST"])
def process():
    data = request.get_json()
    urls = (data or {}).get("urls", [])

    if not urls:
        return jsonify({"error": "처리할 URL이 없습니다."}), 400

    upload_rows = []
    preview_image = None

    try:
        for url in urls:
            url = url.strip()
            if not url or not url.startswith("http"):
                continue
                
            try:
                product = extract_product(url)
                row = convert_to_qoo10_row(product)
                row["source_url"] = url
                upload_rows.append(row)
                
                if not preview_image:
                    # converter.py에서 '메인 이미지' 또는 '이미지_메인_URL' 등을 사용하는지 확인
                    # convert_to_qoo10_row의 결과 컬럼명은 큐텐 양식이므로 '이미지_메인_URL' 보다는 
                    # 원본 데이터나 변환된 행의 특정 컬럼을 활용
                    preview_image = row.get("image_main_url", "")
            except Exception as e:
                print(f"[UI 처리 오류] {url}: {e}")
                continue

        if not upload_rows:
            return jsonify({"error": "유효한 상품 데이터를 추출하지 못했습니다."}), 500

        # 엑셀 파일 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        upload_file = f"qoo10_upload_{timestamp}.xlsx"
        summary_file = f"summary_{timestamp}.xlsx"

        upload_path  = save_to_excel(upload_rows, output_dir=OUTPUT_DIR, filename=upload_file)
        summary_path = save_summary_excel(upload_rows, output_dir=OUTPUT_DIR, filename=summary_file)

        return jsonify({
            "success": True,
            "count": len(upload_rows),
            "upload_file": upload_file,
            "summary_file": summary_file,
            "preview_image": preview_image
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"처리 중 치명적 오류 발생: {str(e)}"}), 500


@app.route("/download/<filename>")
def download(filename):
    safe_name = os.path.basename(filename)
    filepath = os.path.join(OUTPUT_DIR, safe_name)
    if not os.path.exists(filepath):
        return jsonify({"error": "파일을 찾을 수 없습니다."}), 404
    return send_file(filepath, as_attachment=True)


@app.route("/outputs/<path:filename>")
def serve_outputs(filename):
    return send_file(os.path.join(OUTPUT_DIR, filename))


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    app.run(debug=True, port=8080)