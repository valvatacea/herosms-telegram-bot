"""Format pesan agar rapi, ramah pengguna, dan mudah dibaca (ID/EN via lang)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from bot.lang import t


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


def balance_msg(data: Dict, price_str: str = "", lang: str = "id") -> str:
    bal = data.get("balance", data.get("available", "—"))
    currency = data.get("currency", "")
    bal_disp = price_str or f"{code(str(bal))} {code(str(currency))}"
    return (
        f"{header(t(lang, 'saldo_judul'), t(lang, 'saldo_sub'))}\n"
        f"{bold(t(lang, 'tersedia'))} {bal_disp}\n"
    )


def stats_msg(data: Dict, lang: str = "id") -> str:
    lines = [header(t(lang, "stat_judul"), t(lang, "stat_sub"))]
    node = data.get("data", data) if isinstance(data, dict) else {}
    if isinstance(node, dict) and node:
        for country, services in node.items():
            if isinstance(services, dict):
                for service, st in services.items():
                    if isinstance(st, dict):
                        ratio = t(lang, "stat_sukses_dari",
                                  s=st.get('success', '-'), c=st.get('count', '-'))
                        lines.append(
                            f"• {esc(str(country))}/{esc(str(service))}: "
                            f"{esc(ratio)} "
                            f"\\({esc(str(st.get('percent','-')))}%\\)"
                        )
                    else:
                        lines.append(f"• {esc(str(country))}/{esc(str(service))}: {esc(str(st))}")
            else:
                lines.append(f"• {esc(str(country))}: {esc(str(services))}")
    else:
        lines.append(esc(t(lang, "stat_kosong")))
    return "\n".join(lines) + "\n"





_STATUS_KEYS = {
    1: "st_siap",
    2: "st_kode",
    3: "st_resend",
    4: "st_menunggu",
    6: "st_selesai",
    8: "st_batal",
    10: "st_refund",
}


def status_name(s, lang: str = "id") -> str:
    """Kode status angka -> teks mudah dibaca."""
    if s in (None, "", "-"):
        return "-"
    try:
        k = _STATUS_KEYS.get(int(s))
        return t(lang, k) if k else str(s)
    except (TypeError, ValueError):
        return str(s)


def _fmt_dt(iso: str) -> str:
    """ISO 8601 UTC → 'd bulan jam:menit:detik WIB' (+7)."""
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return (dt + timedelta(hours=7)).strftime("%d %b %Y %H:%M:%S WIB")
    except ValueError:
        return str(iso)


def _remaining_bar(act: Dict, lang: str = "id") -> str:
    """Bar sisa durasi (snapshot saat render): 🟩🟩…⬜ + sisa mm:ss."""
    try:
        c = datetime.fromisoformat(str(act.get("createdAt", "")).replace("Z", "+00:00"))
        e = datetime.fromisoformat(str(act.get("expiredAt", "")).replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        if not c or not e or e <= now:
            return "" if not e else t(lang, "kedaluwarsa_flag")
        total = (e - c).total_seconds()
        if total <= 0:
            return ""
        left = (e - now).total_seconds()
        frac = max(0.0, min(1.0, left / total))
        filled = round(frac * 10)
        bar = "🟩" * filled + "⬜" * (10 - filled)
        return f"{bar} {t(lang, 'sisa').split()[0]} {int(left // 60):02d}:{int(left % 60):02d}"
    except Exception:
        return ""


def activation_detail(act: Dict, price_str: str = "", lang: str = "id") -> str:
    cost_line = price_str or f"{code(str(act.get('cost', act.get('price','-'))))} {code(str(act.get('currency','')))}"
    lines = [
        f"{header(t(lang, 'detail_judul'), 'ID: ' + str(act.get('id', '-')))}",
        f"{bold(t(lang, 'status'))} {esc(status_name(act.get('status','-'), lang))}",
        f"{bold(t(lang, 'nomor'))} {code(str(act.get('phone','-')))}",
        f"{bold(t(lang, 'kode_negara'))} {code(str(act.get('phoneCode', act.get('countryPhoneCode','-'))))}",
        f"{bold(t(lang, 'layanan'))} {esc(str(act.get('serviceName', act.get('service','-'))))}",
        f"{bold(t(lang, 'negara'))} {esc(str(act.get('countryName', act.get('country','-'))))}",
        f"{bold(t(lang, 'biaya'))} {cost_line}",
    ]
    more = act.get("moreCodes")
    if more:
        lines.append(f"{bold(t(lang, 'kode_terima'))} {esc(str(more))}")
    exp = act.get("expiredAt")
    if exp and str(exp) not in ("-", ""):
        lines.append(f"{bold(t(lang, 'kedaluwarsa'))} {code(_fmt_dt(exp))}")
        bar = _remaining_bar(act, lang)
        if bar:
            lines.append(bar)
    return "\n".join(lines) + "\n"


def active_list_msg(data: Dict, lang: str = "id") -> str:
    items = data.get("data", []) if isinstance(data, dict) else []
    lines = [header(t(lang, "aktif_judul"), t(lang, "aktif_sub"))]
    if not items:
        return lines[0] + "\n" + esc(t(lang, "aktif_kosong")) + "\n"
    for item in items[:15]:
        if isinstance(item, dict):
            aid = item.get("id", "-")
            phone = item.get("phone", "-")
            status = status_name(item.get("status", "-"), lang)
            disp = item.get("costDisp") or esc(str(item.get("cost", item.get("price", "-"))))
            lines.append(
                f"• {code(str(aid))} \\| {code(str(phone))} \\| {esc(str(status))} \\| {disp}"
            )
        else:
            lines.append(f"• {esc(str(item))}")
    if len(items) > 15:
        lines.append(f"\n_{t(lang, 'aktif_lainnya', n=len(items) - 15)}\\._")
    return "\n".join(lines) + "\n"


def history_msg(data: Dict, lang: str = "id") -> str:
    items = data.get("data", []) if isinstance(data, dict) else []
    lines = [header(t(lang, "riwayat_judul"), t(lang, "riwayat_sub"))]
    if not items:
        return lines[0] + "\n" + esc(t(lang, "riwayat_kosong")) + "\n"
    for item in items[:15]:
        if isinstance(item, dict):
            aid = item.get("id", "-")
            phone = item.get("phone", "-")
            status = status_name(item.get("status", "-"), lang)
            cost = item.get("cost", "-")
            date = item.get("createDate", "-")
            lines.append(
                f"• {code(str(aid))} \\| {code(str(phone))} \\| {esc(str(status))} \\| {code(str(cost))} \\| {esc(str(date))}"
            )
    if len(items) > 15:
        lines.append(f"\n_{t(lang, 'riwayat_lainnya', n=len(items) - 15)}\\._")
    return "\n".join(lines) + "\n"


def otp_msg(activation_id: str, data: Any, lang: str = "id") -> str:
    judul = t(lang, "otp_judul", a=str(activation_id))
    lines = [header(judul, t(lang, "otp_sub"))]
    if isinstance(data, dict):
        code_val = data.get("code", data.get("otp", "-"))
        date = data.get("date", data.get("createDate", "-"))
        lines.append(f"{bold(t(lang, 'kode'))} `{code(str(code_val))}`")
        if date != "-":
            lines.append(f"{bold(t(lang, 'waktu'))} {code(str(date))}")
    elif isinstance(data, list):
        if not data:
            lines.append(esc(t(lang, "otp_kosong")))
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


def purchase_success(act: Dict, price_str: str = "", lang: str = "id") -> str:
    cost_line = price_str or f"{code(str(act.get('cost', act.get('price','-'))))} {code(str(act.get('currency','')))}"
    lines = [
        f"{header(t(lang, 'sukses_judul'), t(lang, 'sukses_sub'))}",
        f"{bold(t(lang, 'id_label'))} {code(str(act.get('id','-')))}",
        f"{bold(t(lang, 'nomor'))} {code(str(act.get('phone','-')))}",
        f"{bold(t(lang, 'kode_negara'))} {code(str(act.get('phoneCode', act.get('countryPhoneCode','-'))))}",
        f"{bold(t(lang, 'layanan'))} {esc(str(act.get('serviceName', act.get('service','-'))))}",
        f"{bold(t(lang, 'negara'))} {esc(str(act.get('countryName', act.get('country','-'))))}",
        f"{bold(t(lang, 'biaya'))} {cost_line}",
    ]
    exp = act.get("expiredAt")
    if exp and str(exp) not in ("-", ""):
        lines.append(f"{bold(t(lang, 'kedaluwarsa'))} {code(_fmt_dt(exp))}")
        bar = _remaining_bar(act, lang)
        if bar:
            lines.append(bar)
    lines.append(f"\n👉 {esc(t(lang, 'sukses_hint'))}")
    return "\n".join(lines) + "\n"


def welcome_msg(lang: str = "id") -> str:
    return (
        f"{header(t(lang, 'welcome_judul'), t(lang, 'welcome_sub'))}\n"
        f"{esc(t(lang, 'welcome_body'))}\n"
        f"• {esc(t(lang, 'welcome_1'))}\n"
        f"• {esc(t(lang, 'welcome_2'))}\n"
        f"• {esc(t(lang, 'welcome_3'))}\n"
        f"• {esc(t(lang, 'welcome_4'))}\n"
        f"• {esc(t(lang, 'welcome_5'))}\n"
        f"\n{esc(t(lang, 'welcome_cta'))}\n"
    )


def confirm_msg(action_label: str, detail: str, lang: str = "id") -> str:
    return (
        f"{header(t(lang, 'konfirmasi_judul'), t(lang, 'konfirmasi_sub'))}\n"
        f"{bold(t(lang, 'aksi'))} {esc(action_label)}\n"
        f"{bold(t(lang, 'detail_lbl'))} {esc(detail)}\n\n"
        f"{t(lang, 'lanjutkan')}"
    )


def error_msg(title: str, detail: str, lang: str = "id") -> str:
    return f"{header('❌ ' + esc(title), '')}\n{esc(detail)}\n"


def success_msg(title: str, detail: str, lang: str = "id") -> str:
    return f"{header('✅ ' + esc(title), '')}\n{esc(detail)}\n"


def buy_confirm_msg(country: str, service: str, price: str, currency: str = "", duration: str = "-", price_str: str = "", lang: str = "id") -> str:
    p_line = price_str or f"{code(str(price))} {code(str(currency))}"
    return (
        f"{header(t(lang, 'konfirmasi_beli_judul'), t(lang, 'konfirmasi_beli_sub'))}\n"
        f"{bold(t(lang, 'negara'))} {esc(str(country))}\n"
        f"{bold(t(lang, 'layanan'))} {esc(str(service))}\n"
        f"{bold(t(lang, 'harga'))} {p_line}\n"
        f"{bold(t(lang, 'durasi'))} {esc(str(duration))}\n"
        f"{bold(t(lang, 'nomor').rstrip(':'))} {t(lang, 'nomor_setelah_beli').split(': ', 1)[1]}\n\n"
        f"{t(lang, 'lanjutkan_beli')}"
    )
