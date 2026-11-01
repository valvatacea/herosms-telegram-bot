"""Tombol inline untuk navigasi bot — ramah pengguna, ID/EN via lang."""

from __future__ import annotations

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot.lang import t
from bot.messages import flag


def main_menu(lang: str = "id") -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton(t(lang, "btn_saldo"), callback_data="menu:balance"),
        InlineKeyboardButton(t(lang, "btn_statistik"), callback_data="menu:stats"),
        InlineKeyboardButton(t(lang, "btn_beli"), callback_data="menu:buy_activation"),
        InlineKeyboardButton(t(lang, "btn_aktif"), callback_data="menu:active"),
        InlineKeyboardButton(t(lang, "btn_riwayat"), callback_data="menu:history"),
    )
    kb.add(InlineKeyboardButton(t(lang, "btn_pengaturan"), callback_data="settings:main"))
    kb.add(InlineKeyboardButton(t(lang, "btn_tutup"), callback_data="menu:close"))
    return kb


def settings_menu(lang: str = "id", currency: str = "idr", autocancel: str = "off") -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    lang_name = t(lang, "bahasa_indo") if lang == "id" else t(lang, "bahasa_inggris")
    if autocancel in ("off", "", None):
        ac_label = t(lang, "autobatal_nonaktif_label")
    else:
        ac_label = t(lang, "autobatal_menit_label", m=autocancel)
    kb.add(InlineKeyboardButton("🌐 {}: {}".format(t(lang, "pengaturan_lang"), lang_name), callback_data="settings:lang"))
    kb.add(
        InlineKeyboardButton("💵 USD" + (" ✅" if currency == "usd" else ""), callback_data="settings:cur:usd"),
        InlineKeyboardButton("🇮🇩 IDR" + (" ✅" if currency == "idr" else ""), callback_data="settings:cur:idr"),
    )
    kb.add(InlineKeyboardButton(t(lang, "autobatal_label", v=ac_label), callback_data="settings:autocancel"))
    kb.add(InlineKeyboardButton(t(lang, "btn_kembali_menu"), callback_data="menu:main"))
    return kb


def settings_lang_menu(current: str = "id", lang: str = "id") -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🇮🇩 " + t(lang, "bahasa_indo") + (" ✅" if current == "id" else ""), callback_data="settings:lang:id"))
    kb.add(InlineKeyboardButton("🇬🇧 " + t(lang, "bahasa_inggris") + (" ✅" if current == "en" else ""), callback_data="settings:lang:en"))
    kb.add(InlineKeyboardButton("⬅️ " + t(lang, "pengaturan_judul"), callback_data="settings:main"))
    return kb


def back_menu(lang: str = "id") -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(t(lang, "btn_kembali_menu"), callback_data="menu:main"))
    return kb


def activation_actions(activation_id: str, watching: bool = False, status=None, lang: str = "id") -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton(t(lang, "btn_otp_terakhir"), callback_data="otp:last:{}".format(activation_id)),
        InlineKeyboardButton(t(lang, "btn_semua_otp"), callback_data="otp:list:{}".format(activation_id)),
        InlineKeyboardButton(t(lang, "btn_resend"), callback_data="act:resend:{}".format(activation_id)),
        InlineKeyboardButton(t(lang, "btn_notif_on") if not watching else t(lang, "btn_notif_off"), callback_data="otp:watch:{}".format(activation_id)),
    )
    # Persis di bawah resend: batalkan bila OTP tidak datang (refund jika belum terima OTP)
    kb.add(InlineKeyboardButton(t(lang, "btn_batal_otp"), callback_data="act:confirm:cancel:{}".format(activation_id)))
    kb.add(
        # Destructive actions butuh konfirmasi dulu
        InlineKeyboardButton(t(lang, "btn_selesai"), callback_data="act:confirm:finish:{}".format(activation_id)),
    )
    # Reaktivasi hanya untuk aktivasi yang sudah selesai (status 6/10);
    # layar tanpa info status (OTP dsb.) menyembunyikannya secara default
    if status is not None and str(status) in ("6", "10"):
        kb.add(InlineKeyboardButton(t(lang, "btn_reaktivasi"), callback_data="act:reactivate:{}".format(activation_id)))
    kb.add(InlineKeyboardButton(t(lang, "btn_daftar_aktif"), callback_data="menu:active"))
    kb.add(InlineKeyboardButton(t(lang, "btn_menu_utama"), callback_data="menu:main"))
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


def _nav_row(kb, page, total, prefix, lang):
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(t(lang, "sebelumnya"), callback_data="{}:{}".format(prefix, page - 1)))
    if page < total:
        nav.append(InlineKeyboardButton(t(lang, "berikutnya"), callback_data="{}:{}".format(prefix, page + 1)))
    if nav:
        kb.add(*nav)


