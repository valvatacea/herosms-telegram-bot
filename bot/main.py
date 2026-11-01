"""Bot Telegram untuk HeroSMS — coverage seluruh OpenAPI spec (api-en.json).
Versi lebih ramah pengguna: konfirmasi sebelum aksi destructive,
pesan error ramah, dan navigasi yang konsisten."""

from __future__ import annotations

import logging
import time
from typing import Dict

import telebot
from telebot.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from bot.config import BOT_TOKEN, HEROSMS_API_KEY, HEROSMS_BASE_URL
from bot.client import HeroSMS, HeroSMSError
from bot.keyboards import (
    main_menu,
    back_menu,
    activation_actions,
    confirm_keyboard,
    email_menu,
    buy_countries_keyboard,
    buy_services_keyboard,
    buy_confirm_keyboard,
    pagination_keys,
    list_with_pagination,
)
from bot.messages import (
    esc,
    balance_msg,
    stats_msg,
    countries_msg,
    services_msg,
    prices_msg,
    activation_detail,
    active_list_msg,
    history_msg,
    otp_msg,
    purchase_success,
    welcome_msg,
    email_list_msg,
    email_detail_msg,
    confirm_msg,
    buy_confirm_msg,
    error_msg,
    success_msg,
)
from bot.state import user_state, set_state, get_state, clear_state

# ── Helper halaman state ──────────────────────────────────────────

def _get_page(uid: int, list_name: str, aid: str | None = None) -> int:
    pages = get_state(uid, "pages", {}) or {}
    if aid:
        otp_pages = pages.get("otp", {}) or {}
        return int(otp_pages.get(aid, 1))
    return int(pages.get(list_name, 1))


def _set_page(uid: int, list_name: str, page: int, aid: str | None = None) -> None:
    pages = get_state(uid, "pages", {}) or {}
    if aid:
        otp_pages = pages.get("otp", {}) or {}
        otp_pages[aid] = page
        pages["otp"] = otp_pages
    else:
        pages[list_name] = page
    set_state(uid, "pages", pages)


def _total_pages_from(data: dict, page: int, size: int) -> int:
    """Estimasi total halaman dari respons API. Default: page (+1 jika penuh)."""
    if not isinstance(data, dict):
        return page
    for key in ("total", "totalPages", "pages", "last_page"):
        if key in data:
            try:
                return max(1, int(data[key]))
            except (ValueError, TypeError):
                pass
    meta = data.get("meta")
    if isinstance(meta, dict):
        for key in ("total", "totalPages", "pages", "last_page"):
            if key in meta:
                try:
                    return max(1, int(meta[key]))
                except (ValueError, TypeError):
                    pass
    items = data.get("data", [])
    if isinstance(items, list) and len(items) >= size:
        return page + 1
    return page


# ── OTP watch (notifikasi otomatis) ───────────────────────────────

def _get_watch(uid: int) -> dict:
    return get_state(uid, "otp_watch", {}) or {}


def _is_watching(uid: int, aid: str) -> bool:
    return aid in (_get_watch(uid) or {})


def _watch_toggle(uid: int, aid: str) -> bool:
    """Toggle watch. Return True jika sekarang sedang di-watch."""
    watch = _get_watch(uid)
    if aid in watch:
        del watch[aid]
        set_state(uid, "otp_watch", watch)
        return False
    watch[aid] = None
    set_state(uid, "otp_watch", watch)
    return True


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("herosms-bot")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="MarkdownV2")
api = HeroSMS(HEROSMS_API_KEY, HEROSMS_BASE_URL)


def _answer(call: CallbackQuery, text: str, alert: bool = False) -> None:
    bot.answer_callback_query(call.id, text, show_alert=alert)


def _edit(chat: int, msg_id: int, text: str, markup=None) -> None:
    try:
        bot.edit_message_text(text, chat, msg_id, reply_markup=markup)
    except Exception:
        bot.send_message(chat, text, reply_markup=markup)


# ── Command ─────────────────────────────────────────────────────

@bot.message_handler(commands=["start"])
def cmd_start(message: Message) -> None:
    bot.reply_to(message, welcome_msg(), reply_markup=main_menu())


