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
    )
    kb.add(InlineKeyboardButton("❌ Tutup", callback_data="menu:close"))
    return kb


def back_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("⬅️ Kembali ke Menu", callback_data="menu:main"))
    return kb


def activation_actions(activation_id: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📨 OTP Terakhir", callback_data=f"otp:last:{activation_id}"),
        InlineKeyboardButton("📋 Semua OTP", callback_data=f"otp:list:{activation_id}"),
        # Destructive actions now require confirmation
        InlineKeyboardButton("✅ Selesai", callback_data=f"act:confirm:finish:{activation_id}"),
        InlineKeyboardButton("❌ Batalkan", callback_data=f"act:confirm:cancel:{activation_id}"),
        InlineKeyboardButton("🔄 Reaktivasi", callback_data=f"act:reactivate:{activation_id}"),
        InlineKeyboardButton("⏳ Perpanjang", callback_data=f"act:prolong:{activation_id}"),
    )
    kb.add(InlineKeyboardButton("⬅️ Daftar Aktif", callback_data="menu:active"))
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
