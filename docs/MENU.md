# Alur Menu & UX

Dokumen ini menjelaskan navigasi tombol inline bot dari sudut pandang pengguna.

## Menu utama

Ketik `/start` atau `/menu` untuk membuka:

| Tombol | Tujuan |
|--------|--------|
| 💰 Saldo | Lihat saldo tersedia |
| 📊 Statistik | Ringkasan statistik akun |
| 🌍 Negara | Daftar negara untuk beli nomor |
| 📱 Layanan | Daftar layanan verifikasi |
| 💵 Harga | Harga aktivasi per layanan |
| 🛒 Beli Nomor | Mulai flow pembelian nomor (pilih negara → layanan → beli) |
| 📬 Email | Submenu aktivasi email |
| 📋 Aktif | Daftar aktivasi SMS aktif dengan tombol aksi |
| 📜 Riwayat | Daftar riwayat aktivasi selesai |
| ❌ Tutup | Tutup menu |

## Flow beli nomor SMS

```
Menu Utama → 🛒 Beli Nomor → Pilih Negara → Pilih Layanan → Konfirmasi beli
                                                            ↓
                                                    ✅ Nomor Dibeli
                                                    ↓
                                          📨 OTP Terakhir / 📋 Semua OTP
                                          ✅ Selesai / ❌ Batalkan (dikorekansi)
                                          🔄 Reaktivasi / ⏳ Perpanjang
```

Aksi destructive (Selesai, Batalkan) memerlukan konfirmasi dua kali (`Ya, yakin` / `Batalin`) untuk mencegah klik tidak sengaja.

## Flow aktivasi email

```
Menu Utama → 📬 Email → 📧 Domain / 💵 Offers / 📬 Daftar Email
                                      ↓
                                Pilih Domain → Pilih Layanan → Konfirmasi beli
                                                              ↓
                                                        ✅ Aktivasi Email Dibeli
```

Daftar email aktif menampilkan setiap entri sebagai tombol yang dapat diklik untuk melihat detail.

## Detail aktivasi

Setiap aktivasi aktif memiliki tombol:

| Tombol | Aksi |
|--------|------|
| 📨 OTP Terakhir | Lihat kode OTP paling baru |
| 📋 Semua OTP | Lihat seluruh kode OTP |
| ✅ Selesai | Tandai selesai (dikorekansi dulu) |
| ❌ Batalkan | Batalkan & saldo dikembalikan (dikorekansi dulu) |
| 🔄 Reaktivasi | Hidupkan kembali aktivasi |
| ⏳ Perpanjang | Perpanjang masa aktif |

## Pesan sistem

- Pesan error ditampilkan dalam kotak `❌` dan tidak mentah.
- Pesan sukses ditampilkan dalam kotak `✅`.
- Konfirmasi destructive ditampilkan dalam kotak `⚠️`.