@bot.message_handler(commands=["menu"])
def cmd_menu(message: Message) -> None:
    bot.send_message(message.chat.id, "Menu utama", reply_markup=main_menu())


@bot.message_handler(commands=["help"])
def cmd_help(message: Message) -> None:
    text = (
        "🔹 *Bantuan*\n"
        "Perintah yang tersedia:\n"
        "\n"
        "/start — menu utama\n"
        "/menu — buka menu utama\n"
        "/help — panduan ini\n"
        "\n"
        "Fitur:\n"
        "• 💰 Saldo & statistik akun\n"
        "• 🌍 Negara, layanan, harga\n"
        "• 🛒 Beli nomor verifikasi (SMS/email)\n"
        "• 📨 OTP terakhir / daftar OTP\n"
        "• ✅ Selesai · ❌ Batalkan · 🔄 Reaktivasi · ⏳ Perpanjang\n"
    )
    bot.reply_to(message, text, reply_markup=main_menu())


# ── Callback router ─────────────────────────────────────────────

@bot.callback_query_handler(func=lambda call: True)
def on_callback(call: CallbackQuery) -> None:
    data = call.data or ""
    uid = call.from_user.id
    chat = call.message.chat.id
    msg_id = call.message.message_id

    try:
        if data == "menu:main":
            _edit(chat, msg_id, welcome_msg(), main_menu())
            _answer(call, "Menu utama")

        elif data == "menu:close":
            bot.edit_message_text("Menu ditutup. Ketik /start untuk buka kembali.", chat, msg_id)
            _answer(call, "Ditutup")

        elif data == "menu:balance":
            _show_balance(chat, msg_id, call)

        elif data == "menu:stats":
            _show_stats(chat, msg_id, call)

        elif data == "menu:countries":
            _show_countries(chat, msg_id, call)

        elif data == "menu:services":
            _show_services(chat, msg_id, call)

        elif data == "menu:prices":
            _show_prices(chat, msg_id, call)

        elif data == "menu:buy_activation":
            _start_buy_flow(chat, msg_id, uid, call)

        elif data == "menu:email":
            _show_email_menu(chat, msg_id, call)

        elif data == "menu:active":
            _show_active(chat, msg_id, call, page=1)

        elif data == "menu:history":
            _show_history(chat, msg_id, call, page=1)

        elif data == "menu:transactions":
            _show_transactions(chat, msg_id, call)

        elif data.startswith("buy:country:"):
            country = data.split(":", 2)[2]
            set_state(uid, "buy_country", country)
            _show_services_for_buy(chat, msg_id, uid, country, call)

        elif data.startswith("buy:service:"):
            service = data.split(":", 2)[2]
            _show_buy_confirm(chat, msg_id, uid, service, call)

        elif data.startswith("buy:confirm:"):
            parts = data.split(":", 3)
            country = parts[2]
            service = parts[3]
            _do_purchase(chat, msg_id, uid, service, country, call)

        elif data.startswith("otp:last:"):
            aid = data.split(":", 2)[2]
            _show_otp_last(chat, msg_id, aid, call)

        elif data.startswith("otp:list:"):
            aid = data.split(":", 2)[2]
            _show_otp_list(chat, msg_id, aid, call, page=1)

        elif data.startswith("otp:watch:"):
            aid = data.split(":", 2)[2]
            now_watching = _watch_toggle(uid, aid)
            _show_activation_detail(chat, msg_id, aid, call)

        elif data.startswith("active:page:"):
            page = int(data.split(":", 2)[2])
            _show_active(chat, msg_id, call, page=page)

        elif data.startswith("history:page:"):
            page = int(data.split(":", 2)[2])
            _show_history(chat, msg_id, call, page=page)

        elif data.startswith("email:page:"):
            page = int(data.split(":", 2)[2])
            _show_email_list(chat, msg_id, call, page=page)

        elif data.startswith("otp:page:"):
            parts = data.split(":", 3)
            aid = parts[2]
            page = int(parts[3])
            _show_otp_list(chat, msg_id, aid, call, page=page)

        elif data.startswith("act:view:"):
            aid = data.split(":", 2)[2]
            _show_activation_detail(chat, msg_id, aid, call)

        # Konfirmasi sebelum aksi destructive
        elif data.startswith("act:confirm:finish:"):
            aid = data.split(":", 3)[3]
            _show_confirm_finish(chat, msg_id, aid, call)

        elif data.startswith("act:confirm:cancel:"):
            aid = data.split(":", 3)[3]
            _show_confirm_cancel(chat, msg_id, aid, call)

        # Eksekusi setelah konfirmasi
        elif data.startswith("confirm:finish:"):
            aid = data.split(":", 2)[2]
            _do_finish(chat, msg_id, aid, call)

        elif data.startswith("confirm:cancel:"):
            aid = data.split(":", 2)[2]
            _do_cancel(chat, msg_id, aid, call)

        elif data.startswith("act:reactivate:"):
            aid = data.split(":", 2)[2]
            _do_reactivate(chat, msg_id, aid, call)

        elif data.startswith("act:prolong:"):
            aid = data.split(":", 2)[2]
            _do_prolong(chat, msg_id, aid, call)

        elif data.startswith("email:domains"):
            _show_email_domains(chat, msg_id, call)

        elif data.startswith("email:offers"):
            _show_email_offers(chat, msg_id, call)

        elif data.startswith("email:list"):
            _show_email_list(chat, msg_id, call, page=1)

        elif data.startswith("email:buy:"):
            domain = data.split(":", 2)[2]
            set_state(uid, "email_domain", domain)
            _show_email_services_for_buy(chat, msg_id, uid, domain, call)

        elif data.startswith("email:service:"):
            service = data.split(":", 2)[2]
            _do_email_purchase(chat, msg_id, uid, service, call)

        elif data.startswith("email:detail:"):
            eid = data.split(":", 2)[2]
            _show_email_detail(chat, msg_id, eid, call)

        elif data.startswith("email:cancel:"):
            eid = data.split(":", 2)[2]
            _do_email_cancel(chat, msg_id, eid, call)

        elif data.startswith("email:reorder:"):
            eid = data.split(":", 2)[2]
            _do_email_reorder(chat, msg_id, eid, call)

        else:
            _answer(call, "Tombol tidak dikenal.", alert=True)

    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Permintaan Gagal", str(exc)), back_menu())
        _answer(call, f"Error: {exc}", alert=True)
    except Exception as exc:  # noqa: BLE001
        log.exception("callback error")
        _edit(chat, msg_id, error_msg("Error Tak Terduga", str(exc)), back_menu())
        _answer(call, str(exc), alert=True)


