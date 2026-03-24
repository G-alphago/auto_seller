from flask import Flask, render_template, request, jsonify, send_file
import os
import traceback

from scraper import extract_product
from converter import convert_to_qoo10_row
from exporter import save_to_excel

app = Flask(__name__)
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/process", methods=["POST"])
def process():
    data = request.get_json()
    url = (data or {}).get("url", "").strip()

    if not url:
        return jsonify({"error": "URL을 입력해 주세요."}), 400

    if not url.startswith("http"):
        return jsonify({"error": "올바른 URL 형식이 아닙니다. (http:// 또는 https://로 시작)"}), 400

    try:
        product = extract_product(url)
        row = convert_to_qoo10_row(product)
        filepath = save_to_excel(row, output_dir=OUTPUT_DIR)
        filename = os.path.basename(filepath)

        return jsonify({
            "success": True,
            "filename": filename,
            "preview": {
                "title":      row.get("상품명", ""),
                "price":      row.get("販売価格", ""),
                "main_image": row.get("メイン画像", ""),
                "options":    row.get("オプション情報", ""),
                "desc_len":   len(row.get("商品説明", "")),
            }
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"처리 중 오류 발생: {str(e)}"}), 500


@app.route("/download/<filename>")
def download(filename):
    safe_name = os.path.basename(filename)
    filepath = os.path.join(OUTPUT_DIR, safe_name)
    if not os.path.exists(filepath):
        return jsonify({"error": "파일을 찾을 수 없습니다."}), 404
    return send_file(filepath, as_attachment=True)


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    app.run(debug=True, port=8080)