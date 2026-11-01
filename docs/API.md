# Referensi API HeroSMS

Endpoint yang dipakai klien `bot/client.py`. Base URL REST: `https://hero-sms.com/api/v1`, legacy: `https://hero-sms.com/stubs/handler_api.php`.

## Activations

| Method | Path | Fungsi klien | Keterangan |
|--------|------|--------------|------------|
| GET | `/activations` | `active_activations()` | Daftar aktivasi aktif (paginasi, search) |
| GET | `/activations/history` | `activation_history()` | Riwayat (wajib `from`+`to`, maks 2 minggu) |
| POST | `/activations` | `buy_activation()` | Beli — service, country, amount, maxPrice, fixedPrice, verificationType |
| DELETE | `/activations/{id}` | `cancel_activation()` | Batal + refund (syarat: belum terima OTP; dilarang 2 menit pertama) |
| POST | `/activations/{id}/finish` | `finish_activation()` | Tandai selesai (tanpa refund) |
| POST | `/activations/{id}/reactivate` | `reactivate_activation()` | Reaktivasi nomor selesai |
| GET | `/activations/{id}/otp/last` | `otp_last()` | OTP terakhir (belum ada -> 400 STATUS_WAIT_CODE) |
| GET | `/activations/{id}/otp` | `otp_list()` | Daftar OTP |

## Statistics & Offers

| Method | Path | Fungsi klien | Keterangan |
|--------|------|--------------|------------|
| GET | `/activations/stats` | `user_stats()` | Statistik per negara/layanan |
| GET | `/activations/offers/{vt}` | `offers(vt, services, countries)` | Daftar harga + stok (layar harga beli) |

## Emails

| Method | Path | Fungsi klien | Keterangan |
|--------|------|--------------|------------|
| GET | `/emails` | `email_list()` | Daftar aktivasi email |
| POST | `/emails` | `buy_email_activation()` | Beli (domain, service) |
| GET | `/emails/{id}` | `email_detail()` | Detail |
| DELETE | `/emails/{id}` | `cancel_email()` | Batal |
| POST | `/emails/{id}/reorder` | `reorder_email()` | Pesan ulang |
| GET | `/emails/domains` | `email_domains(site)` | Domain (WAJIB param `site`) |
| GET | `/emails/offers` | `email_offers(site)` | Offers (WAJIB param `site`) |

## SMS-Activate Compatible (Legacy)

| Fungsi klien | Keterangan |
|--------------|------------|
| `legacy(action, params)` | `?action=...` — getBalance (teks `ACCESS_BALANCE:x`), getCountries (dict `{id: {eng,...}}`), getServicesList (`{services:[{code,name}]}`), getPrices (`{country:{service:{cost,count}}}`) |
| `resend_sms(id)` | `?action=setStatus` status=3 — kirim ulang SMS |

## Autentikasi

- REST: header `Authorization: ApiKey <token>` (BUKAN `Bearer` — per OpenAPI spec)
- Legacy: query param `api_key`

## Contoh

```python
from bot.client import HeroSMS

api = HeroSMS("API_KEY_ANDA", "https://hero-sms.com/api/v1")

saldo = api.get_balance()["balance"]                     # 0.8234 (USD)
harga = api.offers("sms", services="tg", countries="6")  # map harga Telegram Indonesia
act = api.buy_activation(service="tg", country="6",
                         max_price=0.102, fixed_price=True,
                         verification_type="sms")        # respons dibungkus {"data": [...]}
otp = api.otp_last(str(act["id"]))
```