# ── Helper tampilan ─────────────────────────────────────────────

def _show_balance(chat: int, msg_id: int, call: CallbackQuery) -> None:
    try:
        data = api.user_stats()
        _edit(chat, msg_id, balance_msg(data), back_menu())
        _answer(call, "Saldo dimuat")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Cek Saldo", str(exc)), back_menu())
        _answer(call, str(exc), alert=True)


def _show_stats(chat: int, msg_id: int, call: CallbackQuery) -> None:
    try:
        data = api.user_stats()
        _edit(chat, msg_id, stats_msg(data), back_menu())
        _answer(call, "Statistik dimuat")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Cek Statistik", str(exc)), back_menu())
        _answer(call, str(exc), alert=True)


def _show_countries(chat: int, msg_id: int, call: CallbackQuery) -> None:
    try:
        data = api.legacy("getCountries")
        _edit(chat, msg_id, countries_msg(data), back_menu())
        _answer(call, "Negara dimuat")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Muat Negara", str(exc)), back_menu())
        _answer(call, str(exc), alert=True)


def _show_services(chat: int, msg_id: int, call: CallbackQuery) -> None:
    try:
        data = api.legacy("getServicesList")
        _edit(chat, msg_id, services_msg(data), back_menu())
        _answer(call, "Layanan dimuat")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Muat Layanan", str(exc)), back_menu())
        _answer(call, str(exc), alert=True)


def _show_prices(chat: int, msg_id: int, call: CallbackQuery) -> None:
    try:
        data = api.legacy("getPrices")
        _edit(chat, msg_id, prices_msg(data), back_menu())
        _answer(call, "Harga dimuat")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Muat Harga", str(exc)), back_menu())
        _answer(call, str(exc), alert=True)


