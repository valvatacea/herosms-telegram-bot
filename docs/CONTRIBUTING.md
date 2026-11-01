# Panduan Kontribusi

## Tulisan kode

- Bahasa Indonesia untuk komentar dan UI.
- Stdlib dan dependensi terpasang dulu, baru tambah dependensi baru jika perlu.
- Pendekatan terpendek yang bekerja; tidak ada abstraksi untuk satu implementasi.
- Setiap file non-trivial memiliki setidaknya satu tes assert-based di `tests/`.

## Struktur

```
bot/     # Kode utama (paket)
tests/   # Tes assert-based (unittest.mock)
docs/    # Dokumentasi
```

## Menambahkan endpoint API baru

1. Tambah method di `bot/client.py` mengikuti pola yang ada.
2. Tambah handler callback di `bot/main.py` jika perlu tombol.
3. Tambah formatter pesan di `bot/messages.py` jika ada tampilan baru.
4. Tambah tes di `tests/test_herosms.py` dengan `unittest.mock`.
5. Update `docs/API.md`.

## Testing

```bash
python3 -m tests.test_herosms
```

Semua tes harus lolos sebelum commit.

## Commit

Pesan commit dalam bahasa Indonesia, format:

```
<tipe>: <deskripsi singkat>

detail tambahan jika diperlukan
```

Contoh:

```
fix: konfirmasi sebelum aksi destructive finish/cancel
```

## Lisensi

MIT
