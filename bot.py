"""Bot Telegram untuk HeroSMS — coverage seluruh OpenAPI spec (api-en.json)."""

from __future__ import annotations

import logging
from typing import Dict, Optional

import telebot
from telebot.types import Message, CallbackQuery

from config import BOT_TOKEN, HEROSMS_API_KEY, HEROSMS_BASE_URL
from herosms import HeroSMS, HeroSMSError
from keyboards import main_menu, back_menu, activation_actions
from messages import (
    esc, bold, code, header, balance_msg, stats_msg, countries_msg,
    services_msg, prices_msg, activation_detail, active_list_msg,
    history_msg, otp_msg, purchase_success, welcome_msg,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("herosms-bot")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="MarkdownV2")
api = HeroSMS(HEROSMS_API_KEY, HEROSMS_BASE_URL)

# State per user untuk alur multi‑langkah (beli nomor, dll.)
user_state: Dict[int, Dict] = {}


def _set_state(uid: int, key: str, val) -> None:
    user_state.setdefault(uid, {})[key] = val


def _get_state(uid: int, key: str, default=None):
    return user_state.get(uid, {}).get(key, default)


def _clear_state(uid: int) -> None:
    user_state.pop(uid, None)


# ── Command /start ──────────────────────────────────────────────

@bot.message_handler(commands=["start"])
def cmd_start(message: Message) -> None:
    bot.reply_to(message, welcome_msg(), reply_markup=main_menu())


@bot.message_handler(commands=["menu"])
def cmd_menu(message: Message) -> None:
    bot.send_message(message.chat.id, "Menu utama", reply_markup=main_menu())


# ── Callback router ─────────────────────────────────────────────

@bot.callback_query_handler(func=lambda call: True)
def on_callback(call: CallbackQuery) -> None:
    data = call.data or ""
    uid = call.from_user.id
    chat = call.message.chat.id
    msg_id = call.message.message_id

    try:
        if data == "menu:main":
            bot.edit_message_text(welcome_msg(), chat, msg_id, reply_markup=main_menu())

        elif data == "menu:close":
            bot.edit_message_text("Menu ditutup. Ketik /start untuk buka kembali.", chat, msg_id)

        elif data == "menu:balance":
            _show_balance(chat, msg_id, uid, call)

        elif data == "menu:stats":
            _show_stats(chat, msg_id)

        elif data == "menu:countries":
            _show_countries(chat, msg_id)

        elif data == "menu:services":
            _show_services(chat, msg_id)

        elif data == "menu:prices":
            _show_prices(chat, msg_id)

        elif data == "menu:buy_activation":
            _start_buy_flow(chat, msg_id, uid)

        elif data == "menu:active":
            _show_active(chat, msg_id)

        elif data == "menu:history":
            _show_history(chat, msg_id)

        elif data.startswith("buy:country:"):
            country = data.split(":", 2)[2]
            _set_state(uid, "buy_country", country)
            _show_services_for_buy(chat, msg_id, uid, country)

        elif data.startswith("buy:service:"):
            service = data.split(":", 2)[2]
            _do_purchase(chat, msg_id, uid, service)

        elif data.startswith("otp:last:"):
            aid = data.split(":", 2)[2]
            _show_otp_last(chat, msg_id, aid)

        elif data.startswith("otp:list:"):
            aid = data.split(":", 2)[2]
            _show_otp_list(chat, msg_id, aid)

        elif data.startswith("act:finish:"):
            aid = data.split(":", 2)[2]
            _do_act(chat, msg_id, "finish", aid)

        elif data.startswith("act:cancel:"):
            aid = data.split(":", 2)[2]
            _do_act(chat, msg_id, "cancel", aid)

        elif data.startswith("act:reactivate:"):
            aid = data.split(":", 2)[2]
            _do_act(chat, msg_id, "reactivate", aid)

        elif data.startswith("act:prolong:"):
            aid = data.split(":", 2)[2]
            _do_act(chat, msg_id, "prolong", aid)

        else:
            bot.answer_callback_query(call.id, "Tombol tidak dikenal.")

    except HeroSMSError as exc:
        bot.answer_callback_query(call.id, f"Error: {exc}", show_alert=True)
    except Exception as exc:  # noqa: BLE001
        log.exception("callback error")
        bot.answer_callback_query(call.id, f"Error tak terduga: {exc}", show_alert=True)


# ── Helper tampilan ─────────────────────────────────────────────

def _edit(chat: int, msg_id: int, text: str, markup=None) -> None:
    try:
        bot.edit_message_text(text, chat, msg_id, reply_markup=markup)
    except Exception:
        bot.send_message(chat, text, reply_markup=markup)


def _answer(call: CallbackQuery, text: str) -> None:
    bot.answer_callback_query(call.id, text)


def _show_balance(chat: int, msg_id: int, uid: int, call: Optional[CallbackQuery] = None) -> None:
    try:
        data = api.user_stats()
        _edit(chat, msg_id, balance_msg(data), back_menu())
        if call:
            bot.answer_callback_query(call.id, "Saldo dimuat")
    except HeroSMSError as exc:
        _edit(chat, msg_id, f"{header('Gagal Cek Saldo')}\n{esc(str(exc))}", back_menu())
        if call:
            bot.answer_callback_query(call.id, f"Error: {exc}", show_alert=True)


