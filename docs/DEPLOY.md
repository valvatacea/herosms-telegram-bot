# Panduan Deployment HeroSMS Telegram Bot

## 1. Persiapan environment

```bash
git clone https://github.com/valvatacea/herosms-telegram-bot.git
cd herosms-telegram-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Konfigurasi .env

Salin contoh dan isi nilai sebenarnya:

```bash
cp .env.example .env
# Edit .env:
# BOT_TOKEN=123456:ABC-DEF...
# HEROSMS_API_KEY=your_api_key
# HEROSMS_BASE_URL=https://hero-sms.com/api/v1
```

Jangan pernah commit `.env` — sudah tercantum di `.gitignore`.

## 3. Jalankan bot

```bash
python3 -m bot.main   # BUKAN python3 bot/main.py
```

Bot akan menjalankan `infinity_polling` dan siap menerima pesan.

## 4. Jalankan sebagai service (systemd, Linux)

Buat file `/etc/systemd/system/herosms-bot.service`:

```ini
[Unit]
Description=HeroSMS Telegram Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=/root/herosms-telegram-bot
Environment=HOME=/root
ExecStart=/root/herosms-telegram-bot/.venv/bin/python -m bot.main
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
```

Aktifkan:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now herosms-bot
sudo systemctl status herosms-bot
```

## 5. Docker (opsional)

Buat `Dockerfile`:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY bot/ ./bot/
COPY tests/ ./tests/
COPY .env.example .env.example
CMD ["python", "bot/main.py"]
```

Build & run:

```bash
docker build -t herosms-bot .
docker run --env-file .env herosms-bot
```

## 6. State

State pengguna disimpan di `user_state.json` (JSON plain, tidak di-commit). File ini dibuat otomatis saat bot berjalan dan bertahan Bersih restart.

## 7. Monitoring & log

Log ditulis ke stdout (format: `2026-... INFO herosms-bot: ...`). Untuk systemd, lihat lewat:

```bash
sudo journalctl -u herosms-bot -f
```

## 8. Troubleshooting

| Masalah | Solusi |
|---------|--------|
| `ModuleNotFoundError: No module named 'telebot'` | `pip install -r requirements.txt` |
| `RuntimeError: Set BOT_TOKEN...` | Isi `BOT_TOKEN` dan `HEROSMS_API_KEY` di `.env` |
| Bot tidak merespons | Cek `BOT_TOKEN` benar, bot sudah di-start oleh BotFather, firewall tidak blok |
| Callback tidak bekerja | Pastikan `parse_mode="MarkdownV2"` tidak error pada pesan yang di-edit |