def _start_buy_flow(chat: int, msg_id: int, uid: int, call: CallbackQuery) -> None:
    try:
        data = api.legacy("getCountries")
        items = data.get("data", data) if isinstance(data, dict) else data
        _edit(chat, msg_id, "🔹 *Beli Nomor*\n\nPilih negara (Indonesia ditampilkan paling atas):", buy_countries_keyboard(items))
        _answer(call, "Pilih negara")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Muat Negara", str(exc)), back_menu())
        _answer(call, str(exc), alert=True)


def _show_services_for_buy(chat: int, msg_id: int, uid: int, country: str, call: CallbackQuery) -> None:
    try:
        set_state(uid, "buy_country", country)
        data = api.legacy("getServicesList")
        items = data.get("data", data) if isinstance(data, dict) else data
        _edit(
            chat,
            msg_id,
            f"🔹 *Layanan - {country}*\n\nPilih layanan (populer ditampilkan paling atas):",
            buy_services_keyboard(items),
        )
        _answer(call, "Pilih layanan")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Muat Layanan", str(exc)), back_menu())
        _answer(call, str(exc), alert=True)


def _lookup_price(country: str, service: str) -> tuple[str, str]:
    """Coba ambil harga dari legacy getPrices. Kembalikan (price, currency).
    
    Coba beberapa bentuk respons yang mungkin sebelum gagarkan '-'."""
    try:
        data = api.legacy("getPrices")
        if not isinstance(data, dict):
            return "-", ""

        country_l = country.lower()
        service_l = service.lower()

        # Format 1: {data: [{service, country, price, currency}, ...]}
        if isinstance(data.get("data"), list):
            for item in data["data"]:
                if not isinstance(item, dict):
                    continue
                if (str(item.get("service", "")).lower() == service_l
                        and str(item.get("country", "")).lower() == country_l):
                    return str(item.get("price", "-")), str(item.get("currency", ""))

        # Helper: cocokkan key dalam nested dict
        def _match_nested(outer):
            for k, v in outer.items():
                if not isinstance(v, dict):
                    continue
                if str(k).lower() == service_l:
                    for ck, cv in v.items():
                        if str(ck).lower() == country_l:
                            return _extract_price(cv)
                if str(k).lower() == country_l:
                    for sk, sv in v.items():
                        if str(sk).lower() == service_l:
                            return _extract_price(sv)
            return None

        def _extract_price(val):
            if isinstance(val, dict):
                return str(val.get("price", "-")), str(val.get("currency", ""))
            return str(val), ""

        # Format 2: {service: {country: price}} / {country: {service: price}}
        result = _match_nested(data)
        if result:
            return result

        # Format 3: flat {service_country: price}
        for k, v in data.items():
            if f"{service}_{country}".lower() == str(k).lower():
                return str(v), ""

    except Exception:  # noqa: BLE001
        pass
    return "-", ""


def _show_buy_confirm(chat: int, msg_id: int, uid: int, service: str, call: CallbackQuery) -> None:
    country = get_state(uid, "buy_country") or "-"
    price, currency = _lookup_price(country, service)
    set_state(uid, "buy_service", service)
    set_state(uid, "buy_price", price)
    set_state(uid, "buy_currency", currency)
    _edit(
        chat,
        msg_id,
        buy_confirm_msg(country, service, price, currency),
        buy_confirm_keyboard(country, service),
    )
    _answer(call, "Konfirmasi pembelian")


