# Referensi API HeroSMS

Semua endpoint dari OpenAPI 3.2.0 (`api-en.json`, HeroSMS v1.0) yang dicakup oleh klien `bot/client.py`.

Base URL: `https://hero-sms.com/api/v1`

## Activations

| Method | Path | Fungsi klien | Keterangan |
|--------|------|--------------|------------|
| GET | `/activations` | `active_activations()` | Daftar aktivasi aktif |
| GET | `/activations/history` | `activation_history()` | Riwayat aktivasi (filter tanggal, layanan, negara, status) |
| POST | `/activations` | `buy_activation()` | Beli nomor verifikasi baru |
| DELETE | `/activations/{id}` | `cancel_activation()` | Batalkan aktivasi |
| POST | `/activations/{id}/finish` | `finish_activation()` | Tandai aktivasi selesai |
| POST | `/activations/{id}/replace` | `replace_activation()` | Ganti nomor aktivasi |
| POST | `/activations/{id}/reactivate` | `reactivate_activation()` | Reaktivasi aktivasi |
| GET | `/activations/{id}/reactivate/options` | `reactivate_options()` | Opsi reaktivasi |
| POST | `/activations/{id}/prolong` | `prolong_activation()` | Perpanjang masa aktif |
| GET | `/activations/{id}/prolong/options` | `prolong_options()` | Opsi perpanjangan |
| GET | `/activations/{id}/prolong/history` | `prolong_history()` | Riwayat perpanjangan |
| GET | `/activations/{id}/otp/last` | `otp_last()` | OTP terakhir |
| GET | `/activations/{id}/otp` | `otp_list()` | Daftar seluruh OTP |

## Classifiers

| Method | Path | Fungsi klien | Keterangan |
|--------|------|--------------|------------|
| GET | `/classifiers/activations/custom-durations` | `custom_durations()` | Durasi kustom perpanjang |

## Statistics

| Method | Path | Fungsi klien | Keterangan |
|--------|------|--------------|------------|
| GET | `/activations/stats` | `user_stats()` | Statistik pengguna & saldo |
| GET | `/stats/deliverability` | `deliverability_stats()` | Statistik deliverability |
| GET | `/activations/offers/{verification_type}` | `offers()` | Offer per tipe verifikasi |

## Emails

| Method | Path | Fungsi klien | Keterangan |
|--------|------|--------------|------------|
| GET | `/emails` | `email_list()` | Daftar aktivasi email aktif |
| POST | `/emails` | `buy_email_activation()` | Beli aktivasi email |
| GET | `/emails/{id}` | `email_detail()` | Detail aktivasi email |
| DELETE | `/emails/{id}` | `cancel_email()` | Batalkan aktivasi email |
| POST | `/emails/{id}/reorder` | `reorder_email()` | Pesan ulang email |
| GET | `/emails/domains` | `email_domains()` | Daftar domain email |
| GET | `/emails/offers` | `email_offers()` | Offer email |

## SMS-Activate Compatible (Legacy)

| Method | Path | Fungsi klien | Keterangan |
|--------|------|--------------|------------|
| GET | `/stubs/handler_api.php?action=setStatus` | `resend_sms(activation_id)` | Minta pengiriman ulang SMS (status 3) |
| GET | `/stubs/handler_api.php?action=...` | `legacy(action, params)` | Endpoint kompatibel SMS-Activate (getCountries, getServicesList, getPrices, dst.) |

## Autentikasi

API key dikirim via header `Authorization: Bearer <api_key>` pada endpoint REST. Untuk endpoint legacy, API key dikirim sebagai query parameter `api_key`.

## Contoh penggunaan

```python
from bot.client import HeroSMS

api = HeroSMS("API_KEY_ANDa", "https://hero-sms.com/api/v1")

# Cek saldo
stats = api.user_stats()
print(stats)

# Beli nomor WhatsApp di Indonesia
act = api.buy_activation(service="wa", country="id")
print(act["phone"])

# Ambil OTP terakhir
otp = api.otp_last(str(act["id"]))
print(otp["code"])
```
