# HeroSMS Telegram Bot

Bot Telegram yang memuat **seluruh API HeroSMS** (OpenAPI 3.2.0, versi 1.0) dengan tampilan inline keyboard yang rapi dan ramah pengguna.

## Fitur

- 💰 Cek saldo & statistik akun
- 🌍 Daftar negara, layanan, dan harga
- 🛒 Beli nomor verifikasi (SMS/OTP)
- 📨 Terima OTP (terakhir atau daftar)
- ✅ Selesaikan, ❌ batalkan, 🔄 reaktivasi, ⏳ perpanjang aktivasi
- 📬 Aktivasi via email (domains, offers, beli, batal, pesan ulang)
- 📊 Statistik deliverability per negara

## Instalasi

```bash
git clone https://github.com/<USER>/herosms-telegram-bot.git
cd herosms-telegram-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env, isi BOT_TOKEN dan HEROSMS_API_KEY
python bot.py
```

## Variabel lingkungan

| Variabel | Keterangan |
|----------|------------|
| `BOT_TOKEN` | Token BotFather Telegram |
| `HEROSMS_API_KEY` | API key dari HeroSMS |
| `HEROSMS_BASE_URL` | Base URL API (default: `https://hero-sms.com/api/v1`) |

## API yang dicakup

Semua endpoint dari `api-enjson`:
Activations, Activation OTP, Classifiers, Statistics, Emails, dan SMS-Activate compatible (`?action=…`).

## Lisensi

MIT