def _do_purchase(chat: int, msg_id: int, uid: int, service: str, country: str | None = None, call: CallbackQuery | None = None) -> None:
    if country is None:
        country = get_state(uid, "buy_country")
    try:
        act = api.buy_activation(service=service, country=country)
        # Rekam transaksi
        price = get_state(uid, "buy_price", "-")
        currency = get_state(uid, "buy_currency", "")
        pur = {
            "service": service,
            "country": country or "-",
            "price": price,
            "currency": currency,
            "activation_id": str(act.get("id", "")),
            "time": time.strftime("%Y-%m-%d %H:%M"),
        }
        pops = get_state(uid, "purchases", []) or []
        pops.append(pur)
        set_state(uid, "purchases", pops)
        clear_state(uid)
        if call:
            _edit(chat, msg_id, purchase_success(act), activation_actions(str(act.get("id", "")), watching=False))
            _answer(call, "Nomor dibeli")
        else:
            bot.send_message(chat, purchase_success(act), reply_markup=activation_actions(str(act.get("id", "")), watching=False))
    except HeroSMSError as exc:
        if call:
            _edit(chat, msg_id, error_msg("Gagal Beli Nomor", str(exc)), back_menu())
            _answer(call, str(exc), alert=True)
        else:
            bot.send_message(chat, error_msg("Gagal Beli Nomor", str(exc)), reply_markup=back_menu())


# ── Konfirmasi aksi destructive ─────────────────────────────────

def _show_confirm_finish(chat: int, msg_id: int, aid: str, call: CallbackQuery) -> None:
    _edit(
        chat,
        msg_id,
        confirm_msg("Selesaikan Aktivasi", f"Aktivasi ID {aid} akan ditandai selesai."),
        confirm_keyboard("finish", aid),
    )
    _answer(call, "Konfirmasi selesai")


def _show_confirm_cancel(chat: int, msg_id: int, aid: str, call: CallbackQuery) -> None:
    _edit(
        chat,
        msg_id,
        confirm_msg("Batalkan Aktivasi", f"Aktivasi ID {aid} akan dibatalkan dan saldo dikembalikan."),
        confirm_keyboard("cancel", aid),
    )
    _answer(call, "Konfirmasi batalkan")


# ── Eksekusi aksi ───────────────────────────────────────────────

def _do_finish(chat: int, msg_id: int, aid: str, call: CallbackQuery) -> None:
    try:
        api.finish_activation(aid)
        _edit(chat, msg_id, success_msg("Aktivasi Selesai", f"Aktivasi ID {aid} telah diselesaikan."), back_menu())
        _answer(call, "Selesai")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Selesaikan", str(exc)), activation_actions(aid, watching=_is_watching(uid, aid)))
        _answer(call, str(exc), alert=True)


def _do_cancel(chat: int, msg_id: int, aid: str, call: CallbackQuery) -> None:
    try:
        api.cancel_activation(aid)
        _edit(chat, msg_id, success_msg("Aktivasi Dibatalkan", f"Aktivasi ID {aid} telah dibatalkan."), back_menu())
        _answer(call, "Dibatalkan")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Batalkan", str(exc)), activation_actions(aid, watching=_is_watching(uid, aid)))
        _answer(call, str(exc), alert=True)


def _do_reactivate(chat: int, msg_id: int, aid: str, call: CallbackQuery) -> None:
    try:
        api.reactivate_activation(aid)
        _edit(chat, msg_id, success_msg("Aktivasi Di-reaktivasi", f"Aktivasi ID {aid} telah di-reaktivasi."), activation_actions(aid, watching=_is_watching(uid, aid)))
        _answer(call, "Di-reaktivasi")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Reaktivasi", str(exc)), activation_actions(aid, watching=_is_watching(uid, aid)))
        _answer(call, str(exc), alert=True)


def _do_prolong(chat: int, msg_id: int, aid: str, call: CallbackQuery) -> None:
    try:
        api.prolong_activation(aid)
        _edit(chat, msg_id, success_msg("Aktivasi Diperpanjang", f"Aktivasi ID {aid} telah diperpanjang."), activation_actions(aid, watching=_is_watching(uid, aid)))
        _answer(call, "Diperpanjang")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Perpanjang", str(exc)), activation_actions(aid, watching=_is_watching(uid, aid)))
        _answer(call, str(exc), alert=True)


# ── Email ───────────────────────────────────────────────────────

def _show_email_menu(chat: int, msg_id: int, call: CallbackQuery) -> None:
    _edit(chat, msg_id, "🔹 *Aktivasi Email*\n\nManajemen aktivasi via email:", email_menu())
    _answer(call, "Menu email")


