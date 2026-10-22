import asyncio
import os
import re
import json
import uuid
from pathlib import Path
from flask import Flask, request, jsonify, send_file, render_template, send_from_directory
import edge_tts

app = Flask(__name__)

# ── Thư mục lưu file audio xuất ra ──
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# ── Danh sách giọng đọc tiếng Trung của Microsoft Edge TTS ──
VOICES = {
    "zh-CN": {
        "label": "🇨🇳 Phổ thông (Mandarin)",
        "voices": [
            {"id": "zh-CN-XiaoxiaoNeural",  "name": "Xiaoxiao (晓晓)",   "gender": "Nữ",  "style": "Ấm áp, Tin tức, Tiểu thuyết"},
            {"id": "zh-CN-XiaoyiNeural",    "name": "Xiaoyi (晓伊)",     "gender": "Nữ",  "style": "Hoạt hình, Sôi động"},
            {"id": "zh-CN-YunjianNeural",   "name": "Yunjian (云健)",     "gender": "Nam", "style": "Thể thao, Nhiệt huyết"},
            {"id": "zh-CN-YunxiNeural",     "name": "Yunxi (云希)",       "gender": "Nam", "style": "Tiểu thuyết, Trẻ trung"},
            {"id": "zh-CN-YunxiaNeural",    "name": "Yunxia (云夏)",      "gender": "Nam", "style": "Hoạt hình, Dễ thương"},
            {"id": "zh-CN-YunyangNeural",   "name": "Yunyang (云扬)",     "gender": "Nam", "style": "Tin tức, Chuyên nghiệp"},
        ]
    },
    "zh-CN-dialect": {
        "label": "🗣️ Phương ngữ Trung Quốc",
        "voices": [
            {"id": "zh-CN-liaoning-XiaobeiNeural", "name": "Xiaobei - Liêu Ninh (辽宁小北)", "gender": "Nữ", "style": "Phương ngữ Đông Bắc"},
            {"id": "zh-CN-shaanxi-XiaoniNeural",   "name": "Xiaoni - Thiểm Tây (陕西小妮)",  "gender": "Nữ", "style": "Phương ngữ Thiểm Tây"},
        ]
    },
    "zh-HK": {
        "label": "🇭🇰 Quảng Đông (Cantonese)",
        "voices": [
            {"id": "zh-HK-HiuGaaiNeural",  "name": "HiuGaai (曉佳)",  "gender": "Nữ",  "style": "Thân thiện"},
            {"id": "zh-HK-HiuMaanNeural",  "name": "HiuMaan (曉曼)",  "gender": "Nữ",  "style": "Thân thiện"},
            {"id": "zh-HK-WanLungNeural",   "name": "WanLung (雲龍)",  "gender": "Nam", "style": "Thân thiện"},
        ]
    },
    "zh-TW": {
        "label": "🇹🇼 Đài Loan (Taiwanese Mandarin)",
        "voices": [
            {"id": "zh-TW-HsiaoChenNeural", "name": "HsiaoChen (曉臻)", "gender": "Nữ",  "style": "Thân thiện"},
            {"id": "zh-TW-HsiaoYuNeural",   "name": "HsiaoYu (曉雨)",   "gender": "Nữ",  "style": "Thân thiện"},
            {"id": "zh-TW-YunJheNeural",     "name": "YunJhe (雲哲)",    "gender": "Nam", "style": "Thân thiện"},
        ]
    }
}


def sanitize_filename(name: str) -> str:
    """Loại bỏ ký tự đặc biệt không hợp lệ, giữ lại Hán tự & Pinyin."""
    name = re.sub(r'[\\/:*?"<>|]', '_', name.strip())
    if not name:
        name = f"audio_{uuid.uuid4().hex[:8]}"
    return name


async def generate_tts(text: str, voice: str, rate: str, filename: str) -> Path:
    """Tạo file MP3 từ text bằng edge-tts."""
    safe_name = sanitize_filename(filename)
    if not safe_name.endswith(".mp3"):
        safe_name += ".mp3"
    output_path = OUTPUT_DIR / safe_name

    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(str(output_path))
    return output_path


def parse_file_content(content: str, file_ext: str) -> list[dict]:
    """Parse CSV/TSV/TXT file thành danh sách các mục cần đọc."""
    items = []
    lines = content.strip().split('\n')

    if file_ext in ('.csv', '.tsv'):
        sep = ',' if file_ext == '.csv' else '\t'
        for i, line in enumerate(lines):
            parts = [p.strip().strip('"').strip("'") for p in line.split(sep)]
            if len(parts) >= 2:
                # Cột 1: Nội dung đọc, Cột 2: Tên file
                items.append({"text": parts[0], "name": parts[1]})
            elif len(parts) == 1 and parts[0]:
                items.append({"text": parts[0], "name": parts[0]})
    else:
        for line in lines:
            line = line.strip()
            if line:
                items.append({"text": line, "name": line})

    return items


