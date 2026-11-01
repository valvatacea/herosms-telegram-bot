"""Bot Telegram untuk HeroSMS — coverage seluruh OpenAPI spec (api-en.json).
Versi lebih ramah pengguna: konfirmasi sebelum aksi destructive,
pesan error ramah, dan navigasi yang konsisten."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
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
    settings_menu,
    settings_lang_menu,
    buy_search_results_keyboard,
)
from bot.messages import (
    esc,
    code,
    status_name,
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
    watch = _get_watch(uid) or {}
    return aid in watch and watch.get(aid) != "off"


def _watch_toggle(uid: int, aid: str) -> bool:
    """Toggle watch. Return True jika sekarang sedang di-watch."""
    watch = _get_watch(uid)
    val = watch.get(aid)
    if val == "off":
        # Sedang mati, nyalakan kembali
        del watch[aid]
        set_state(uid, "otp_watch", watch)
        return True
    if aid in watch:
        # Sedang nyala (None atau kode OTP), matikan
        watch[aid] = "off"
        set_state(uid, "otp_watch", watch)
        return False
    # Belum ada, nyalakan default
    watch[aid] = None
    set_state(uid, "otp_watch", watch)
    return True


logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("herosms-bot")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="MarkdownV2")
api = HeroSMS(HEROSMS_API_KEY, HEROSMS_BASE_URL)


def _answer(call: CallbackQuery, text: str, alert: bool = False) -> None:
    bot.answer_callback_query(call.id, text, show_alert=alert)


def _alert(prefix: str, exc: Exception) -> str:
    """Teks alert callback query yang belum melebihi batas Telegram (~200 char)."""
    msg = str(exc)
    budget = 200 - len(prefix) - 3  # 3 = ": ..."
    if len(msg) > budget:
        msg = msg[:budget].rsplit(" ", 1)[0] + "..."
    return f"{prefix}: {msg}"


def _edit(chat: int, msg_id: int, text: str, markup=None) -> None:
    try:
        bot.edit_message_text(text, chat, msg_id, reply_markup=markup)
    except Exception:
        bot.send_message(chat, text, reply_markup=markup)


def _legacy_items(data):
    """Normalisasi respons legacy ke list: {'services': [...]} atau {id: {...}} → list."""
    if isinstance(data, dict):
        if isinstance(data.get("services"), list):
            return data["services"]
        if isinstance(data.get("data"), (list, dict)):
            data = data["data"]
    if isinstance(data, dict):
        return [v for v in data.values() if isinstance(v, dict)]
    return data if isinstance(data, list) else []


# ── Kurs USD→IDR (cache 24 jam) & format harga ─────────────────────

_FX = {"rate": None, "ts": 0.0}


def _idr_rate() -> float | None:
    if _FX["rate"] is None or time.time() - _FX["ts"] > 86400:
        try:
            r = api.session.get("https://open.er-api.com/v6/latest/USD", timeout=10)
            _FX["rate"] = float(r.json()["rates"]["IDR"])
            _FX["ts"] = time.time()
        except Exception:
            return _FX["rate"]
    return _FX["rate"]


def _fmt_price(usd, uid) -> str:
    """Harga sesuai setting mata uang: $USD, atau Rp saja (kurs)."""
    usd = str(usd)
    if usd in ("-", ""):
        return code(usd)
    if (get_state(uid, "settings_currency") or "usd") != "idr":
        return code("$" + usd)
    rate = _idr_rate()
    if not rate:
        return code("$" + usd)
    try:
        rp = f"{int(float(usd) * rate):,}".replace(",", ".")
    except (TypeError, ValueError):
        return code("$" + usd)
    return code(f"Rp{rp}")


def _price_disp(usd, uid) -> str:
    """Biaya dengan emot & simbol sesuai mata uang: 💵 $x / 🇮🇩 Rpx."""
    usd = str(usd)
    if usd in ("-", ""):
        return code("-")
    if (get_state(uid, "settings_currency") or "usd") == "idr":
        return f"🇮🇩 {_fmt_price(usd, uid)}"
    return f"💵 {code('$' + usd)}"


def _idr_label(usd, uid) -> str:
    """Label tombol harga: '🇮🇩 Rp...' saat mode IDR, '💵 $USD' saat USD."""
    usd = str(usd)
    if (get_state(uid, "settings_currency") or "usd") != "idr":
        return f"💵 ${usd}"
    rate = _idr_rate()
    if not rate:
        return f"💵 ${usd}"
    try:
        rp = f"{int(float(usd) * rate):,}".replace(",", ".")
    except (TypeError, ValueError):
        return f"💵 ${usd}"
    return f"🇮🇩 Rp{rp}"


# ── Nama layanan/negara dari kode API (cache sekali) ──────────────

_NAME_CACHE = {"countries": None, "services": None}


def _country_name(cid) -> str:
    if _NAME_CACHE["countries"] is None:
        try:
            data = api.legacy("getCountries")
            vals = data.values() if isinstance(data, dict) else []
            _NAME_CACHE["countries"] = {
                str(v.get("id")): v.get("eng") for v in vals if isinstance(v, dict)
            }
        except Exception:
            _NAME_CACHE["countries"] = {}
    return (_NAME_CACHE["countries"] or {}).get(str(cid), str(cid))


def _service_name(code) -> str:
    if _NAME_CACHE["services"] is None:
        try:
            data = api.legacy("getServicesList")
            _NAME_CACHE["services"] = {
                str(i.get("code")): i.get("name")
                for i in _legacy_items(data)
                if isinstance(i, dict)
            }
        except Exception:
            _NAME_CACHE["services"] = {}
    return (_NAME_CACHE["services"] or {}).get(str(code), str(code))


# ── Command ─────────────────────────────────────────────────────

@bot.message_handler(commands=["start"])
def cmd_start(message: Message) -> None:
    log.debug(f"command /start uid={message.chat.id}")
    bot.reply_to(message, welcome_msg(), reply_markup=main_menu())


@bot.message_handler(commands=["menu"])
def cmd_menu(message: Message) -> None:
    log.debug(f"command /menu uid={message.chat.id}")
    bot.send_message(message.chat.id, "Menu utama", reply_markup=main_menu())


@bot.message_handler(commands=["help"])
def cmd_help(message: Message) -> None:
    log.debug(f"command /help uid={message.chat.id}")
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
        "• 🛒 Beli nomor verifikasi \\(SMS/email\\)\n"
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
    log.debug(f"callback uid={uid} chat={chat} data={data}")

    try:
        if data == "menu:main":
            _edit(chat, msg_id, welcome_msg(), main_menu())
            _answer(call, "Menu utama")

        elif data == "menu:close":
            bot.edit_message_text("Menu ditutup\\. Ketik /start untuk buka kembali\\.", chat, msg_id)
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

        elif data == "settings:main":
            _show_settings(chat, msg_id, uid, call)

        elif data == "settings:lang":
            lang = get_state(uid, "settings_lang") or "id"
            _edit(chat, msg_id, "🔹 *Pilih Bahasa*", settings_lang_menu(lang))
            _answer(call, "Pilih bahasa")

        elif data == "settings:lang:id":
            set_state(uid, "settings_lang", "id")
            _show_settings(chat, msg_id, uid, call)
            _answer(call, "Bahasa: Indonesia")

        elif data == "settings:lang:soon":
            _answer(call, "English segera tersedia", alert=True)

        elif data.startswith("settings:cur:"):
            set_state(uid, "settings_currency", data.split(":")[2])
            _show_settings(chat, msg_id, uid, call)
            _answer(call, "Mata uang disimpan")

        elif data == "settings:autocancel":
            cur = str(get_state(uid, "settings_autocancel") or "off")
            order = ["off", "5", "10", "15"]
            nxt = order[(order.index(cur) + 1) % len(order)] if cur in order else "5"
            set_state(uid, "settings_autocancel", nxt)
            _show_settings(chat, msg_id, uid, call)
            _answer(call, "Nonaktif" if nxt == "off" else f"Auto-batal: {nxt} menit")

        elif data.startswith("buy:countries:"):
            _show_countries_page(chat, msg_id, uid, int(data.split(":")[2]), call)

        elif data.startswith("buy:services:"):
            _show_services_page(chat, msg_id, uid, int(data.split(":")[2]), call)

        elif data == "buy:search:country":
            set_state(uid, "_buy_search", "country")
            bot.send_message(chat, "🔍 Ketik nama negara yang dicari:")
            bot.register_next_step_handler(call.message, _handle_buy_search)
            _answer(call, "Mode pencarian negara")

        elif data == "buy:search:service":
            set_state(uid, "_buy_search", "service")
            bot.send_message(chat, "🔍 Ketik nama layanan yang dicari:")
            bot.register_next_step_handler(call.message, _handle_buy_search)
            _answer(call, "Mode pencarian layanan")

        elif data.startswith("buy:country:"):
            parts = data.split(":", 3)
            country = parts[2]
            set_state(uid, "buy_country", country)
            if len(parts) > 3 and parts[3]:
                set_state(uid, "buy_country_name", parts[3])
            _show_services_for_buy(chat, msg_id, uid, country, call)

        elif data.startswith("buy:service:"):
            parts = data.split(":", 3)
            service = parts[2]
            if len(parts) > 3 and parts[3]:
                set_state(uid, "buy_service_name", parts[3])
            _show_buy_prices(chat, msg_id, uid, service, call)

        elif data.startswith("buy:price:"):
            price = data.split(":", 2)[2]
            _show_buy_confirm(chat, msg_id, uid, price, call)

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

        elif data.startswith("act:resend:"):
            aid = data.split(":", 2)[2]
            _show_confirm_resend(chat, msg_id, aid, call)

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

        elif data.startswith("confirm:resend:"):
            aid = data.split(":", 2)[2]
            _do_resend(chat, msg_id, aid, call)

        elif data.startswith("act:reactivate:"):
            aid = data.split(":", 2)[2]
            _do_reactivate(chat, msg_id, aid, call)

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
        _answer(call, _alert("Error", exc), alert=True)
    except Exception as exc:  # noqa: BLE001
        log.exception("callback error")
        _edit(chat, msg_id, error_msg("Error Tak Terduga", str(exc)), back_menu())
        _answer(call, _alert("Error tak terduga", exc), alert=True)


# ── Helper tampilan ─────────────────────────────────────────────

def _show_balance(chat: int, msg_id: int, call: CallbackQuery) -> None:
    try:
        uid = call.from_user.id
        data = api.get_balance()
        bal = str(data.get("balance", "-"))
        _edit(chat, msg_id, balance_msg(data, _price_disp(bal, uid)), back_menu())
        _answer(call, "Saldo dimuat")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Cek Saldo", str(exc)), back_menu())
        _answer(call, _alert("Error", exc), alert=True)


def _show_settings(chat: int, msg_id: int, uid: int, call: CallbackQuery) -> None:
    lang = get_state(uid, "settings_lang") or "id"
    cur = get_state(uid, "settings_currency") or "usd"
    ac = str(get_state(uid, "settings_autocancel") or "off")
    lang_name = "Indonesia" if lang == "id" else "English"
    ac_name = "Nonaktif" if ac == "off" else f"{ac} menit"
    text = (
        "🔹 *Pengaturan*\n\n"
        f"Bahasa: {esc(lang_name)}\n"
        f"Mata uang tampilan: {code(cur.upper())}\n"
        f"Auto\\-batal tanpa OTP: {esc(ac_name)}\n"
        "Harga HeroSMS selalu USD, mode IDR menampilkan konversi kurs"
    )
    _edit(chat, msg_id, text, settings_menu(lang, cur, ac))
    _answer(call, "Pengaturan")


def _show_stats(chat: int, msg_id: int, call: CallbackQuery) -> None:
    try:
        data = api.user_stats()
        # Kunci respons = kode (6/go) -> ubah ke nama (Indonesia/Telegram)
        if isinstance(data, dict) and isinstance(data.get("data"), dict):
            data = {"data": {
                _country_name(c): {
                    _service_name(s): v for s, v in sv.items()
                }
                for c, sv in data["data"].items()
                if isinstance(sv, dict)
            }}
        _edit(chat, msg_id, stats_msg(data), back_menu())
        _answer(call, "Statistik dimuat")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Cek Statistik", str(exc)), back_menu())
        _answer(call, _alert("Error", exc), alert=True)


def _show_countries(chat: int, msg_id: int, call: CallbackQuery) -> None:
    try:
        data = api.legacy("getCountries")
        _edit(chat, msg_id, countries_msg(data), back_menu())
        _answer(call, "Negara dimuat")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Muat Negara", str(exc)), back_menu())
        _answer(call, _alert("Error", exc), alert=True)


def _show_services(chat: int, msg_id: int, call: CallbackQuery) -> None:
    try:
        data = api.legacy("getServicesList")
        _edit(chat, msg_id, services_msg(data), back_menu())
        _answer(call, "Layanan dimuat")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Muat Layanan", str(exc)), back_menu())
        _answer(call, _alert("Error", exc), alert=True)


def _show_prices(chat: int, msg_id: int, call: CallbackQuery) -> None:
    try:
        data = api.legacy("getPrices")
        _edit(chat, msg_id, prices_msg(data), back_menu())
        _answer(call, "Harga dimuat")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Muat Harga", str(exc)), back_menu())
        _answer(call, _alert("Error", exc), alert=True)


def _start_buy_flow(chat: int, msg_id: int, uid: int, call: CallbackQuery) -> None:
    _show_countries_page(chat, msg_id, uid, 1, call)


def _show_countries_page(chat: int, msg_id: int, uid: int, page: int, call: CallbackQuery) -> None:
    try:
        data = api.legacy("getCountries")
        items = _legacy_items(data)
        total = max(1, (len(items) + 14) // 15)
        page = min(max(1, page), total)
        _edit(chat, msg_id, "🔹 *Beli Nomor*\n\nPilih negara:", buy_countries_keyboard(items, page))
        _answer(call, f"Halaman {page}/{total}")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Muat Negara", str(exc)), back_menu())
        _answer(call, _alert("Error", exc), alert=True)


def _show_services_for_buy(chat: int, msg_id: int, uid: int, country: str, call: CallbackQuery) -> None:
    _show_services_page(chat, msg_id, uid, 1, call)


def _show_services_page(chat: int, msg_id: int, uid: int, page: int, call: CallbackQuery) -> None:
    country = get_state(uid, "buy_country") or "-"
    try:
        data = api.legacy("getServicesList")
        items = _legacy_items(data)
        total = max(1, (len(items) + 14) // 15)
        page = min(max(1, page), total)
        cname = esc(get_state(uid, "buy_country_name") or country)
        _edit(
            chat,
            msg_id,
            "🔹 *Layanan \\- {country}*".format(country=cname) + "\n\nPilih layanan:",
            buy_services_keyboard(items, page),
        )
        _answer(call, f"Halaman {page}/{total}")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Muat Layanan", str(exc)), back_menu())
        _answer(call, _alert("Error", exc), alert=True)


def _handle_buy_search(message: Message) -> None:
    """Handler hasil ketikan pencarian negara/layanan."""
    uid = message.from_user.id
    if not message.text or message.text.startswith("/"):
        return
    q = message.text.strip().lower()
    if not q:
        return
    kind = get_state(uid, "_buy_search") or "country"
    set_state(uid, "_buy_search", None)
    if kind == "country":
        data = api.legacy("getCountries")
        items = [
            i for i in _legacy_items(data)
            if isinstance(i, dict) and q in str(i.get("eng", i.get("name", ""))).lower()
        ]
        if not items:
            bot.send_message(message.chat.id, f"🔍 Tidak ada negara yang cocok untuk {code(q)}, coba kata lain")
            return
        bot.send_message(message.chat.id, f"🔍 {code(str(len(items)))} negara cocok untuk {code(q)}:", reply_markup=buy_search_results_keyboard("country", items))
    else:
        data = api.legacy("getServicesList")
        items = [
            i for i in _legacy_items(data)
            if isinstance(i, dict) and q in str(i.get("name", "")).lower()
        ]
        if not items:
            bot.send_message(message.chat.id, f"🔍 Tidak ada layanan yang cocok untuk {code(q)}, coba kata lain")
            return
        bot.send_message(message.chat.id, f"🔍 {code(str(len(items)))} layanan cocok untuk {code(q)}:", reply_markup=buy_search_results_keyboard("service", items))

def _show_buy_prices(chat: int, msg_id: int, uid: int, service: str, call: CallbackQuery) -> None:
    """Skema beli baru: negara → layanan → daftar harga → konfirmasi."""
    country = get_state(uid, "buy_country") or "-"
    set_state(uid, "buy_service", service)
    try:
        data = api.offers("sms", services=service, countries=str(country))
        node = (
            data.get("data", {}).get(service, {}).get(str(country), {})
            if isinstance(data, dict) else {}
        )
        entries = sorted(node.get("map", {}).items(), key=lambda kv: float(kv[0]))[:10]
        if not entries:
            _edit(chat, msg_id, error_msg("Stok Kosong", f"Tidak ada nomor untuk layanan {service} negara {country}"), back_menu())
            _answer(call, "Stok kosong", alert=True)
            return
        lines = [f"🔹 *Pilih Harga*", ""]
        p_sname = esc(get_state(uid, "buy_service_name") or service)
        p_cname = esc(get_state(uid, "buy_country_name") or country)
        lines.append(f"Layanan: {p_sname} \\| Negara: {p_cname}")
        lines.append("")
        for price, count in entries:
            lines.append(f"• {_price_disp(price, uid)} — stok {code(count)}")
        kb = telebot.types.InlineKeyboardMarkup(row_width=2)
        kb.add(*[telebot.types.InlineKeyboardButton(_idr_label(price, uid), callback_data=f"buy:price:{price}") for price, _ in entries])
        kb.add(telebot.types.InlineKeyboardButton("⬅️ Batal", callback_data="menu:buy_activation"))
        _edit(chat, msg_id, "\n".join(lines), kb)
        _answer(call, "Pilih harga")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Muat Harga", str(exc)), back_menu())
        _answer(call, _alert("Error", exc), alert=True)


def _show_buy_confirm(chat: int, msg_id: int, uid: int, price: str, call: CallbackQuery) -> None:
    country = get_state(uid, "buy_country") or "-"
    service = get_state(uid, "buy_service") or "-"
    cname = get_state(uid, "buy_country_name") or country
    sname = get_state(uid, "buy_service_name") or service
    set_state(uid, "buy_price", price)
    # Durasi default aktivasi OTP = 20 menit (custom-durations hanya untuk rent/produk kustom)
    duration = "20 menit (default aktivasi)"
    set_state(uid, "buy_duration", duration)
    _edit(
        chat,
        msg_id,
        buy_confirm_msg(cname, sname, price, "", duration, _price_disp(price, uid)),
        buy_confirm_keyboard(country, service),
    )
    _answer(call, "Konfirmasi pembelian")


def _do_purchase(chat: int, msg_id: int, uid: int, service: str, country: str | None = None, call: CallbackQuery | None = None) -> None:
    if country is None:
        country = get_state(uid, "buy_country")
    try:
        sprice = get_state(uid, "buy_price")
        mp = float(sprice) if sprice else None
        act = api.buy_activation(
            service=service,
            country=country,
            max_price=mp,
            fixed_price=mp is not None,
            verification_type="sms",
        )
        # Respons POST dibungkus {"data": [ ... ]} — ambil isinya
        if isinstance(act, dict):
            inner = act.get("data")
            if isinstance(inner, list) and inner:
                act = inner[0]
            elif isinstance(inner, dict) and inner:
                act = inner
        if isinstance(act, dict):
            act["serviceName"] = _service_name(act.get("service") or service)
            act["countryName"] = _country_name(act.get("country") or country)
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
            "ts": time.time(),
        }
        pops = get_state(uid, "purchases", []) or []
        pops.append(pur)
        watch = _get_watch(uid) or {}
        set_state(uid, "purchases", pops)
        clear_state(uid)
        set_state(uid, "purchases", pops)
        set_state(uid, "otp_watch", watch)
        if call:
            _edit(chat, msg_id, purchase_success(act, _price_disp(act.get("price", get_state(uid, "buy_price", "-")), uid)), activation_actions(str(act.get("id", "")), watching=False))
            _answer(call, "Nomor dibeli")
        else:
            bot.send_message(chat, purchase_success(act, _price_disp(act.get("price", get_state(uid, "buy_price", "-")), uid)), reply_markup=activation_actions(str(act.get("id", "")), watching=False))
    except HeroSMSError as exc:
        if call:
            _edit(chat, msg_id, error_msg("Gagal Beli Nomor", str(exc)), back_menu())
            _answer(call, _alert("Error", exc), alert=True)
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
        _answer(call, _alert("Error", exc), alert=True)


def _do_cancel(chat: int, msg_id: int, aid: str, call: CallbackQuery) -> None:
    try:
        api.cancel_activation(aid)
        _edit(chat, msg_id, success_msg("Aktivasi Dibatalkan", f"Aktivasi ID {aid} telah dibatalkan."), back_menu())
        _answer(call, "Dibatalkan")
    except HeroSMSError as exc:
        if "EARLY_CANCEL_DENIED" in str(exc) or "first 2 minutes" in str(exc):
            _answer(call, "Tunggu 2 menit setelah beli sebelum batalkan. Coba lagi setelah itu.", alert=True)
            return
        _edit(chat, msg_id, error_msg("Gagal Batalkan", str(exc)), activation_actions(aid, watching=_is_watching(call.from_user.id, aid)))
        _answer(call, _alert("Error", exc), alert=True)


# ── Konfirmasi & eksekusi resend SMS ──────────────────────────────

def _show_confirm_resend(chat: int, msg_id: int, aid: str, call: CallbackQuery) -> None:
    _edit(
        chat,
        msg_id,
        confirm_msg("Kirim Ulang SMS", f"Aktivasi ID {aid} akan meminta pengiriman ulang SMS.\nBiaya mungkin dikenakan sesuai ketentuan layanan."),
        confirm_keyboard("resend", aid),
    )
    _answer(call, "Konfirmasi kirim ulang SMS")


def _do_resend(chat: int, msg_id: int, aid: str, call: CallbackQuery) -> None:
    try:
        api.resend_sms(aid)
        _edit(chat, msg_id, success_msg("SMS Dikirim Ulang", f"Aktivasi ID {aid}: permintaan resend SMS telah dikirim."), activation_actions(aid, watching=_is_watching(call.from_user.id, aid)))
        _answer(call, "SMS dikirim ulang")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Kirim Ulang", str(exc)), activation_actions(aid, watching=_is_watching(call.from_user.id, aid)))
        _answer(call, _alert("Error", exc), alert=True)


def _do_reactivate(chat: int, msg_id: int, aid: str, call: CallbackQuery) -> None:
    w = _is_watching(call.from_user.id, aid)
    try:
        api.reactivate_activation(aid)
        _edit(chat, msg_id, success_msg("Aktivasi Di-reaktivasi", f"Aktivasi ID {aid} telah di-reaktivasi."), activation_actions(aid, watching=w))
        _answer(call, "Di-reaktivasi")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Reaktivasi", str(exc)), activation_actions(aid, watching=w))
        _answer(call, _alert("Error", exc), alert=True)


def _show_activation_detail(chat: int, msg_id: int, aid: str, call: CallbackQuery) -> None:
    try:
        act: Dict = {}
        try:
            # search=ID tidak match di API — ambil daftar lalu cocokkan manual
            data = api.active_activations(size=25)
            items = data.get("data", []) if isinstance(data, dict) else []
            if isinstance(items, list):
                act = next((x for x in items if str(x.get("id", "")) == str(aid)), {})
        except HeroSMSError:
            pass
        if not act:
            try:
                now = datetime.now(timezone.utc)
                data = api.activation_history(
                    from_=(now - timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    to=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    size=25,
                )
                items = data.get("data", []) if isinstance(data, dict) else []
                if isinstance(items, list) and items:
                    act = next((x for x in items if str(x.get("id", "")) == str(aid)), {})
            except HeroSMSError:
                pass
        if not act:
            act = {"id": aid, "status": "-", "phone": "-"}
        if isinstance(act, dict):
            act["serviceName"] = _service_name(act.get("service"))
            act["countryName"] = _country_name(act.get("country"))
        watch = _is_watching(call.from_user.id, str(aid))
        _edit(chat, msg_id, activation_detail(act, _price_disp(act.get("price", act.get("cost", "-")), call.from_user.id)), activation_actions(str(aid), watching=watch))
        _answer(call, "Detail aktivasi")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Muat Detail", str(exc)), back_menu())
        _answer(call, _alert("Error", exc), alert=True)


# ── Email ───────────────────────────────────────────────────────

def _show_email_menu(chat: int, msg_id: int, call: CallbackQuery) -> None:
    _edit(chat, msg_id, "🔹 *Aktivasi Email*\n\nManajemen aktivasi via email:", email_menu())
    _answer(call, "Menu email")


def _show_email_domains(chat: int, msg_id: int, call: CallbackQuery) -> None:
    uid = call.from_user.id
    site = get_state(uid, "email_site")
    if not site:
        set_state(uid, "_email_pending", "domains")
        set_state(uid, "_email_chat", chat)
        set_state(uid, "_email_msg_id", msg_id)
        bot.send_message(chat, "Masukkan site \\(contoh: telegram\\.com\\):")
        bot.register_next_step_handler(call.message, _handle_email_site_input)
        _answer(call, "Masukkan site dulu")
        return
    _email_domains_render(chat, msg_id, uid, site)

def _email_domains_render(chat: int, msg_id: int, uid: int, site: str) -> None:
    try:
        data = api.email_domains(site=site)
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
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Muat Domain", str(exc)), back_menu())


def _show_email_offers(chat: int, msg_id: int, call: CallbackQuery) -> None:
    uid = call.from_user.id
    site = get_state(uid, "email_site")
    if not site:
        set_state(uid, "_email_pending", "offers")
        set_state(uid, "_email_chat", chat)
        set_state(uid, "_email_msg_id", msg_id)
        bot.send_message(chat, "Masukkan site \\(contoh: telegram\\.com\\):")
        bot.register_next_step_handler(call.message, _handle_email_site_input)
        _answer(call, "Masukkan site dulu")
        return
    _email_offers_render(chat, msg_id, uid, site)

def _email_offers_render(chat: int, msg_id: int, uid: int, site: str) -> None:
    try:
        data = api.email_offers(site=site)
        _edit(chat, msg_id, prices_msg(data), back_menu())
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Muat Offers", str(exc)), back_menu())

def _handle_email_site_input(message: Message) -> None:
    uid = message.from_user.id
    if message.text.startswith("/"):
        return
    site = message.text.strip()
    if not site:
        return
    set_state(uid, "email_site", site)
    pending = get_state(uid, "_email_pending") or "domains"
    chat = get_state(uid, "_email_chat") or message.chat.id
    msg_id = get_state(uid, "_email_msg_id") or message.message_id
    set_state(uid, "_email_pending", None)
    set_state(uid, "_email_chat", None)
    set_state(uid, "_email_msg_id", None)
    if pending == "domains":
        _email_domains_render(chat, msg_id, uid, site)
    else:
        _email_offers_render(chat, msg_id, uid, site)


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
        _answer(call, _alert("Error", exc), alert=True)


def _show_email_services_for_buy(chat: int, msg_id: int, uid: int, domain: str, call: CallbackQuery) -> None:
    try:
        data = api.legacy("getServicesList")
        items = _legacy_items(data)
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
        _answer(call, _alert("Error", exc), alert=True)


def _do_email_purchase(chat: int, msg_id: int, uid: int, service: str, call: CallbackQuery) -> None:
    domain = get_state(uid, "email_domain")
    try:
        act = api.buy_email_activation(domain=domain, service=service)
        clear_state(uid)
        _edit(chat, msg_id, purchase_success(act), email_menu())
        _answer(call, "Aktivasi email dibeli")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Beli Email", str(exc)), back_menu())
        _answer(call, _alert("Error", exc), alert=True)


def _show_email_detail(chat: int, msg_id: int, eid: str, call: CallbackQuery) -> None:
    try:
        data = api.email_detail(eid)
        _edit(chat, msg_id, email_detail_msg(data), email_menu())
        _answer(call, "Detail email")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Muat Detail", str(exc)), email_menu())
        _answer(call, _alert("Error", exc), alert=True)


def _do_email_cancel(chat: int, msg_id: int, eid: str, call: CallbackQuery) -> None:
    try:
        api.cancel_email(eid)
        _edit(chat, msg_id, success_msg("Email Dibatalkan", f"Aktivasi email ID {eid} telah dibatalkan."), back_menu())
        _answer(call, "Dibatalkan")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Batalkan", str(exc)), email_menu())
        _answer(call, _alert("Error", exc), alert=True)


def _do_email_reorder(chat: int, msg_id: int, eid: str, call: CallbackQuery) -> None:
    try:
        api.reorder_email(eid)
        _edit(chat, msg_id, success_msg("Email Dipesan Ulang", f"Aktivasi email ID {eid} telah dipesan ulang."), email_menu())
        _answer(call, "Dipesan ulang")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Pesan Ulang", str(exc)), email_menu())
        _answer(call, _alert("Error", exc), alert=True)


# ── Aktivasi SMS ────────────────────────────────────────────────

def _show_active(chat: int, msg_id: int, call: CallbackQuery, page: int = 1) -> None:
    uid = call.from_user.id
    size = 15
    try:
        data = api.active_activations(page=page, size=size)
        items = data.get("data", []) if isinstance(data, dict) else []
        for it in items:
            if isinstance(it, dict):
                it["costDisp"] = _price_disp(it.get("price", it.get("cost", "-")), uid)
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
        _answer(call, _alert("Error", exc), alert=True)


def _show_history(chat: int, msg_id: int, call: CallbackQuery, page: int = 1) -> None:
    uid = call.from_user.id
    size = 15
    now = datetime.now(timezone.utc)
    from_ = (now - timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%SZ")
    to = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        data = api.activation_history(from_=from_, to=to, page=page, size=size)
        items = data.get("data", []) if isinstance(data, dict) else []
        total = _total_pages_from(data, page, size)
        _set_page(uid, "history", page)
        kb = telebot.types.InlineKeyboardMarkup(row_width=1)
        for item in items[:size]:
            if isinstance(item, dict):
                aid = item.get("id", "-")
                phone = item.get("phone", "-")
                status = status_name(item.get("status", "-"))
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
        _answer(call, _alert("Error", exc), alert=True)


def _show_otp_last(chat: int, msg_id: int, aid: str, call: CallbackQuery) -> None:
    try:
        data = api.otp_last(aid)
        _edit(chat, msg_id, otp_msg(aid, data), activation_actions(aid, watching=_is_watching(call.from_user.id, aid)))
        _answer(call, "OTP dimuat")
    except HeroSMSError as exc:
        if "STATUS_WAIT_CODE" in str(exc):
            _edit(chat, msg_id, "🔹 *OTP Belum Masuk*\n\nMasih menunggu SMS pertama\\. Nyalakan Notif OTP biar otomatis kabari saat masuk\\.", activation_actions(aid, watching=_is_watching(call.from_user.id, aid)))
            _answer(call, "OTP belum masuk")
            return
        _edit(chat, msg_id, error_msg("Gagal Ambil OTP", str(exc)), activation_actions(aid, watching=_is_watching(call.from_user.id, aid)))
        _answer(call, _alert("Error", exc), alert=True)


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
        _answer(call, _alert("Error", exc), alert=True)


# ── Run ─────────────────────────────────────────────────────────

def _start_otp_poller(bot, interval: int = 30):
    """Background thread: cek semua aktivasi pembelian user, kirim pesan saat OTP baru (opt-out)."""
    import threading
    import time

    def loop():
        while True:
            try:
                for uid in list(user_state.keys()):
                    # Semua activation dari pembelian user (bukan hanya otp_watch)
                    purchases = get_state(uid, "purchases", []) or []
                    watch = _get_watch(uid) or {}
                    changed = False

                    # Daftarkan setiap purchase activation ke watch (default ON / opt-out)
                    # Skip yang secara eksplisit dimatikan pemain ("off")
                    for p in purchases:
                        aid = p.get("activation_id")
                        if aid and aid not in watch and watch.get(aid) != "off":
                            watch[aid] = None
                            changed = True

                    if changed:
                        set_state(uid, "otp_watch", watch)

                    # Auto-batal: tanpa OTP melebihi ambang -> cancel otomatis (refund)
                    ac = str(get_state(uid, "settings_autocancel", "off") or "off")
                    if ac.isdigit():
                        limit_min = int(ac)
                        now_t = time.time()
                        ac_changed = False
                        for p in purchases:
                            pid = p.get("activation_id")
                            pts = p.get("ts")
                            if not pid or not pts or p.get("autocancel_done"):
                                continue
                            if watch.get(pid):  # OTP sudah pernah masuk (kode tersimpan) — jangan batal
                                continue
                            if now_t - float(pts) >= limit_min * 60:
                                p["autocancel_done"] = True
                                ac_changed = True
                                try:
                                    api.cancel_activation(pid)
                                    watch[pid] = "off"
                                    bot.send_message(
                                        uid,
                                        f"⏹ Aktivasi {pid} dibatalkan otomatis \\({limit_min} menit tanpa OTP\\)\\. Saldo dikembalikan\\.",
                                        parse_mode="MarkdownV2",
                                    )
                                except HeroSMSError:
                                    pass  # gagal (mis. habis/2 menit pertama) — provider refund otomatis saat kedaluwarsa
                        if ac_changed:
                            set_state(uid, "purchases", purchases)
                            set_state(uid, "otp_watch", watch)

                    for aid in list(watch.keys()):
                        if watch.get(aid) == "off":
                            continue  # pemain telah mematikan notifikasi untuk activation ini
                        if not aid or str(aid).strip() in ("", "-", "None"):
                            watch.pop(aid, None)  # bersihkan entri korup dari data lama
                            continue
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
                                changed = True
                                set_state(uid, "otp_watch", watch)
                                log.debug(f"OTP baru aid={aid} uid={uid}")
                                bot.send_message(
                                    uid,
                                    f"🔔 *OTP Baru untuk Aktivasi {aid}*\n\nKode: *{esc(latest_text)}*",
                                    parse_mode="MarkdownV2",
                                )
                        except HeroSMSError as exc:
                            if "HTTP 404" in str(exc):
                                # aktivasi sudah tamat/dihapus — berhenti memantau
                                watch.pop(aid, None)
                                set_state(uid, "otp_watch", watch)
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
