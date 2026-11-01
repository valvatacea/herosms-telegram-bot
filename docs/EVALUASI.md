# Evaluasi Bot HeroSMS

Tanggal: 2026-11-01 · Commit `37de872` · Cabang `master` (semua tersinkron ke GitHub)

## Metrik kode (pygount)

- **10 file Python, 1.618 baris kode** (+91 baris docstring/komentar)
- `main.py` 877 · `messages.py` 307 · `lang.py` 223 · `keyboards.py` 169 · `client.py` 159 · `state.py` 68 · `config.py` 8
- 116 fungsi total (48 router/handler di `main.py`)
- 93 commit sejak inisialisasi

## Status kualitas

| Item | Status |
|---|---|
| `py_compile` (SyntaxWarning = error) | ✅ bersih |
| Tes (`tests/test_herosms.py`) | ✅ 8/8 |
| Log runtime (`bot.log`) | ✅ 0 Traceback/ERROR |
| Instansi `getUpdates` ganda (409) | ✅ tidak ada (sudah 1 instance) |
| Git status | ✅ clean, `origin/master` sinkron |

## Cakupan fitur

- **Beli nomor OTP SMS** (bukan sewa): negara (195) → layanan (812) → harga → konfirmasi tampil nama negara/layanan, harga sesuai mata uang, durasi → sukses tampil nomor + kedaluwarsa WIB + bar sisa
- **Paginasi** negara 15/hal × 13 hal, layanan 15/hal, 2 kolom; Indonesia → ASEAN → populer dulu
- **Pencarian** negara & layanan (kata bebas, max 20 hasil)
- **OTP**: notifikasi otomatis (poller 30 dtk, default ON), OTP terakhir, daftar OTP, kirim ulang SMS
- **Aksi**: selesai, batalkan (refund, pesan ramah untuk aturan 2 menit), reaktivasi (hidden kecuali status 6/10; pesan ramah SIM_OFFLINE)
- **Auto-batal** tanpa OTP: nonaktif/5/10/15 menit (refund otomatis)
- **i18n** ID/EN penuh: ~160 kunci di `lang.py`, semua layar + notifikasi ikut bahasa
- **Mata uang** USD/IDR per user, default **IDR**; kurs di-cache 24 jam
- **Emoji bendera** 195/195 via pycountry (+12 alias, Kosovo hardcode)
- Multi-instance aman: state via fcntl lock, reload dari disk tiap tulis

## Bug yang diperbaiki (belajar dari sesi ini)

1. `clear_state()` di alur beli ikut menghapus settings → bahasa/mata uang balik default sendiri → diganti `drop_state(kunci buy_*)`
2. Baterai keyboard 1 kolom saat refactor i18n → dikembalikan 2 kolom (`d7e25fb`)
3. 409 conflict dua instance: `kill` ke wrapper bash tidak membunuh child python → restart wajib bunuh PID python eksplisit
4. Escape MarkdownV2: nilai kamus yang melewati `esc()` tidak boleh membawa backslash; yang dipakai raw harus bawa `\| \( \) .` tunggal

## Risiko/sisa utang (sengaja ditunda)

- **Dead code**: `_show_countries/_show_services/_show_prices` + 3 jawaban "dimuat" — tombolnya sudah dihapus dari menu, handler menunggu dibersihkan saat refactor router berikutnya
- **Progress bar sisa durasi** = snapshot statis (Telegram tak mendukung animasi pesan); refresh saat layar dibuka ulang
- **Durasi default 20 menit** diasumsikan untuk semua aktivasi (custom-durations hanya untuk rent) — durasi nyata tetap dihitung dari `expiredAt − createdAt`
- **Tes = plain assert**, tidak terdeteksi `pytest`/`unittest` — jalankan `PYTHONPATH=. .venv/bin/python3 tests/test_herosms.py`
- Saldo riil ~$0.8 → uji beli terbatas; sisa verifikasi fitur berjalan lewat aktivasi murah (IDR Rp652 ≈ $0.036)
