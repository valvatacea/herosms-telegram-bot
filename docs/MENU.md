# Alur Menu & UX

Navigasi tombol inline bot dari sudut pandang pengguna.

## Menu utama

Ketik `/start` atau `/menu`:

| Tombol | Tujuan |
|--------|--------|
| 💰 Saldo | Saldo — format ikut mata uang (`💵 $x` / `🇮🇩 Rpx`) |
| 📊 Statistik | Statistik aktivasi per negara/layanan (nama) |
| 🛒 Beli Nomor | Mulai flow pembelian (lihat bawah) |
| 📋 Aktif | Daftar aktivasi berjalan (biaya ikut mata uang) |
| 📜 Riwayat | Riwayat aktivasi selesai (14 hari, batas API) |
| ⚙️ Pengaturan | Bahasa, mata uang USD/IDR, auto-batal OTP |
| ❌ Tutup | Tutup menu |

## Flow beli nomor OTP SMS

```
🛒 Beli Nomor
   ↓ Pilih Negara (Indonesia → ASEAN → populer → alfabetis; 15/halaman, 2 kolom, 🔍 cari)
   ↓ Pilih Layanan (Google/sosmed dulu; 15/halaman, 🔍 cari)
   ↓ Pilih Harga (10 termurah dari offers + stok; 💵 USD / 🇮🇩 Rp)
   ↓ Konfirmasi (negara, layanan, harga, durasi 20 menit)
   ✅ Nomor Dibeli (ID, nomor, biaya, kedaluwarsa WIB + bar sisa durasi)
```

Nomor HP hanya ada SETELAH pembelian sukses (di-assign provider saat transaksi).

## Tombol pada aktivasi

| Tombol | Aksi |
|--------|------|
| 📨 OTP Terakhir | OTP terbaru (belum masuk → pesan menunggu, bukan error) |
| 📋 Semua OTP | Seluruh OTP yang pernah masuk |
| 🔄 Kirim Ulang SMS | Minta provider kirim ulang SMS |
| 🔔 / 🔕 Notif OTP | Toggle notifikasi OTP otomatis (default ON) |
| 🚫 OTP Tidak Muncul? Batalkan | Batal + refund (konfirmasi dulu; provider larang <2 menit pertama) |
| ✅ Selesai | Tandai selesai (konfirmasi dulu; tanpa refund) |
| 🔄 Reaktivasi | Hidupkan nomor yang sudah selesai |
| ⬅️ Daftar Aktif / 🏠 Menu Utama | Navigasi |

## Pengaturan

| Tombol | Siklus |
|--------|--------|
| 🌐 Bahasa | 🇮🇩 Indonesia / 🇬🇧 English — seluruh layar, tombol, dan notifikasi ikut bahasa |
| 💵 USD / 🇮🇩 IDR | Mata uang tampilan (default **IDR**; IDR = konversi kurs, cache 24 jam) |
| ⏱ Auto-Batal OTP | NONAKTIF → 5 → 10 → 15 menit (batal otomatis tanpa OTP + refund + notif) |

Catatan: tombol Reaktivasi hanya muncul untuk aktivasi berstatus selesai/dikembalikan (6/10); nomor offline ditolak server dengan pesan ramah ("Nomor Tidak Tersedia").

## Pesan sistem

- Error → kotak `❌` (pesan provider, bukan stack mentah) 
- Sukses → kotak `✅`; konfirmasi destructive → kotak `⚠️`
- Semua render MarkdownV2 di-escape penuh