def _show_email_domains(chat: int, msg_id: int, call: CallbackQuery) -> None:
    try:
        data = api.email_domains()
        items = data.get("data", data) if isinstance(data, dict) else data
        kb = telebot.types.InlineKeyboardMarkup(row_width=2)
        buttons = []
        for item in items[:20]:
            if isinstance(item, dict):
                name = item.get("name", "-")
                did = item.get("id", item.get("domain", "-"))
                buttons.append(telebot.types.InlineKeyboardButton(
                    f"📧 {name}", callback_data=f"email:buy:{did}"))
        kb.add(*buttons)
        kb.add(telebot.types.InlineKeyboardButton("⬅️ Kembali", callback_data="menu:email"))
        _edit(chat, msg_id, "🔹 *Domain Email*\n\nPilih domain:", kb)
        _answer(call, "Domain dimuat")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Muat Domain", str(exc)), back_menu())
        _answer(call, str(exc), alert=True)


def _show_email_offers(chat: int, msg_id: int, call: CallbackQuery) -> None:
    try:
        data = api.email_offers()
        _edit(chat, msg_id, prices_msg(data), back_menu())
        _answer(call, "Offers dimuat")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Muat Offers", str(exc)), back_menu())
        _answer(call, str(exc), alert=True)


def _show_email_list(chat: int, msg_id: int, call: CallbackQuery, page: int = 1) -> None:
    uid = call.from_user.id
    size = 15
    try:
        data = api.email_list(page=page, size=size)
        items = data.get("data", []) if isinstance(data, dict) else []
        total = _total_pages_from(data, page, size)
        _set_page(uid, "email", page)
        kb = telebot.types.InlineKeyboardMarkup(row_width=1)
        for item in items[:size]:
            if isinstance(item, dict):
                eid = item.get("id", "-")
                email = item.get("email") or item.get("domain", "-")
                kb.add(telebot.types.InlineKeyboardButton(
                    f"📬 {email} (ID {eid})", callback_data=f"email:detail:{eid}"))
        nav = pagination_keys(page, total, "email")
        if nav:
            kb.add(*nav)
        kb.add(telebot.types.InlineKeyboardButton("⬅️ Kembali", callback_data="menu:email"))
        _edit(chat, msg_id, email_list_msg(data), kb)
        _answer(call, f"Halaman {page}/{total}")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Muat Email", str(exc)), back_menu())
        _answer(call, str(exc), alert=True)


def _show_email_services_for_buy(chat: int, msg_id: int, uid: int, domain: str, call: CallbackQuery) -> None:
    try:
        data = api.legacy("getServicesList")
        items = data.get("data", data) if isinstance(data, dict) else data
        kb = telebot.types.InlineKeyboardMarkup(row_width=2)
        buttons = []
        for item in items[:25]:
            if isinstance(item, dict):
                name = item.get("name", "-")
                sid = item.get("id", item.get("code", "-"))
                buttons.append(telebot.types.InlineKeyboardButton(
                    f"📱 {name}", callback_data=f"email:service:{sid}"))
        kb.add(*buttons)
        kb.add(telebot.types.InlineKeyboardButton("⬅️ Domain", callback_data="email:domains"))
        _edit(chat, msg_id, f"🔹 *Layanan Email - {domain}*\n\nPilih layanan:", kb)
        _answer(call, "Pilih layanan")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Muat Layanan", str(exc)), back_menu())
        _answer(call, str(exc), alert=True)


def _do_email_purchase(chat: int, msg_id: int, uid: int, service: str, call: CallbackQuery) -> None:
    domain = get_state(uid, "email_domain")
    try:
        act = api.buy_email_activation(domain=domain, service=service)
        clear_state(uid)
        _edit(chat, msg_id, purchase_success(act), email_menu())
        _answer(call, "Aktivasi email dibeli")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Beli Email", str(exc)), back_menu())
        _answer(call, str(exc), alert=True)


def _show_email_detail(chat: int, msg_id: int, eid: str, call: CallbackQuery) -> None:
    try:
        data = api.email_detail(eid)
        _edit(chat, msg_id, email_detail_msg(data), email_menu())
        _answer(call, "Detail email")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Muat Detail", str(exc)), email_menu())
        _answer(call, str(exc), alert=True)


