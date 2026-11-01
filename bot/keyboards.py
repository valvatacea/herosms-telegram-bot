"""Tombol inline untuk navigasi bot — versi lebih ramah pengguna."""

from __future__ import annotations

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("💰 Saldo", callback_data="menu:balance"),
        InlineKeyboardButton("📊 Statistik", callback_data="menu:stats"),
        InlineKeyboardButton("🌍 Negara", callback_data="menu:countries"),
        InlineKeyboardButton("📱 Layanan", callback_data="menu:services"),
        InlineKeyboardButton("💵 Harga", callback_data="menu:prices"),
        InlineKeyboardButton("🛒 Beli Nomor", callback_data="menu:buy_activation"),
        InlineKeyboardButton("📬 Email", callback_data="menu:email"),
        InlineKeyboardButton("📋 Aktif", callback_data="menu:active"),
        InlineKeyboardButton("📜 Riwayat", callback_data="menu:history"),
        InlineKeyboardButton("💰 Riwayat Transaksi", callback_data="menu:transactions"),
    )
    kb.add(InlineKeyboardButton("❌ Tutup", callback_data="menu:close"))
    return kb


def back_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("⬅️ Kembali ke Menu", callback_data="menu:main"))
    return kb


def activation_actions(activation_id: str, watching: bool = False) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📨 OTP Terakhir", callback_data=f"otp:last:{activation_id}"),
        InlineKeyboardButton("📋 Semua OTP", callback_data=f"otp:list:{activation_id}"),
        InlineKeyboardButton("🔄 Kirim Ulang SMS", callback_data=f"act:resend:{activation_id}"),
        InlineKeyboardButton("🔔 Nyalakan Notif OTP" if not watching else "🔕 Matikan Notif OTP", callback_data=f"otp:watch:{activation_id}"),
        # Destructive actions butuh konfirmasi dulu
        InlineKeyboardButton("✅ Selesai", callback_data=f"act:confirm:finish:{activation_id}"),
        InlineKeyboardButton("❌ Batalkan", callback_data=f"act:confirm:cancel:{activation_id}"),
        InlineKeyboardButton("🔄 Reaktivasi", callback_data=f"act:reactivate:{activation_id}"),
        InlineKeyboardButton("⏳ Perpanjang", callback_data=f"act:prolong:{activation_id}"),
    )
    kb.add(InlineKeyboardButton("⬅️ Daftar Aktif", callback_data="menu:active"))
    kb.add(InlineKeyboardButton("🏠 Menu Utama", callback_data="menu:main"))
    return kb


# ── Keyboard pembelian (negara & layanan, populer dulu) ─────────

POPULAR_COUNTRY_IDS = ["id", "ID", "Indonesia", "indonesia"]
POPULAR_SERVICE_IDS = ["wa", "whatsapp", "tg", "telegram", "fb", "facebook", "ig", "instagram", "sms", "sms-verify"]


def _popular_first(items, popular_ids, id_key="id", name_key="name"):
    """Urutkan item: yang populer dulu, lalu yang lain."""
    popular_set = {str(p).lower() for p in popular_ids}
    pop, rest = [], []
    for it in items:
        if not isinstance(it, dict):
            rest.append(it)
            continue
        vid = str(it.get(id_key, it.get(name_key, ""))).lower()
        (pop if vid in popular_set else rest).append(it)
    return pop + rest


def buy_countries_keyboard(items):
    kb = InlineKeyboardMarkup(row_width=2)
    ordered = _popular_first(items, POPULAR_COUNTRY_IDS)
    buttons = []
    for item in ordered[:20]:
        name = item.get("name", "-")
        cid = item.get("id", item.get("code", "-"))
        is_id = str(cid).lower() in {"id", "indonesia"}
        label = f"🇮🇩 {name}" if is_id else f"🌍 {name}"
        buttons.append(InlineKeyboardButton(label, callback_data=f"buy:country:{cid}"))
    kb.add(*buttons)
    kb.add(InlineKeyboardButton("⬅️ Kembali", callback_data="menu:main"))
    return kb


def buy_services_keyboard(items):
    kb = InlineKeyboardMarkup(row_width=2)
    ordered = _popular_first(items, POPULAR_SERVICE_IDS)
    buttons = []
    for item in ordered[:25]:
        name = item.get("name", "-")
        sid = item.get("id", item.get("code", "-"))
        buttons.append(InlineKeyboardButton(f"📱 {name}", callback_data=f"buy:service:{sid}"))
    kb.add(*buttons)
    kb.add(InlineKeyboardButton("⬅️ Negara", callback_data="menu:buy_activation"))
    return kb


def buy_confirm_keyboard(country: str, service: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ Ya, beli", callback_data=f"buy:confirm:{country}:{service}"),
        InlineKeyboardButton("❌ Batal", callback_data="menu:buy_activation"),
    )
    kb.add(InlineKeyboardButton("🏠 Menu Utama", callback_data="menu:main"))
    return kb


def confirm_keyboard(action: str, activation_id: str) -> InlineKeyboardMarkup:
    """Konfirmasi sebelum tindakan destructive (finish / cancel)."""
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton(
            "✅ Ya, yakin", callback_data=f"confirm:{action}:{activation_id}"
        ),
        InlineKeyboardButton(
            "❌ Batalin", callback_data=f"act:view:{activation_id}"
        ),
    )
    kb.add(InlineKeyboardButton("🏠 Menu Utama", callback_data="menu:main"))
    return kb


def email_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📧 Domain", callback_data="email:domains"),
        InlineKeyboardButton("💵 Offers", callback_data="email:offers"),
        InlineKeyboardButton("📬 Daftar Email", callback_data="email:list"),
    )
    kb.add(InlineKeyboardButton("🏠 Menu Utama", callback_data="menu:main"))
    return kb


# ── Pagination ────────────────────────────────────────────────────

def pagination_keys(page: int, total_pages: int, prefix: str) -> list[InlineKeyboardButton]:
    """Tombol prev/next untuk daftar yang dipaginasi. prefix = 'active'|'history'|'email'."""
    buttons: list[InlineKeyboardButton] = []
    if page > 1:
        buttons.append(InlineKeyboardButton("⬅️ Sebelumnya", callback_data=f"{prefix}:page:{page - 1}"))
    if page < total_pages:
        buttons.append(InlineKeyboardButton("Selanjutnya ➡️", callback_data=f"{prefix}:page:{page + 1}"))
    return buttons


def list_with_pagination(items_per_page: list, page: int, total_pages: int, prefix: str) -> InlineKeyboardMarkup:
    """Keyboard daftar item + tombol navigasi halaman."""
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(*items_per_page)
    nav = pagination_keys(page, total_pages, prefix)
    if nav:
        kb.add(*nav)
    kb.add(InlineKeyboardButton("🏠 Menu Utama", callback_data="menu:main"))
    return kb
