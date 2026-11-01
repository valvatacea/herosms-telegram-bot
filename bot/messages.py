"""Format pesan agar rapi, ramah pengguna, dan mudah dibaca."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List


def esc(text: str) -> str:
    """Escape karakter khusus MarkdownV2."""
    text = str(text)
    for ch in r"_*[]()~`>#+-=|{}.!":
        text = text.replace(ch, "\\" + ch)
    return text


def bold(text: str) -> str:
    return f"*{esc(text)}*"


def code(text: str) -> str:
    return f"`{esc(text)}`"


_FLAG_ALIAS = {
    "russia": "Russian Federation",
    "usa": "United States",
    "united states of america": "United States",
    "uk": "United Kingdom",
    "england": "United Kingdom",
    "south korea": "Korea, Republic of",
    "north korea": "Korea, Democratic People's Republic of",
    "vietnam": "Viet Nam",
    "turkey": "Türkiye",
    "iran": "Iran, Islamic Republic of",
    "syria": "Syrian Arab Republic",
    "laos": "Lao People's Democratic Republic",
    "moldova": "Moldova, Republic of",
    "tanzania": "Tanzania, United Republic of",
    "venezuela": "Venezuela, Bolivarian Republic of",
    "bolivia": "Bolivia, Plurinational State of",
    "taiwan": "Taiwan, Province of China",
    "palestine": "Palestine, State of",
    "dr congo": "Congo, The Democratic Republic of the",
    "ivory coast": "Côte d'Ivoire",
    "czech": "Czechia",
    "papua": "Papua New Guinea",
    "uae": "United Arab Emirates",
    "salvador": "El Salvador",
    "swaziland": "Eswatini",
    "bosnia": "Bosnia and Herzegovina",
    "brunei": "Brunei Darussalam",
    "reunion": "Réunion",
    "cape verde": "Cabo Verde",
    "kosovo": "FLAG:🇽🇰",
}


def flag(name: str) -> str:
    """Emoji bendera dari nama negara (fallback 🌍)."""
    try:
        import pycountry
        query = _FLAG_ALIAS.get(str(name).strip().lower(), str(name))
        if query.startswith("FLAG:"):
            return query[5:]
        c = pycountry.countries.lookup(query)
        return "".join(chr(0x1F1E6 + ord(ch) - 65) for ch in c.alpha_2)
    except Exception:
        return "🌍"


def header(title: str, subtitle: str = "") -> str:
    lines = [f"🔹 *{esc(title)}*"]
    if subtitle:
        lines.append(f"_{esc(subtitle)}_")
    return "\n".join(lines) + "\n"


def balance_msg(data: Dict, price_str: str = "") -> str:
    bal = data.get("balance", data.get("available", "—"))
    currency = data.get("currency", "")
    bal_disp = price_str or f"{code(str(bal))} {code(str(currency))}"
    return (
        f"{header('💰 Saldo Akun', 'HeroSMS')}\n"
        f"{bold('Tersedia:')} {bal_disp}\n"
    )


def stats_msg(data: Dict) -> str:
    lines = [header("📊 Statistik Pengguna", "Ringkasan akun HeroSMS")]
    node = data.get("data", data) if isinstance(data, dict) else {}
    if isinstance(node, dict) and node:
        for country, services in node.items():
            if isinstance(services, dict):
                for service, st in services.items():
                    if isinstance(st, dict):
                        lines.append(
                            f"• {esc(str(country))}/{esc(str(service))}: "
                            f"sukses {esc(str(st.get('success','-')))} dari {esc(str(st.get('count','-')))} "
                            f"\\({esc(str(st.get('percent','-')))}%\\)"
                        )
                    else:
                        lines.append(f"• {esc(str(country))}/{esc(str(service))}: {esc(str(st))}")
            else:
                lines.append(f"• {esc(str(country))}: {esc(str(services))}")
    else:
        lines.append("Belum ada statistik aktivasi\\.")
    return "\n".join(lines) + "\n"


def countries_msg(data: Dict) -> str:
    if isinstance(data, dict) and isinstance(data.get("data"), (list, dict)):
        data = data["data"]
    items = list(data.values()) if isinstance(data, dict) else data
    if not isinstance(items, list):
        items = [items]
    lines = [header("🌍 Daftar Negara", "Pilih negara untuk beli nomor")]
    if not items:
        return lines[0] + "\nBelum ada data negara\\.\n"
    for item in items[:30]:
        if isinstance(item, dict):
            name = item.get("eng", item.get("name", "-"))
            code_ = item.get("code", item.get("id", "-"))
            lines.append(f"{flag(name)} {esc(name)} — {code(code_)}")
        else:
            lines.append(f"• {esc(str(item))}")
    if len(items) > 30:
        lines.append(f"\n_…dan {len(items) - 30} negara lainnya\\._")
    return "\n".join(lines) + "\n"


def services_msg(data: Dict) -> str:
    if isinstance(data, dict) and isinstance(data.get("services"), list):
        data = data["services"]
    items = list(data.values()) if isinstance(data, dict) else data
    if not isinstance(items, list):
        items = [items]
    lines = [header("📱 Daftar Layanan", "Pilih layanan verifikasi")]
    if not items:
        return lines[0] + "\nBelum ada data layanan\\.\n"
    for item in items[:40]:
        if isinstance(item, dict):
            name = item.get("name", "-")
            sid = item.get("id", item.get("code", "-"))
            lines.append(f"📱 {esc(name)} — {code(str(sid))}")
        else:
            lines.append(f"• {esc(str(item))}")
    if len(items) > 40:
        lines.append(f"\n_…dan {len(items) - 40} layanan lainnya\\._")
    return "\n".join(lines) + "\n"


def prices_msg(data: Dict) -> str:
    lines = [header("💵 Harga Aktivasi", "Per layanan / negara")]
    if isinstance(data, dict):
        if isinstance(data.get("data"), (list, dict)):
            data = data["data"]
        entries = list(data.items()) if isinstance(data, dict) else []
        if not entries:
            return lines[0] + "\nBelum ada data harga\\.\n"
        for key, val in entries[:15]:
            s = str(val)
            if len(s) > 80:
                s = s[:77] + "..."
            lines.append(f"• {esc(str(key))}: {code(s)}")
        if len(entries) > 15:
            lines.append(f"\n_…dan {len(entries) - 15} negara lainnya\\._")
    else:
        lines.append(code(str(data)[:300]))
    return "\n".join(lines) + "\n"


_STATUS_NAMES = {
    1: "Siap",
    2: "Kode diterima",
    3: "Kirim ulang diminta",
    4: "Menunggu OTP",
    6: "Selesai",
    8: "Dibatalkan",
    10: "Dikembalikan",
}


def status_name(s) -> str:
    """Kode status angka -> teks mudah dibaca."""
    if s in (None, "", "-"):
        return "-"
    try:
        return _STATUS_NAMES.get(int(s), str(s))
    except (TypeError, ValueError):
        return str(s)


def _fmt_dt(iso: str) -> str:
    """ISO 8601 UTC → 'd bulan jam:menit:detik WIB' (+7)."""
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return (dt + timedelta(hours=7)).strftime("%d %b %Y %H:%M:%S WIB")
    except ValueError:
        return str(iso)


def _remaining_bar(act: Dict) -> str:
    """Bar sisa durasi (snapshot saat render): 🟩🟩…⬜ + sisa mm:ss."""
    try:
        c = datetime.fromisoformat(str(act.get("createdAt", "")).replace("Z", "+00:00"))
        e = datetime.fromisoformat(str(act.get("expiredAt", "")).replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        if not c or not e or e <= now:
            return "" if not e else "⌛ Kedaluwarsa"
        total = (e - c).total_seconds()
        if total <= 0:
            return ""
        left = (e - now).total_seconds()
        frac = max(0.0, min(1.0, left / total))
        filled = round(frac * 10)
        bar = "🟩" * filled + "⬜" * (10 - filled)
        return f"{bar} sisa {int(left // 60):02d}:{int(left % 60):02d}"
    except Exception:
        return ""


def activation_detail(act: Dict, price_str: str = "") -> str:
    cost_line = price_str or f"{code(str(act.get('cost', act.get('price','-'))))} {code(str(act.get('currency','')))}"
    lines = [
        f"{header('📋 Detail Aktivasi', f'ID: {code(str(act.get("id","-")))}')}",
        f"{bold('Status:')} {esc(status_name(act.get('status','-')))}",
        f"{bold('Nomor:')} {code(str(act.get('phone','-')))}",
        f"{bold('Kode negara:')} {code(str(act.get('phoneCode', act.get('countryPhoneCode','-'))))}",
        f"{bold('Layanan:')} {esc(str(act.get('serviceName', act.get('service','-'))))}",
        f"{bold('Negara:')} {esc(str(act.get('countryName', act.get('country','-'))))}",
        f"{bold('Biaya:')} {cost_line}",
    ]
    more = act.get("moreCodes")
    if more:
        lines.append(f"{bold('Kode terima:')} {esc(str(more))}")
    exp = act.get("expiredAt")
    if exp and str(exp) not in ("-", ""):
        lines.append(f"{bold('Kedaluwarsa:')} {code(_fmt_dt(exp))}")
        bar = _remaining_bar(act)
        if bar:
            lines.append(bar)
    return "\n".join(lines) + "\n"


def active_list_msg(data: Dict) -> str:
    items = data.get("data", []) if isinstance(data, dict) else []
    lines = [header("📋 Aktivasi Aktif", "Klik nomor untuk lihat detail & OTP")]
    if not items:
        return lines[0] + "\nBelum ada aktivasi aktif\\. Beli nomor dulu di menu 🛒\\.\n"
    for item in items[:15]:
        if isinstance(item, dict):
            aid = item.get("id", "-")
            phone = item.get("phone", "-")
            status = status_name(item.get("status", "-"))
            disp = item.get("costDisp") or esc(str(item.get("cost", item.get("price", "-"))))
            lines.append(
                f"• {code(str(aid))} \\| {code(str(phone))} \\| {esc(str(status))} \\| {disp}"
            )
        else:
            lines.append(f"• {esc(str(item))}")
    if len(items) > 15:
        lines.append(f"\n_…dan {len(items) - 15} aktivasi lain._")
    return "\n".join(lines) + "\n"


def history_msg(data: Dict) -> str:
    items = data.get("data", []) if isinstance(data, dict) else []
    lines = [header("📜 Riwayat Aktivasi", "Aktivasi yang sudah selesai")]
    if not items:
        return lines[0] + "\nBelum ada riwayat aktivasi\\.\n"
    for item in items[:15]:
        if isinstance(item, dict):
            aid = item.get("id", "-")
            phone = item.get("phone", "-")
            status = status_name(item.get("status", "-"))
            cost = item.get("cost", "-")
            date = item.get("createDate", "-")
            lines.append(
                f"• {code(str(aid))} \\| {code(str(phone))} \\| {esc(str(status))} \\| {code(str(cost))} \\| {esc(str(date))}"
            )
    if len(items) > 15:
        lines.append(f"\n_…dan {len(items) - 15} entri lain\\._")
    return "\n".join(lines) + "\n"


def otp_msg(activation_id: str, data: Any) -> str:
    lines = [header(f"📨 OTP - Aktivasi {code(str(activation_id))}", "Kode verifikasi")]
    if isinstance(data, dict):
        code_val = data.get("code", data.get("otp", "-"))
        date = data.get("date", data.get("createDate", "-"))
        lines.append(f"{bold('Kode:')} `{code(str(code_val))}`")
        if date != "-":
            lines.append(f"{bold('Waktu:')} {code(str(date))}")
    elif isinstance(data, list):
        if not data:
            lines.append("Belum ada kode OTP yang diterima\\.")
        for i, item in enumerate(data[:10], 1):
            if isinstance(item, dict):
                code_val = item.get("code", item.get("otp", "-"))
                date = item.get("date", item.get("createDate", "-"))
                lines.append(f"{i}. `{code(str(code_val))}` \\({code(str(date))}\\)")
            else:
                lines.append(f"{i}. {code(str(item))}")
    else:
        lines.append(code(str(data)))
    return "\n".join(lines) + "\n"


def purchase_success(act: Dict, price_str: str = "") -> str:
    cost_line = price_str or f"{code(str(act.get('cost', act.get('price','-'))))} {code(str(act.get('currency','')))}"
    lines = [
        f"{header('✅ Nomor Dibeli', 'Aktivasi OTP SMS berhasil dibuat')}",
        f"{bold('ID:')} {code(str(act.get('id','-')))}",
        f"{bold('Nomor:')} {code(str(act.get('phone','-')))}",
        f"{bold('Kode negara:')} {code(str(act.get('phoneCode', act.get('countryPhoneCode','-'))))}",
        f"{bold('Layanan:')} {esc(str(act.get('serviceName', act.get('service','-'))))}",
        f"{bold('Negara:')} {esc(str(act.get('countryName', act.get('country','-'))))}",
        f"{bold('Biaya:')} {cost_line}",
    ]
    exp = act.get("expiredAt")
    if exp and str(exp) not in ("-", ""):
        lines.append(f"{bold('Kedaluwarsa:')} {code(_fmt_dt(exp))}")
        bar = _remaining_bar(act)
        if bar:
            lines.append(bar)
    lines.append(f"\n👉 Klik tombol di bawah untuk ambil OTP atau selesaikan aktivasi\\.")
    return "\n".join(lines) + "\n"


def welcome_msg() -> str:
    return (
        f"{header('🤖 HeroSMS Bot', 'Manajemen aktivasi SMS/OTP via Telegram')}\n"
        "Selamat datang\\! Bot ini membantu Anda:\n"
        f"• {esc('Cek saldo & statistik akun')}\n"
        f"• {esc('Lihat negara, layanan, dan harga')}\n"
        f"• {esc('Beli nomor verifikasi (SMS & email)')}\n"
        f"• {esc('Terima OTP langsung di chat')}\n"
        f"• {esc('Selesaikan, batalkan, atau perpanjang aktivasi')}\n"
        "\nPilih menu di bawah untuk memulai 👇\n"
    )


def confirm_msg(action_label: str, detail: str) -> str:
    return (
        f"{header('⚠️ Konfirmasi', 'Tindakan tidak dapat dibatalkan')}\n"
        f"{bold('Aksi:')} {esc(action_label)}\n"
        f"{bold('Detail:')} {esc(detail)}\n\n"
        "Lanjutkan?"
    )


def error_msg(title: str, detail: str) -> str:
    return f"{header('❌ ' + esc(title), '')}\n{esc(detail)}\n"


def success_msg(title: str, detail: str) -> str:
    return f"{header('✅ ' + esc(title), '')}\n{esc(detail)}\n"


def email_list_msg(data: Dict) -> str:
    items = data.get("data", []) if isinstance(data, dict) else []
    lines = [header("📬 Aktivasi Email Aktif", "Daftar pembelian email")]
    if not items:
        return lines[0] + "\nBelum ada aktivasi email\\.\n"
    for item in items[:15]:
        if isinstance(item, dict):
            eid = item.get("id", "-")
            email = item.get("email") or item.get("domain", "-")
            status = item.get("status", "-")
            lines.append(f"• {code(str(eid))} | {esc(str(email))} | {esc(str(status))}")
    if len(items) > 15:
        lines.append(f"\n_…dan {len(items) - 15} entri lain\\._")
    return "\n".join(lines) + "\n"


def email_detail_msg(data: Dict) -> str:
    lines = [header("📧 Detail Aktivasi Email", f"ID: {code(str(data.get('id','-')))}")]
    lines.append(f"{bold('Email/Domain:')} {esc(str(data.get('email') or data.get('domain','-')))}")
    lines.append(f"{bold('Status:')} {esc(str(data.get('status','-')))}")
    lines.append(f"{bold('Layanan:')} {esc(str(data.get('service','-')))}")
    if data.get("cost"):
        lines.append(f"{bold('Biaya:')} {code(str(data.get('cost')))} {code(str(data.get('currency','')))}")
    if data.get("createDate"):
        lines.append(f"{bold('Dibuat:')} {code(str(data.get('createDate')))}")
    return "\n".join(lines) + "\n"


def buy_confirm_msg(country: str, service: str, price: str, currency: str = "", duration: str = "-", price_str: str = "") -> str:
    p_line = price_str or f"{code(str(price))} {code(str(currency))}"
    return (
        f"{header('🛒 Konfirmasi Pembelian', 'Review sebelum transaksi')}\n"
        f"{bold('Negara:')} {esc(str(country))}\n"
        f"{bold('Layanan:')} {esc(str(service))}\n"
        f"{bold('Harga:')} {p_line}\n"
        f"{bold('Durasi:')} {esc(str(duration))}\n"
        f"{bold('Nomor:')} akan ditampilkan setelah pembelian\\.\n\n"
        "Lanjutkan pembelian?"
    )