def _do_email_cancel(chat: int, msg_id: int, eid: str, call: CallbackQuery) -> None:
    try:
        api.cancel_email(eid)
        _edit(chat, msg_id, success_msg("Email Dibatalkan", f"Aktivasi email ID {eid} telah dibatalkan."), back_menu())
        _answer(call, "Dibatalkan")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Batalkan", str(exc)), email_menu())
        _answer(call, str(exc), alert=True)


def _do_email_reorder(chat: int, msg_id: int, eid: str, call: CallbackQuery) -> None:
    try:
        api.reorder_email(eid)
        _edit(chat, msg_id, success_msg("Email Dipesan Ulang", f"Aktivasi email ID {eid} telah dipesan ulang."), email_menu())
        _answer(call, "Dipesan ulang")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Pesan Ulang", str(exc)), email_menu())
        _answer(call, str(exc), alert=True)


# ── Aktivasi SMS ────────────────────────────────────────────────

def _show_active(chat: int, msg_id: int, call: CallbackQuery, page: int = 1) -> None:
    uid = call.from_user.id
    size = 15
    try:
        data = api.active_activations(page=page, size=size)
        items = data.get("data", []) if isinstance(data, dict) else []
        total = _total_pages_from(data, page, size)
        _set_page(uid, "active", page)
        kb = telebot.types.InlineKeyboardMarkup(row_width=1)
        for item in items[:size]:
            if isinstance(item, dict):
                aid = item.get("id", "-")
                phone = item.get("phone", "-")
                kb.add(telebot.types.InlineKeyboardButton(
                    f"📱 {phone} (ID {aid})", callback_data=f"act:view:{aid}"))
        nav = pagination_keys(page, total, "active")
        if nav:
            kb.add(*nav)
        kb.add(telebot.types.InlineKeyboardButton("⬅️ Kembali", callback_data="menu:main"))
        _edit(chat, msg_id, active_list_msg(data), kb)
        _answer(call, f"Halaman {page}/{total}")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Muat Aktif", str(exc)), back_menu())
        _answer(call, str(exc), alert=True)


def _show_history(chat: int, msg_id: int, call: CallbackQuery, page: int = 1) -> None:
    uid = call.from_user.id
    size = 15
    try:
        data = api.activation_history(page=page, size=size)
        items = data.get("data", []) if isinstance(data, dict) else []
        total = _total_pages_from(data, page, size)
        _set_page(uid, "history", page)
        kb = telebot.types.InlineKeyboardMarkup(row_width=1)
        for item in items[:size]:
            if isinstance(item, dict):
                aid = item.get("id", "-")
                phone = item.get("phone", "-")
                status = item.get("status", "-")
                kb.add(telebot.types.InlineKeyboardButton(
                    f"📜 {phone} (ID {aid}, {status})", callback_data=f"act:view:{aid}"))
        nav = pagination_keys(page, total, "history")
        if nav:
            kb.add(*nav)
        kb.add(telebot.types.InlineKeyboardButton("⬅️ Kembali", callback_data="menu:main"))
        _edit(chat, msg_id, history_msg(data), kb)
        _answer(call, f"Halaman {page}/{total}")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Muat Riwayat", str(exc)), back_menu())
        _answer(call, str(exc), alert=True)