# ── ROUTES ──

@app.route("/")
def index():
    return render_template("index.html", voices=VOICES)


@app.route("/api/voices")
def api_voices():
    return jsonify(VOICES)


@app.route("/api/tts", methods=["POST"])
def api_tts():
    """Chuyển đổi text sang speech, trả về file MP3."""
    data = request.get_json()
    text = data.get("text", "").strip()
    voice = data.get("voice", "zh-CN-XiaoxiaoNeural")
    rate = data.get("rate", "+0%")
    filename = data.get("filename", "").strip()

    if not text:
        return jsonify({"error": "Vui lòng nhập nội dung cần đọc."}), 400

    if not filename:
        # Lấy 30 ký tự đầu làm tên file
        filename = text[:30].replace('\n', ' ')

    try:
        output_path = asyncio.run(generate_tts(text, voice, rate, filename))
        return jsonify({
            "success": True,
            "filename": output_path.name,
            "filepath": str(output_path),
            "url": f"/audio/{output_path.name}"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/tts-batch", methods=["POST"])
def api_tts_batch():
    """Chuyển đổi hàng loạt từ file upload (CSV/TSV/TXT)."""
    if "file" not in request.files:
        return jsonify({"error": "Không tìm thấy file upload."}), 400

    file = request.files["file"]
    voice = request.form.get("voice", "zh-CN-XiaoxiaoNeural")
    rate = request.form.get("rate", "+0%")

    if not file.filename:
        return jsonify({"error": "File trống."}), 400

    ext = Path(file.filename).suffix.lower()
    if ext not in ('.csv', '.tsv', '.txt'):
        return jsonify({"error": "Chỉ hỗ trợ file .csv, .tsv, .txt"}), 400

    try:
        content = file.read().decode("utf-8")
    except UnicodeDecodeError:
        try:
            file.seek(0)
            content = file.read().decode("gbk")
        except Exception:
            return jsonify({"error": "Không thể đọc file. Hãy dùng mã hóa UTF-8."}), 400

    items = parse_file_content(content, ext)
    if not items:
        return jsonify({"error": "File không chứa dữ liệu hợp lệ."}), 400

    results = []
    for item in items:
        try:
            output_path = asyncio.run(generate_tts(item["text"], voice, rate, item["name"]))
            results.append({
                "text": item["text"],
                "filename": output_path.name,
                "url": f"/audio/{output_path.name}",
                "status": "success"
            })
        except Exception as e:
            results.append({
                "text": item["text"],
                "filename": "",
                "url": "",
                "status": f"error: {str(e)}"
            })

    return jsonify({"results": results, "total": len(results)})


@app.route("/audio/<path:filename>")
def serve_audio(filename):
    return send_from_directory(str(OUTPUT_DIR), filename, mimetype="audio/mpeg")


@app.route("/api/files")
def list_files():
    """Liệt kê tất cả file audio đã tạo."""
    files = []
    for f in sorted(OUTPUT_DIR.iterdir()):
        if f.suffix == ".mp3":
            files.append({
                "name": f.name,
                "size": f"{f.stat().st_size / 1024:.1f} KB",
                "url": f"/audio/{f.name}"
            })
    return jsonify(files)


@app.route("/api/rename", methods=["POST"])
def rename_file():
    """Đổi tên file audio."""
    data = request.get_json()
    old_name = data.get("old_name", "")
    new_name = sanitize_filename(data.get("new_name", ""))
    if not new_name.endswith(".mp3"):
        new_name += ".mp3"

    old_path = OUTPUT_DIR / old_name
    new_path = OUTPUT_DIR / new_name

    if not old_path.exists():
        return jsonify({"error": "File không tồn tại."}), 404
    if new_path.exists():
        return jsonify({"error": "Tên file mới đã tồn tại."}), 409

    old_path.rename(new_path)
    return jsonify({"success": True, "new_name": new_name, "url": f"/audio/{new_name}"})


@app.route("/api/delete", methods=["POST"])
def delete_file():
    """Xóa file audio."""
    data = request.get_json()
    filename = data.get("filename", "")
    filepath = OUTPUT_DIR / filename
    if filepath.exists() and filepath.suffix == ".mp3":
        filepath.unlink()
        return jsonify({"success": True})
    return jsonify({"error": "File không tồn tại."}), 404


if __name__ == "__main__":
    print(f"\n🎙️  Chinese TTS Server đang chạy!")
    print(f"📂  File audio xuất ra: {OUTPUT_DIR}")
    print(f"🌐  Mở trình duyệt: http://localhost:5500\n")
    app.run(host="0.0.0.0", port=5500, debug=True)
