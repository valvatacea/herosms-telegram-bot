"""Tombol inline untuk navigasi bot — versi lebih ramah pengguna."""

from __future__ import annotations

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot.messages import flag


def main_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("💰 Saldo", callback_data="menu:balance"),
        InlineKeyboardButton("📊 Statistik", callback_data="menu:stats"),
        InlineKeyboardButton("🛒 Beli Nomor", callback_data="menu:buy_activation"),
        InlineKeyboardButton("📬 Email", callback_data="menu:email"),
        InlineKeyboardButton("📋 Aktif", callback_data="menu:active"),
        InlineKeyboardButton("📜 Riwayat", callback_data="menu:history"),
    )
    kb.add(InlineKeyboardButton("⚙️ Pengaturan", callback_data="settings:main"))
    kb.add(InlineKeyboardButton("❌ Tutup", callback_data="menu:close"))
    return kb


def settings_menu(lang: str = "id", currency: str = "usd", autocancel: str = "off") -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    lang_name = "Indonesia" if lang == "id" else "English"
    ac_label = "NONAKTIF" if autocancel in ("off", "", None) else f"{autocancel} MENIT"
    kb.add(InlineKeyboardButton(f"🌐 Bahasa: {lang_name}", callback_data="settings:lang"))
    kb.add(
        InlineKeyboardButton("💵 USD" + (" ✅" if currency == "usd" else ""), callback_data="settings:cur:usd"),
        InlineKeyboardButton("🇮🇩 IDR" + (" ✅" if currency == "idr" else ""), callback_data="settings:cur:idr"),
    )
    kb.add(InlineKeyboardButton(f"⏱ Auto-Batal OTP: {ac_label}", callback_data="settings:autocancel"))
    kb.add(InlineKeyboardButton("⬅️ Kembali ke Menu", callback_data="menu:main"))
    return kb


def settings_lang_menu(current: str = "id") -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🇮🇩 Indonesia" + (" ✅" if current == "id" else ""), callback_data="settings:lang:id"))
    kb.add(InlineKeyboardButton("🇬🇧 English (segera)", callback_data="settings:lang:soon"))
    kb.add(InlineKeyboardButton("⬅️ Pengaturan", callback_data="settings:main"))
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
    )
    # Persis di bawah resend: batalkan bila OTP tidak datang (refund jika belum terima OTP)
    kb.add(InlineKeyboardButton("🚫 OTP Tidak Muncul? Batalkan", callback_data=f"act:confirm:cancel:{activation_id}"))
    kb.add(
        # Destructive actions butuh konfirmasi dulu
        InlineKeyboardButton("✅ Selesai", callback_data=f"act:confirm:finish:{activation_id}"),
        InlineKeyboardButton("🔄 Reaktivasi", callback_data=f"act:reactivate:{activation_id}"),
    )
    kb.add(InlineKeyboardButton("⬅️ Daftar Aktif", callback_data="menu:active"))
    kb.add(InlineKeyboardButton("🏠 Menu Utama", callback_data="menu:main"))
    return kb


# ── Keyboard pembelian (negara & layanan, populer dulu) ─────────

POPULAR_COUNTRY_IDS = ["6", "id", "ID", "Indonesia", "indonesia"]
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
        if isinstance(item, dict):
            name = item.get("eng", item.get("name", "-"))
            cid = item.get("id", item.get("code", "-"))
        else:
            name = str(item)
            cid = str(item)
        label = f"{flag(name)} {name}"
        buttons.append(InlineKeyboardButton(label, callback_data=f"buy:country:{cid}:{str(name)[:30]}"))
    kb.add(*buttons)
    kb.add(InlineKeyboardButton("⬅️ Kembali", callback_data="menu:main"))
    return kb


def buy_services_keyboard(items):
    kb = InlineKeyboardMarkup(row_width=2)
    ordered = _popular_first(items, POPULAR_SERVICE_IDS)
    buttons = []
    for item in ordered[:25]:
        if isinstance(item, dict):
            name = item.get("name", "-")
            sid = item.get("id", item.get("code", "-"))
        else:
            name = str(item)
            sid = str(item)
        buttons.append(InlineKeyboardButton(f"📱 {name}", callback_data=f"buy:service:{sid}:{str(name)[:30]}"))
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
