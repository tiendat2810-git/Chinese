#!/bin/bash
# ── Chinese TTS Studio ──
# Chạy script này để khởi động server TTS

cd "$(dirname "$0")"
source venv/bin/activate

echo ""
echo "  🎙️  ╔════════════════════════════════════════╗"
echo "      ║     Chinese TTS Studio v1.0            ║"
echo "      ║     Microsoft Edge Neural Voices       ║"
echo "      ╚════════════════════════════════════════╝"
echo ""
echo "  📂  File audio xuất ra: $(pwd)/output/"
echo "  🌐  Mở trình duyệt:    http://localhost:5500"
echo "  ⌨️   Tắt server:        Ctrl + C"
echo ""

python3 app.py
