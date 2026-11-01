# HeroSMS Telegram Bot

Bot Telegram yang mencakup **seluruh API HeroSMS** (OpenAPI 3.2.0, versi 1.0) dengan tampilan inline keyboard yang rapi, ramah pengguna, dan aman.

## Fitur

| Fitur | Keterangan |
|-------|------------|
| 💰 Saldo & Statistik | Cek saldo akun dan statistik penggunaan |
| 🌍 Negara & Layanan | Lihat daftar negara, layanan verifikasi, dan harga |
| 🛒 Beli Nomor | Beli nomor verifikasi SMS/OTP per negara & layanan |
| 📨 OTP | Terima OTP terakhir atau daftar seluruh OTP |
| ✅ Selesai / ❌ Batalkan | Selesaikan atau batalkan aktivasi (dengan konfirmasi) |
| 🔄 Kirim Ulang SMS | Minta pengiriman ulang SMS (dikorekansi dulu) |
| 🔔 Notif OTP | Notifikasi OTP otomatis untuk semua pembelian (default ON, matikan kapan saja) |
| 🔄 Reaktivasi | Reaktivasi aktivasi yang sudah selesai |
| ⏳ Perpanjang | Perpanjang masa aktif aktivasi |
| 📬 Email | Domain, offers, beli, detail, batal, pesan ulang aktivasi email |
| 🧪 Tes | Assert-based tanpa memanggil API nyata |

## Struktur direktori

```
herosms-telegram-bot/
├── bot/               # Paket utama bot
│   ├── __init__.py
│   ├── main.py        # Entry point (bot logic + callback router)
│   ├── client.py      # Klien API HeroSMS (semua endpoint)
│   ├── config.py      # Loader variabel lingkungan (.env)
│   ├── keyboards.py   # Inline keyboard (tombol navigasi)
│   ├── messages.py    # Format pesan MarkdownV2
│   ├── state.py       # State pengguna tersimpan di user_state.json
│   └── user_state.json # State runtime (tidak di-commit)
├── tests/             # Tes assert-based, tanpa API nyata
│   ├── __init__.py
│   └── test_herosms.py
├── docs/              # Dokumentasi
│   ├── API.md         # Referensi semua endpoint API
│   ├── DEPLOY.md      # Panduan deployment
│   ├── EVALUASI.md    # Evaluasi & keterbatasan bot
│   ├── MENU.md        # Alur menu dan UX
│   └── CONTRIBUTING.md # Panduan kontribusi
├── .env.example       # Contoh variabel lingkungan
├── .gitignore
├── LICENSE
├── requirements.txt
└── README.md
```

## Instalasi

```bash
git clone https://github.com/valvatacea/herosms-telegram-bot.git
cd herosms-telegram-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env, isi BOT_TOKEN dan HEROSMS_API_KEY
python bot/main.py
```

## Variabel lingkungan

| Variabel | Wajib | Keterangan | Default |
|----------|-------|------------|---------|
| `BOT_TOKEN` | Ya | Token dari BotFather Telegram | — |
| `HEROSMS_API_KEY` | Ya | API key dari dashboard HeroSMS | — |
| `HEROSMS_API_BASE_URL` | Tidak | Base URL REST API | `https://hero-sms.com/api/v1` |

## API yang dicakup

Semua endpoint dari OpenAPI spec (`api-en.json`):

- **Activations** — lihat, beli, selesaikan, batalkan, reaktivasi, perpanjang
- **OTP** — terakhir dan daftar per aktivasi
- **Classifiers** — durasi kustom
- **Statistics** — statistik pengguna, deliverability, offers
- **Emails** — daftar, beli, detail, batal, pesan ulang, domain, offers
- **Legacy / SMS-Activate** — endpoint `?action=...` kompatibel SMS-Activate

Lihat `docs/API.md` untuk tabel lengkap.

## Testing

```bash
python3 -m tests.test_herosms
```

Semua tes menggunakan `unittest.mock`, tidak memanggil API nyata.

## Lisensi

MIT
