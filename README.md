# HeroSMS Telegram Bot

Bot Telegram untuk **aktivasi OTP SMS** via [HeroSMS](https://hero-sms.com) (REST `/api/v1` OpenAPI 3.2.0 + endpoint legacy SMS-Activate kompatibel). Khusus beli nomor OTP — **bukan sewa (rent)**.

## Fitur

| Fitur | Keterangan |
|-------|------------|
| 💰 Saldo | Cek saldo — ikut setting mata uang: `💵 $0.8234` atau `🇮🇩 Rp14.929` |
| 📊 Statistik | Statistik aktivasi per negara/layanan (nama, bukan kode angka) |
| 🛒 Beli Nomor | Negara → layanan → **daftar harga** → konfirmasi → nomor |
| 📨 OTP | OTP terakhir / daftar OTP, notifikasi otomatis saat OTP masuk |
| 🔄 Kirim Ulang SMS | Minta provider kirim ulang SMS |
| 🚫 Batal Otomatis | Batalkan otomatis bila OTP tidak masuk dalam X menit (atasan di Pengaturan) |
| ✅ Selesai / Batal | Selesaikan (tanpa refund) atau batalkan (refund; konfirmasi dulu) |
| 🔄 Reaktivasi | Aktifkan kembali nomor yang sudah selesai |
| 📋 Aktif / 📜 Riwayat | Aktivasi berjalan & riwayat selesai (14 hari, batas API) |
| ⚙️ Pengaturan | Bahasa (struktur; Indonesia aktif) & mata uang USD/IDR + auto-batal |

### Skema pembelian
1. 🛒 Beli Nomor → daftar negara — urutan: **Indonesia → ASEAN → populer → alfabetis**; 15/halaman, 2 kolom, bendera per negara, `🔍` pencarian
2. Pilih negara → daftar layanan — **Google/sosmed dulu**; 15/halaman, pencarian tersedia
3. Pilih layanan → **daftar harga** dari offers API (10 termurah + stok; label harga ikut setting mata uang)
4. Pilih harga → konfirmasi: negara, layanan, harga, durasi (nomor diberikan setelah beli — nomor HP tidak ada sebelum transaksi)
5. Beli → `POST /activations` dengan `maxPrice` + `fixedPrice` (harga persis pilihanmu) + `verificationType: "sms"`
6. Pesan sukses: ID, nomor, biaya (emot + simbol mata uang), kedaluwarsa WIB + bar sisa durasi, tombol aksi lengkap

## Setup

```bash
git clone https://github.com/valvatacea/herosms-telegram-bot.git
cd herosms-telegram-bot
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # isi BOT_TOKEN dan HEROSMS_API_KEY
python3 -m bot.main    # BUKAN python3 bot/main.py (memutus import bot.config)
```

Untuk log live, jalankan dengan redirect: `python3 -m bot.main > bot.log 2>&1`.

## Variabel lingkungan

| Variabel | Wajib | Keterangan | Default |
|----------|-------|------------|---------|
| `BOT_TOKEN` | Ya | Token dari @BotFather | — |
| `HEROSMS_API_KEY` | Ya | API key akun hero-sms.com | — |
| `HEROSMS_BASE_URL` | Tidak | Base URL REST API | `https://hero-sms.com/api/v1` |

## Struktur

```
herosms-telegram-bot/
├── bot/
│   ├── main.py      # Entry: router callback/command, flow beli, poller OTP, auto-batal
│   ├── client.py    # Klien HeroSMS (REST + legacy /stubs/handler_api.php)
│   ├── messages.py  # Format MarkdownV2: esc, flag emoji, status_name, bar durasi
│   ├── keyboards.py # Inline keyboard: menu, paginasi, pencarian
│   ├── state.py     # Persistence per user (user_state.json)
│   └── config.py    # Baca .env
├── tests/test_herosms.py  # 8 tes, unittest.mock, tanpa API nyata
├── docs/                 # MENU.md, API.md, DEPLOY.md, CONTRIBUTING.md
├── requirements.txt
└── README.md
```

## Catatan teknis

- **Auth**: REST pakai header `Authorization: ApiKey <token>`; legacy pakai query param `api_key`
- **MarkdownV2**: semua teks di-escape; karakter reserved: `_ * [ ] ( ) ~ \` > # + - = | { } . !` — makanya banyak `\\` di source. Label tombol tidak di-parse (jangan escape)
- **Pembelian OTP murni**: tanpa `duration` (param sewa), `verification_type="sms"`
- **Refund**: batalkan sebelum OTP diterima = refund; provider larang batal <2 menit pertama (`EARLY_CANCEL_DENIED`); tanpa OTP hingga expired → refund otomatis
- **Durasi aktivasi**: default 20 menit; custom-durations itu untuk produk sewa/kustom, tidak dipakai
- **Kurs IDR**: open.er-api.com (gratis tanpa key; cache 24 jam)
- **Bendera negara**: `pycountry` nama → ISO 2 huruf → emoji; alias untuk nama pendek ("DR Congo", "UAE", dst.); Kosovo di-hardcode 🇽🇰
- **Riwayat provider**: hanya aktivasi yang benar-benar menerima OTP/berstatus selesai — batal/expired tanpa OTP tidak tercatat
- **State**: `user_state.json` (gitignored) — purchases, OTP watch, halaman, settings per user

## Tes

```bash
PYTHONPATH=. python3 tests/test_herosms.py
```

## Lisensi

MIT
