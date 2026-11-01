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


# ── Keyboard pembelian (negara & layanan: populer dulu + paginasi + cari) ──

_COUNTRY_ORDER = (
    ["Indonesia", "Singapore", "Malaysia", "Thailand", "Vietnam", "Philippines",
     "Myanmar", "Cambodia", "Laos", "Brunei"]
    + ["United States", "United Kingdom", "Russia", "China", "India", "Germany",
       "France", "Japan", "South Korea", "Turkey", "Egypt", "Brazil", "Mexico",
       "Nigeria", "Pakistan", "Bangladesh", "Ukraine", "Kazakhstan"]
)
_SERVICE_ORDER = ["google", "whatsapp", "telegram", "facebook", "instagram",
                  "tiktok", "discord", "twitter", "line", "amazon", "apple",
                  "microsoft", "netflix", "spotify", "steam"]


def order_countries(items):
    """Indonesia → ASEAN → populer → sisanya alfabetis."""
    pos = {n.lower(): i for i, n in enumerate(_COUNTRY_ORDER)}
    dicts = [i for i in items if isinstance(i, dict)]
    def key(it):
        n = str(it.get("eng", it.get("name", ""))).lower()
        if n in pos:
            return (0, pos[n])
        return (1, n)
    return sorted(dicts, key=key)


def order_services(items):
    """Layanan populer (sosmed/Google) dulu → sisanya alfabetis."""
    dicts = [i for i in items if isinstance(i, dict)]
    def key(it):
        n = str(it.get("name", "")).lower()
        for j, p in enumerate(_SERVICE_ORDER):
            if n.startswith(p):
                return (0, j)
        return (1, n)
    return sorted(dicts, key=key)


def _page_slice(items, page, per):
    total = max(1, (len(items) + per - 1) // per)
    page = min(max(1, page), total)
    return items[(page - 1) * per:page * per], page, total


def _nav_row(kb, page, total, prefix):
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("‹ Sebelumnya", callback_data=f"{prefix}:{page-1}"))
    if page < total:
        nav.append(InlineKeyboardButton("Berikutnya ›", callback_data=f"{prefix}:{page+1}"))
    if nav:
        kb.add(*nav)


def buy_countries_keyboard(items, page=1, per=15):
    kb = InlineKeyboardMarkup(row_width=2)
    chunk, page, total = _page_slice(order_countries(items), page, per)
    buttons = []
    for item in chunk:
        name = item.get("eng", item.get("name", "-"))
        buttons.append(InlineKeyboardButton(f"{flag(name)} {name}", callback_data=f"buy:country:{item.get('id', item.get('code', '-'))}:{str(name)[:30]}"))
    kb.add(*buttons)
    _nav_row(kb, page, total, "buy:countries")
    kb.add(InlineKeyboardButton(f"🔍 Cari Negara ({page}/{total})", callback_data="buy:search:country"))
    kb.add(InlineKeyboardButton("⬅️ Kembali", callback_data="menu:main"))
    return kb


def buy_services_keyboard(items, page=1, per=15):
    kb = InlineKeyboardMarkup(row_width=2)
    chunk, page, total = _page_slice(order_services(items), page, per)
    buttons = []
    for item in chunk:
        name = item.get("name", "-")
        buttons.append(InlineKeyboardButton(f"📱 {name}", callback_data=f"buy:service:{item.get('id', item.get('code', '-'))}:{str(name)[:30]}"))
    kb.add(*buttons)
    _nav_row(kb, page, total, "buy:services")
    kb.add(InlineKeyboardButton(f"🔍 Cari Layanan ({page}/{total})", callback_data="buy:search:service"))
    kb.add(InlineKeyboardButton("⬅️ Negara", callback_data="menu:buy_activation"))
    return kb


def buy_search_results_keyboard(kind: str, items):
    """Hasil pencarian negara/layanan (max 20)."""
    kb = InlineKeyboardMarkup(row_width=1)
    for item in items[:20]:
        if not isinstance(item, dict):
            continue
        if kind == "country":
            name = item.get("eng", item.get("name", "-"))
            cid = item.get("id", item.get("code", "-"))
            kb.add(InlineKeyboardButton(f"{flag(name)} {name}", callback_data=f"buy:country:{cid}:{str(name)[:30]}"))
        else:
            name = item.get("name", "-")
            sid = item.get("id", item.get("code", "-"))
            kb.add(InlineKeyboardButton(f"📱 {name}", callback_data=f"buy:service:{sid}:{str(name)[:30]}"))
    if kind == "country":
        kb.add(InlineKeyboardButton("⬅️ Semua Negara", callback_data="buy:countries:1"))
    else:
        kb.add(InlineKeyboardButton("⬅️ Semua Layanan", callback_data="buy:services:1"))
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
