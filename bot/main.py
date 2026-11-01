"""Bot Telegram untuk HeroSMS — coverage seluruh OpenAPI spec (api-en.json).
Versi lebih ramah pengguna: konfirmasi sebelum aksi destructive,
pesan error ramah, dan navigasi yang konsisten."""

from __future__ import annotations

import logging
from typing import Dict

import telebot
from telebot.types import Message, CallbackQuery

from bot.config import BOT_TOKEN, HEROSMS_API_KEY, HEROSMS_BASE_URL
from bot.client import HeroSMS, HeroSMSError
from bot.keyboards import (
    main_menu,
    back_menu,
    activation_actions,
    confirm_keyboard,
    email_menu,
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
    error_msg,
    success_msg,
)
from bot.state import user_state, set_state, get_state, clear_state

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
            _show_active(chat, msg_id, call)

        elif data == "menu:history":
            _show_history(chat, msg_id, call)

        elif data.startswith("buy:country:"):
            country = data.split(":", 2)[2]
            set_state(uid, "buy_country", country)
            _show_services_for_buy(chat, msg_id, uid, country, call)

        elif data.startswith("buy:service:"):
            service = data.split(":", 2)[2]
            _do_purchase(chat, msg_id, uid, service, call)

        elif data.startswith("otp:last:"):
            aid = data.split(":", 2)[2]
            _show_otp_last(chat, msg_id, aid, call)

        elif data.startswith("otp:list:"):
            aid = data.split(":", 2)[2]
            _show_otp_list(chat, msg_id, aid, call)

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
            _show_email_list(chat, msg_id, call)

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
        kb = telebot.types.InlineKeyboardMarkup(row_width=2)
        buttons = []
        for item in items[:20]:
            if isinstance(item, dict):
                name = item.get("name", "-")
                cid = item.get("id", item.get("code", "-"))
                buttons.append(telebot.types.InlineKeyboardButton(
                    f"🌍 {name}", callback_data=f"buy:country:{cid}"))
        kb.add(*buttons)
        kb.add(telebot.types.InlineKeyboardButton("⬅️ Kembali", callback_data="menu:main"))
        _edit(chat, msg_id, "🔹 *Beli Nomor*\n\nPilih negara:", kb)
        _answer(call, "Pilih negara")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Muat Negara", str(exc)), back_menu())
        _answer(call, str(exc), alert=True)


def _show_services_for_buy(chat: int, msg_id: int, uid: int, country: str, call: CallbackQuery) -> None:
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
                    f"📱 {name}", callback_data=f"buy:service:{sid}"))
        kb.add(*buttons)
        kb.add(telebot.types.InlineKeyboardButton("⬅️ Negara", callback_data="menu:buy_activation"))
        _edit(chat, msg_id, f"🔹 *Layanan - {country}*\n\nPilih layanan:", kb)
        _answer(call, "Pilih layanan")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Muat Layanan", str(exc)), back_menu())
        _answer(call, str(exc), alert=True)


def _do_purchase(chat: int, msg_id: int, uid: int, service: str, call: CallbackQuery) -> None:
    country = get_state(uid, "buy_country")
    try:
        act = api.buy_activation(service=service, country=country)
        clear_state(uid)
        _edit(chat, msg_id, purchase_success(act), activation_actions(str(act.get("id", ""))))
        _answer(call, "Nomor dibeli")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Beli Nomor", str(exc)), back_menu())
        _answer(call, str(exc), alert=True)


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
        _edit(chat, msg_id, error_msg("Gagal Selesaikan", str(exc)), activation_actions(aid))
        _answer(call, str(exc), alert=True)


def _do_cancel(chat: int, msg_id: int, aid: str, call: CallbackQuery) -> None:
    try:
        api.cancel_activation(aid)
        _edit(chat, msg_id, success_msg("Aktivasi Dibatalkan", f"Aktivasi ID {aid} telah dibatalkan."), back_menu())
        _answer(call, "Dibatalkan")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Batalkan", str(exc)), activation_actions(aid))
        _answer(call, str(exc), alert=True)