def _show_stats(chat: int, msg_id: int) -> None:
    try:
        data = api.user_stats()
        _edit(chat, msg_id, stats_msg(data), back_menu())
    except HeroSMSError as exc:
        _edit(chat, msg_id, f"{header('Gagal Cek Statistik')}\n{esc(str(exc))}", back_menu())


def _show_countries(chat: int, msg_id: int) -> None:
    try:
        data = api.legacy("getCountries")
        _edit(chat, msg_id, countries_msg(data), back_menu())
    except HeroSMSError as exc:
        _edit(chat, msg_id, f"{header('Gagal Muat Negara')}\n{esc(str(exc))}", back_menu())


def _show_services(chat: int, msg_id: int) -> None:
    try:
        data = api.legacy("getServicesList")
        _edit(chat, msg_id, services_msg(data), back_menu())
    except HeroSMSError as exc:
        _edit(chat, msg_id, f"{header('Gagal Muat Layanan')}\n{esc(str(exc))}", back_menu())


def _show_prices(chat: int, msg_id: int) -> None:
    try:
        data = api.legacy("getPrices")
        _edit(chat, msg_id, prices_msg(data), back_menu())
    except HeroSMSError as exc:
        _edit(chat, msg_id, f"{header('Gagal Muat Harga')}\n{esc(str(exc))}", back_menu())


def _start_buy_flow(chat: int, msg_id: int, uid: int) -> None:
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
        _edit(chat, msg_id, header("Beli Nomor", "Pilih negara"), kb)
    except HeroSMSError as exc:
        _edit(chat, msg_id, f"{header('Gagal Muat Negara')}\n{esc(str(exc))}", back_menu())


def _show_services_for_buy(chat: int, msg_id: int, uid: int, country: str) -> None:
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
        _edit(chat, msg_id, header(f"Layanan - {country}", "Pilih layanan"), kb)
    except HeroSMSError as exc:
        _edit(chat, msg_id, f"{header('Gagal Muat Layanan')}\n{esc(str(exc))}", back_menu())


def _do_purchase(chat: int, msg_id: int, uid: int, service: str) -> None:
    country = _get_state(uid, "buy_country")
    try:
        act = api.buy_activation(service=service, country=country)
        _clear_state(uid)
        _edit(chat, msg_id, purchase_success(act), activation_actions(str(act.get("id", ""))))
    except HeroSMSError as exc:
        _edit(chat, msg_id, f"{header('Gagal Beli Nomor')}\n{esc(str(exc))}", back_menu())


def _show_active(chat: int, msg_id: int) -> None:
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
    except HeroSMSError as exc:
        _edit(chat, msg_id, f"{header('Gagal Muat Aktif')}\n{esc(str(exc))}", back_menu())


def _show_history(chat: int, msg_id: int) -> None:
    try:
        data = api.activation_history()
        _edit(chat, msg_id, history_msg(data), back_menu())
    except HeroSMSError as exc:
        _edit(chat, msg_id, f"{header('Gagal Muat Riwayat')}\n{esc(str(exc))}", back_menu())


def _show_otp_last(chat: int, msg_id: int, aid: str) -> None:
    try:
        data = api.otp_last(aid)
        _edit(chat, msg_id, otp_msg(aid, data), activation_actions(aid))
    except HeroSMSError as exc:
        _edit(chat, msg_id, f"{header('Gagal Ambil OTP')}\n{esc(str(exc))}", activation_actions(aid))


def _show_otp_list(chat: int, msg_id: int, aid: str) -> None:
    try:
        data = api.otp_list(aid)
        _edit(chat, msg_id, otp_msg(aid, data), activation_actions(aid))
    except HeroSMSError as exc:
        _edit(chat, msg_id, f"{header('Gagal Ambil Daftar OTP')}\n{esc(str(exc))}", activation_actions(aid))


def _do_act(chat: int, msg_id: int, action: str, aid: str) -> None:
    try:
        if action == "finish":
            api.finish_activation(aid)
            _edit(chat, msg_id, f"{header('✅ Selesai', f'Aktivasi {aid} selesai.')}", back_menu())
        elif action == "cancel":
            api.cancel_activation(aid)
            _edit(chat, msg_id, f"{header('❌ Dibatalkan', f'Aktivasi {aid} dibatalkan.')}", back_menu())
        elif action == "reactivate":
            api.reactivate_activation(aid)
            _edit(chat, msg_id, f"{header('🔄 Reaktivasi', f'Aktivasi {aid} di-reaktivasi.')}", activation_actions(aid))
        elif action == "prolong":
            api.prolong_activation(aid)
            _edit(chat, msg_id, f"{header('⏳ Diperpanjang', f'Aktivasi {aid} diperpanjang.')}", activation_actions(aid))
    except HeroSMSError as exc:
        _edit(chat, msg_id, f"{header(f'Gagal {action}')}\n{esc(str(exc))}", activation_actions(aid))


# ── fallback untuk callIfAvailable placeholder ──
def call_if_available():
    class _C:
        id = None
    return _C()


# ── Run ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info("Bot HeroSMS dimulai…")
    bot.infinity_polling(skip_pending=True)