def buy_countries_keyboard(items, page=1, per=15, lang="id"):
    kb = InlineKeyboardMarkup(row_width=2)
    chunk, page, total = _page_slice(order_countries(items), page, per)
    for item in chunk:
        name = item.get("eng", item.get("name", "-"))
        cid = item.get("id", item.get("code", "-"))
        kb.add(InlineKeyboardButton("{} {}".format(flag(name), name), callback_data="buy:country:{}:{}".format(cid, str(name)[:30])))
    _nav_row(kb, page, total, "buy:countries", lang)
    kb.add(InlineKeyboardButton(t(lang, "cari_negara", p=page, t=total), callback_data="buy:search:country"))
    kb.add(InlineKeyboardButton(t(lang, "btn_kembali"), callback_data="menu:main"))
    return kb


def buy_services_keyboard(items, page=1, per=15, lang="id"):
    kb = InlineKeyboardMarkup(row_width=2)
    chunk, page, total = _page_slice(order_services(items), page, per)
    for item in chunk:
        name = item.get("name", "-")
        sid = item.get("id", item.get("code", "-"))
        kb.add(InlineKeyboardButton("📱 {}".format(name), callback_data="buy:service:{}:{}".format(sid, str(name)[:30])))
    _nav_row(kb, page, total, "buy:services", lang)
    kb.add(InlineKeyboardButton(t(lang, "cari_layanan", p=page, t=total), callback_data="buy:search:service"))
    kb.add(InlineKeyboardButton(t(lang, "btn_negara_beli"), callback_data="menu:buy_activation"))
    return kb


def buy_search_results_keyboard(kind: str, items, lang: str = "id") -> InlineKeyboardMarkup:
    """Hasil pencarian negara/layanan (max 20)."""
    kb = InlineKeyboardMarkup(row_width=1)
    for item in items[:20]:
        if not isinstance(item, dict):
            continue
        if kind == "country":
            name = item.get("eng", item.get("name", "-"))
            cid = item.get("id", item.get("code", "-"))
            kb.add(InlineKeyboardButton("{} {}".format(flag(name), name), callback_data="buy:country:{}:{}".format(cid, str(name)[:30])))
        else:
            name = item.get("name", "-")
            sid = item.get("id", item.get("code", "-"))
            kb.add(InlineKeyboardButton("📱 {}".format(name), callback_data="buy:service:{}:{}".format(sid, str(name)[:30])))
    if kind == "country":
        kb.add(InlineKeyboardButton(t(lang, "semua_negara"), callback_data="buy:countries:1"))
    else:
        kb.add(InlineKeyboardButton(t(lang, "semua_layanan"), callback_data="buy:services:1"))
    return kb


def buy_confirm_keyboard(country: str, service: str, lang: str = "id") -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton(t(lang, "btn_ya_beli"), callback_data="buy:confirm:{}:{}".format(country, service)),
        InlineKeyboardButton(t(lang, "btn_batal_beli"), callback_data="menu:buy_activation"),
    )
    kb.add(InlineKeyboardButton(t(lang, "btn_menu_utama"), callback_data="menu:main"))
    return kb


def confirm_keyboard(action: str, activation_id: str, lang: str = "id") -> InlineKeyboardMarkup:
    """Konfirmasi sebelum tindakan destructive (finish / cancel)."""
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton(t(lang, "btn_ya_yakin"), callback_data="confirm:{}:{}".format(action, activation_id)),
        InlineKeyboardButton(t(lang, "btn_batalin"), callback_data="act:view:{}".format(activation_id)),
    )
    kb.add(InlineKeyboardButton(t(lang, "btn_menu_utama"), callback_data="menu:main"))
    return kb


def pagination_keys(page: int, total_pages: int, prefix: str, lang: str = "id") -> list:
    """Tombol prev/next untuk daftar yang dipaginasi. prefix = 'active'|'history'."""
    buttons: list = []
    if page > 1:
        buttons.append(InlineKeyboardButton(t(lang, "sebelumnya"), callback_data="{}:page:{}".format(prefix, page - 1)))
    if page < total_pages:
        buttons.append(InlineKeyboardButton(t(lang, "berikutnya"), callback_data="{}:page:{}".format(prefix, page + 1)))
    return buttons


def list_with_pagination(items_per_page: list, page: int, total_pages: int, prefix: str, lang: str = "id") -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(*items_per_page)
    nav = pagination_keys(page, total_pages, prefix, lang)
    if nav:
        kb.add(*nav)
    kb.add(InlineKeyboardButton(t(lang, "btn_menu_utama"), callback_data="menu:main"))
    return kb