def _do_reactivate(chat: int, msg_id: int, aid: str, call: CallbackQuery) -> None:
    try:
        api.reactivate_activation(aid)
        _edit(chat, msg_id, success_msg("Aktivasi Di-reaktivasi", f"Aktivasi ID {aid} telah di-reaktivasi."), activation_actions(aid))
        _answer(call, "Di-reaktivasi")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Reaktivasi", str(exc)), activation_actions(aid))
        _answer(call, str(exc), alert=True)


def _do_prolong(chat: int, msg_id: int, aid: str, call: CallbackQuery) -> None:
    try:
        api.prolong_activation(aid)
        _edit(chat, msg_id, success_msg("Aktivasi Diperpanjang", f"Aktivasi ID {aid} telah diperpanjang."), activation_actions(aid))
        _answer(call, "Diperpanjang")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Perpanjang", str(exc)), activation_actions(aid))
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


def _show_email_list(chat: int, msg_id: int, call: CallbackQuery) -> None:
    try:
        data = api.email_list()
        items = data.get("data", []) if isinstance(data, dict) else []
        kb = telebot.types.InlineKeyboardMarkup(row_width=1)
        for item in items[:15]:
            if isinstance(item, dict):
                eid = item.get("id", "-")
                email = item.get("email") or item.get("domain", "-")
                kb.add(telebot.types.InlineKeyboardButton(
                    f"📬 {email} (ID {eid})", callback_data=f"email:detail:{eid}"))
        kb.add(telebot.types.InlineKeyboardButton("🔄 Segarkan", callback_data="email:list"))
        kb.add(telebot.types.InlineKeyboardButton("⬅️ Kembali", callback_data="menu:email"))
        _edit(chat, msg_id, email_list_msg(data), kb)
        _answer(call, "Daftar email dimuat")
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

def _show_active(chat: int, msg_id: int, call: CallbackQuery) -> None:
    try:
        data = api.active_activations()
        items = data.get("data", []) if isinstance(data, dict) else []
        kb = telebot.types.InlineKeyboardMarkup(row_width=1)
        for item in items[:15]:
            if isinstance(item, dict):
                aid = item.get("id", "-")
                phone = item.get("phone", "-")
                kb.add(telebot.types.InlineKeyboardButton(
                    f"📱 {phone} (ID {aid})", callback_data=f"act:view:{aid}"))
        kb.add(telebot.types.InlineKeyboardButton("🔄 Segarkan", callback_data="menu:active"))
        kb.add(telebot.types.InlineKeyboardButton("⬅️ Kembali", callback_data="menu:main"))
        _edit(chat, msg_id, active_list_msg(data), kb)
        _answer(call, "Aktivasi aktif dimuat")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Muat Aktif", str(exc)), back_menu())
        _answer(call, str(exc), alert=True)


def _show_history(chat: int, msg_id: int, call: CallbackQuery) -> None:
    try:
        data = api.activation_history()
        _edit(chat, msg_id, history_msg(data), back_menu())
        _answer(call, "Riwayat dimuat")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Muat Riwayat", str(exc)), back_menu())
        _answer(call, str(exc), alert=True)


def _show_activation_detail(chat: int, msg_id: int, aid: str, call: CallbackQuery) -> None:
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
        _edit(chat, msg_id, activation_detail(act), activation_actions(aid))
        _answer(call, "Detail aktivasi")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Muat Detail", str(exc)), back_menu())
        _answer(call, str(exc), alert=True)


def _show_otp_last(chat: int, msg_id: int, aid: str, call: CallbackQuery) -> None:
    try:
        data = api.otp_last(aid)
        _edit(chat, msg_id, otp_msg(aid, data), activation_actions(aid))
        _answer(call, "OTP dimuat")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Ambil OTP", str(exc)), activation_actions(aid))
        _answer(call, str(exc), alert=True)


def _show_otp_list(chat: int, msg_id: int, aid: str, call: CallbackQuery) -> None:
    try:
        data = api.otp_list(aid)
        _edit(chat, msg_id, otp_msg(aid, data), activation_actions(aid))
        _answer(call, "Daftar OTP dimuat")
    except HeroSMSError as exc:
        _edit(chat, msg_id, error_msg("Gagal Ambil Daftar OTP", str(exc)), activation_actions(aid))
        _answer(call, str(exc), alert=True)


# ── Run ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info("Bot HeroSMS dimulai…")
    bot.infinity_polling(skip_pending=True)