def _show_transactions(chat: int, msg_id: int, call: CallbackQuery) -> None:
    uid = call.from_user.id
    purchases = get_state(uid, "purchases", []) or []
    if not purchases:
        txt = "💰 *Riwayat Transaksi*\n\nBelum ada pembelian."
        _edit(chat, msg_id, txt, back_menu())
        _answer(call, "Belum ada transaksi")
        return

    total = 0.0
    lines = ["💰 *Riwayat Transaksi*\n"]
    for p in reversed(purchases[-20:]):
        try:
            total += float(str(p.get("price", "0")).replace(",", "."))
        except (ValueError, TypeError):
            pass
        lines.append(
            f"• {p.get('time', '-')} | {p.get('service', '-')}"
            f" | {p.get('country', '-')} | {p.get('price', '-')} {p.get('currency', '')}"
        )
    lines.append(f"\n*Total:* {total:g}")
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("⬅️ Kembali", callback_data="menu:main"))
    _edit(chat, msg_id, "\n".join(lines), kb)
    _answer(call, "Riwayat transaksi")
    try:
        # coba ambil dari daftar aktif dulu
        data = api.active_activations()
        items = data.get("data", []) if isinstance(data, dict) else []
        act = next((x for x in items if isinstance(x, dict) and str(x.get("id")) == aid), None)
        if act is None:
            hist = api.activation_history()
            hitems = hist.get("data", []) if isinstance(hist, dict) else []
            act = next((x for x in hitems if isinstance(x, dict) and str(x.get("id")) == aid), None)
        if act is None:
            _edit(chat, msg_id, error_msg("Tidak Ditemukan", f"Aktivasi ID {aid} tidak ditemukan."), back_menu())
            _answer(call, "Tidak ditemukan", alert=True)
            return
        _edit(chat, msg_id, activation_detail(act), activation_actions(aid, watching=_is_watching(call.from_user.id, aid)))
        _answer(call, "Detail aktivasi")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Muat Detail", str(exc)), back_menu())
        _answer(call, str(exc), alert=True)


def _show_otp_last(chat: int, msg_id: int, aid: str, call: CallbackQuery) -> None:
    try:
        data = api.otp_last(aid)
        _edit(chat, msg_id, otp_msg(aid, data), activation_actions(aid, watching=_is_watching(call.from_user.id, aid)))
        _answer(call, "OTP dimuat")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Ambil OTP", str(exc)), activation_actions(aid, watching=_is_watching(call.from_user.id, aid)))
        _answer(call, str(exc), alert=True)


def _show_otp_list(chat: int, msg_id: int, aid: str, call: CallbackQuery, page: int = 1) -> None:
    uid = call.from_user.id
    size = 15
    try:
        data = api.otp_list(aid, page=page, size=size)
        items = data.get("data", []) if isinstance(data, dict) else []
        total = _total_pages_from(data, page, size)
        _set_page(uid, "otp", page, aid=aid)
        txt = otp_msg(aid, data)
        kb = activation_actions(aid, watching=_is_watching(uid, aid))
        # Sisipkan tombol pagination sebelum tombol kembali
        nav = pagination_keys(page, total, f"otp:{aid}")
        if nav:
            # activation_actions has row_width; add nav row
            for btn in nav:
                kb.add(btn)
        _edit(chat, msg_id, txt, kb)
        _answer(call, f"Halaman {page}/{total}")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Ambil Daftar OTP", str(exc)), activation_actions(aid, watching=_is_watching(uid, aid)))
        _answer(call, str(exc), alert=True)


# ── Run ─────────────────────────────────────────────────────────

def _start_otp_poller(bot, interval: int = 30):
    """Background thread: cek aktivasi yang di-watch, kirim pesan saat OTP baru."""
    import threading
    import time

    def loop():
        while True:
            try:
                # Ambil semua user yang punya otp_watch
                for uid in list(user_state.keys()):
                    watch = _get_watch(uid)
                    for aid in list(watch.keys()):
                        try:
                            data = api.otp_list(aid, page=1, size=5)
                            items = data.get("data", []) if isinstance(data, dict) else []
                            if not items:
                                continue
                            latest = items[0]
                            latest_text = str(latest.get("code", latest.get("text", "")))
                            last_seen = watch.get(aid)
                            if latest_text and latest_text != last_seen:
                                watch[aid] = latest_text
                                set_state(uid, "otp_watch", watch)
                                bot.send_message(
                                    uid,
                                    f"🔔 *OTP Baru untuk Aktivasi {aid}*\n\nKode: *{latest_text}*",
                                    parse_mode="MarkdownV2",
                                )
                        except HeroSMSError:
                            continue
                        except Exception:  # noqa: BLE001
                            continue
            except Exception:  # noqa: BLE001
                pass
            time.sleep(interval)

    t = threading.Thread(target=loop, daemon=True)
    t.start()


if __name__ == "__main__":
    _start_otp_poller(bot)
    log.info("Bot HeroSMS dimulai…")
    bot.infinity_polling(skip_pending=True)
