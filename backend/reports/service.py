"""Rapor kurucuları: filtreleme, toplama, stat kartları ve Türkçe formatlama.

Satır değerleri sunucuda formatlanmış string olarak döner; frontend renderer'ı
(report-page.js) yalnızca çizer. `locale` modülü bilinçli olarak kullanılmıyor
(Windows'ta Türkçe locale güvenilmez) — formatlama el yazması yardımcılarla.
"""

from datetime import date, timedelta
from random import Random

from backend.reports import mock_data
from backend.reports.registry import REPORTS

KART_SATIR_LIMITI = 100

AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
         "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]


# --- Formatlama yardımcıları -------------------------------------------------

def fmt_int(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def fmt_tl(n: int) -> str:
    return "₺" + fmt_int(round(n))


def fmt_tl_kurus(n: float) -> str:
    lira = int(n)
    kurus = round((n - lira) * 100)
    return f"₺{fmt_int(lira)},{kurus:02d}"


def fmt_compact(n: float, birim: str = "") -> str:
    """Büyük sayılar için '13,5 Mn' biçimi; küçükler nokta ayraçlı tam sayı."""
    if abs(n) >= 1_000_000:
        return f"{birim}{n / 1_000_000:.1f}".replace(".", ",") + " Mn"
    return birim + fmt_int(round(n))


def fmt_pct_signed(oran: float) -> str:
    """+%10,4 / -%2,3 biçimi (oran: 0.104 → +%10,4)."""
    isaret = "+" if oran >= 0 else "-"
    return f"{isaret}%{abs(oran) * 100:.1f}".replace(".", ",")


def fmt_date(d: date) -> str:
    return d.strftime("%d.%m.%Y")


def period_label(start: date | None, end: date | None) -> str:
    if start is None or end is None:
        return "Tüm kayıtlar"
    if start == end:
        return fmt_date(start)
    return f"{fmt_date(start)} – {fmt_date(end)}"


# --- Dönem çözümleme ---------------------------------------------------------

def default_range(report_id: str, bugun: date) -> tuple[date | None, date | None]:
    """Raporun varsayılan dönemini (start, end) olarak çözer."""
    donem = REPORTS[report_id]["default_period"]
    if donem is None:
        return None, None
    if donem == "bu ay":
        return bugun.replace(day=1), bugun
    if donem == "bu yıl":
        return bugun.replace(month=1, day=1), bugun
    if donem == "son 30 gün":
        return bugun - timedelta(days=29), bugun
    if donem == "son 7 gün":
        return bugun - timedelta(days=6), bugun
    raise ValueError(f"Bilinmeyen varsayılan dönem: {donem}")


def _clamp(start: date, end: date, bugun: date) -> tuple[date, date]:
    """Aralığı veri ufkuna kıskaçlar; ters aralığı sessizce takas eder."""
    if start > end:
        start, end = end, start
    start = max(start, mock_data.data_start(bugun))
    end = min(end, bugun)
    return start, end


def _days(start: date, end: date):
    gun = start
    while gun <= end:
        yield gun
        gun += timedelta(days=1)


def _months(start: date, end: date):
    """Aralıkla kesişen ayları (ay_başı, ay_sonu_kıskaçlı) olarak verir."""
    yil, ay = start.year, start.month
    while (yil, ay) <= (end.year, end.month):
        ay_bas = date(yil, ay, 1)
        sonraki = date(yil + (ay == 12), ay % 12 + 1, 1)
        ay_son = sonraki - timedelta(days=1)
        yield max(ay_bas, start), min(ay_son, end), ay_son
        yil, ay = sonraki.year, sonraki.month


# --- Ana giriş ---------------------------------------------------------------

def get_report(report_id: str, start: date | None, end: date | None,
               enum_filters: dict, limit: int = KART_SATIR_LIMITI,
               bugun: date | None = None) -> dict:
    bugun = bugun or date.today()
    if start is None or end is None:
        start, end = default_range(report_id, bugun)
    if start is not None:
        start, end = _clamp(start, end, bugun)

    meta = REPORTS[report_id]
    builder = _BUILDERS[report_id]
    govde = builder(start, end, enum_filters, limit, bugun)

    return {
        "report_id": report_id,
        "title": meta["title"],
        "subtitle": meta["subtitle"],
        "period": {
            "start": start.isoformat() if start else None,
            "end": end.isoformat() if end else None,
            "label": period_label(start, end),
        },
        "applied_filters": enum_filters,
        "available_filters": {
            anahtar: {"label": f["label"], "values": f["values"]}
            for anahtar, f in meta["enum_filters"].items()
        },
        **govde,
    }


# --- Rapor kurucuları --------------------------------------------------------

def _build_gelir(start, end, _filtreler, _limit, bugun):
    aylar = []
    for ay_bas, ay_son, gercek_ay_sonu in _months(start, end):
        toplamlar = {"otobus": 0, "metro": 0, "tramvay": 0}
        for gun in _days(ay_bas, ay_son):
            g = mock_data.daily_gelir(gun)
            for k in toplamlar:
                toplamlar[k] += g[k]
        etiket = f"{AYLAR[ay_bas.month - 1]} {ay_bas.year}"
        # Baştan ya da sondan kesilen ay "kısmi"dir; değişim yüzdesine girmez
        kismi = ay_bas.day != 1 or ay_son < gercek_ay_sonu
        if kismi:
            etiket += " (devam)" if ay_son == bugun else " (kısmi)"
        aylar.append({"etiket": etiket, "kismi": kismi, **toplamlar,
                      "toplam": sum(toplamlar.values())})

    rows = []
    onceki_tam = None  # değişim yalnız tam aylar arasında anlamlı
    for ay in aylar:
        if ay["kismi"] or onceki_tam is None:
            degisim = "—"
        else:
            degisim = fmt_pct_signed(ay["toplam"] / onceki_tam - 1)
        rows.append({
            "ay": ay["etiket"],
            "otobus": fmt_tl(ay["otobus"]),
            "metro": fmt_tl(ay["metro"]),
            "tramvay": fmt_tl(ay["tramvay"]),
            "toplam": fmt_tl(ay["toplam"]),
            "degisim": degisim,
        })
        if not ay["kismi"]:
            onceki_tam = ay["toplam"]

    toplam_gelir = sum(a["toplam"] for a in aylar)
    en_yuksek = max(aylar, key=lambda a: a["toplam"]) if aylar else None
    tam_aylar = [a for a in aylar if not a["kismi"]]
    if len(tam_aylar) >= 2:
        buyume = fmt_pct_signed(tam_aylar[-1]["toplam"] / tam_aylar[0]["toplam"] - 1)
    else:
        buyume = "—"
    return {
        "stats": [
            {"label": "Toplam Gelir", "value": fmt_compact(toplam_gelir, "₺")},
            {"label": "Aylık Ortalama",
             "value": fmt_compact(toplam_gelir / len(aylar), "₺") if aylar else "—"},
            {"label": "En Yüksek Ay",
             "value": en_yuksek["etiket"].split(" ")[0] if en_yuksek else "—"},
            {"label": "Dönem Değişimi", "value": buyume},
        ],
        "columns": [
            {"key": "ay", "label": "Ay"},
            {"key": "otobus", "label": "Otobüs", "num": True},
            {"key": "metro", "label": "Metro", "num": True},
            {"key": "tramvay", "label": "Tramvay", "num": True},
            {"key": "toplam", "label": "Toplam Gelir", "num": True},
            {"key": "degisim", "label": "Değişim", "num": True},
        ],
        "rows": rows,
        "total_rows": len(rows),
    }


def _build_dolum_hakedis(start, end, filtreler, _limit, _bugun):
    satirlar = []
    for bayi in mock_data.bayiler():
        if filtreler.get("bolge") and bayi["bolge"] != filtreler["bolge"]:
            continue
        dolum = sum(mock_data.daily_dolum(bayi["kod"], g) for g in _days(start, end))
        if dolum == 0:
            continue  # pasif / dolumu olmayan bayi hakediş listesine girmez
        # Hakediş ödeme durumu döneme göre deterministik
        rng = Random(f"hakedis:{bayi['kod']}:{start}:{end}")
        durum = "Ödendi" if rng.random() < 0.7 else "Bekliyor"
        if filtreler.get("durum") and durum != filtreler["durum"]:
            continue
        komisyon = round(dolum * 0.03)
        satirlar.append({"bayi": bayi, "dolum": dolum, "komisyon": komisyon,
                         "hakedis": dolum - komisyon, "durum": durum})
    satirlar.sort(key=lambda s: s["dolum"], reverse=True)

    rows = [{
        "bayi_kodu": s["bayi"]["kod"],
        "bayi_adi": s["bayi"]["ad"],
        "bolge": s["bayi"]["bolge"],
        "dolum": fmt_tl(s["dolum"]),
        "komisyon": fmt_tl(s["komisyon"]),
        "hakedis": fmt_tl(s["hakedis"]),
        "durum": s["durum"],
    } for s in satirlar]

    return {
        "stats": [
            {"label": "Toplam Dolum",
             "value": fmt_compact(sum(s["dolum"] for s in satirlar), "₺")},
            {"label": "Toplam Komisyon",
             "value": fmt_compact(sum(s["komisyon"] for s in satirlar), "₺")},
            {"label": "Ödenecek Hakediş",
             "value": fmt_compact(sum(s["hakedis"] for s in satirlar
                                      if s["durum"] == "Bekliyor"), "₺")},
            {"label": "Bayi Sayısı", "value": str(len(satirlar))},
        ],
        "columns": [
            {"key": "bayi_kodu", "label": "Bayi Kodu"},
            {"key": "bayi_adi", "label": "Bayi Adı"},
            {"key": "bolge", "label": "Bölge"},
            {"key": "dolum", "label": "Dolum Tutarı", "num": True},
            {"key": "komisyon", "label": "Komisyon (%3)", "num": True},
            {"key": "hakedis", "label": "Hakediş", "num": True},
            {"key": "durum", "label": "Durum", "badge": True},
        ],
        "rows": rows,
        "total_rows": len(rows),
    }


def _build_yolcu(start, end, filtreler, _limit, _bugun):
    gunler = list(_days(start, end))
    hafta_sonlari = [g for g in gunler if g.weekday() >= 5]
    satirlar = []
    for hat_no, guzergah, mod, baz, _hs_orani, baz_doluluk in mock_data.HATLAR:
        if filtreler.get("mod") and mod != filtreler["mod"]:
            continue
        binisler = {g: mock_data.daily_binis(hat_no, g) for g in gunler}
        toplam = sum(binisler.values())
        ort = toplam / len(gunler)
        hs_ort = (sum(binisler[g] for g in hafta_sonlari) / len(hafta_sonlari)
                  if hafta_sonlari else None)
        doluluk = min(99, max(35, round(baz_doluluk * ort / baz)))
        satirlar.append({"hat_no": hat_no, "guzergah": guzergah, "mod": mod,
                         "ort": ort, "hs_ort": hs_ort, "toplam": toplam,
                         "doluluk": doluluk})
    satirlar.sort(key=lambda s: s["ort"], reverse=True)

    rows = [{
        "hat_no": s["hat_no"],
        "guzergah": s["guzergah"],
        "mod": s["mod"],
        "gunluk_ort": fmt_int(round(s["ort"])),
        "hafta_sonu_ort": fmt_int(round(s["hs_ort"])) if s["hs_ort"] is not None else "—",
        "doluluk": f"%{s['doluluk']}",
    } for s in satirlar]

    return {
        "stats": [
            {"label": "Günlük Ortalama Biniş",
             "value": fmt_int(round(sum(s["ort"] for s in satirlar)))},
            {"label": "Toplam Biniş",
             "value": fmt_compact(sum(s["toplam"] for s in satirlar))},
            {"label": "En Yoğun Hat",
             "value": (f"{satirlar[0]['hat_no']} {satirlar[0]['mod']}"
                       if satirlar else "—")},
            {"label": "En Yoğun Saat", "value": "08:00–09:00"},
        ],
        "columns": [
            {"key": "hat_no", "label": "Hat No"},
            {"key": "guzergah", "label": "Güzergah"},
            {"key": "mod", "label": "Mod"},
            {"key": "gunluk_ort", "label": "Günlük Ort. Biniş", "num": True},
            {"key": "hafta_sonu_ort", "label": "Hafta Sonu Ort.", "num": True},
            {"key": "doluluk", "label": "Doluluk", "num": True},
        ],
        "rows": rows,
        "total_rows": len(rows),
    }


def _build_kart(start, end, filtreler, limit, _bugun):
    tip_filtre = filtreler.get("islem_tipi")
    rows, toplam_islem = [], 0
    dolum_toplam, dolum_adet = 0, 0
    gun = end
    while gun >= start:
        for islem in mock_data.kart_transactions(gun):
            if tip_filtre and islem["islem_tipi"] != tip_filtre:
                continue
            toplam_islem += 1
            if islem["islem_tipi"] == "Dolum":
                dolum_toplam += islem["tutar"]
                dolum_adet += 1
            if len(rows) < limit:
                gosterim_tipi = ("Biniş (İndirimli)"
                                 if islem["islem_tipi"] == "İndirimli"
                                 else islem["islem_tipi"])
                rows.append({
                    "islem_no": islem["islem_no"],
                    "kart_no": islem["kart_no"],
                    "islem_tipi": gosterim_tipi,
                    "nokta": islem["nokta"],
                    "tutar": fmt_tl_kurus(islem["tutar"]),
                    "tarih": fmt_date(islem["tarih"]),
                    "saat": islem["saat"],
                })
        gun -= timedelta(days=1)

    return {
        "stats": [
            {"label": "Toplam İşlem", "value": fmt_int(toplam_islem)},
            {"label": "Toplam Dolum", "value": fmt_compact(dolum_toplam, "₺")},
            {"label": "Aktif Kart", "value": "2,4 Mn"},
            {"label": "Ortalama Dolum",
             "value": fmt_tl(dolum_toplam / dolum_adet) if dolum_adet else "—"},
        ],
        "columns": [
            {"key": "islem_no", "label": "İşlem No"},
            {"key": "kart_no", "label": "Kart No"},
            {"key": "islem_tipi", "label": "İşlem Tipi"},
            {"key": "nokta", "label": "Nokta / Hat"},
            {"key": "tutar", "label": "Tutar", "num": True},
            {"key": "tarih", "label": "Tarih"},
            {"key": "saat", "label": "Saat"},
        ],
        "rows": rows,
        "total_rows": toplam_islem,
    }


def _build_bayi(start, end, filtreler, _limit, _bugun):
    satirlar = []
    for bayi in mock_data.bayiler():
        if start is not None and not (start <= bayi["kayit_tarihi"] <= end):
            continue
        if filtreler.get("bolge") and bayi["bolge"] != filtreler["bolge"]:
            continue
        if filtreler.get("durum") and bayi["durum"] != filtreler["durum"]:
            continue
        satirlar.append(bayi)
    satirlar.sort(key=lambda b: b["kod"])

    rows = [{
        "bayi_kodu": b["kod"],
        "bayi_adi": b["ad"],
        "bolge": b["bolge"],
        "yetkili": b["yetkili"],
        "telefon": b["telefon"],
        "kayit_tarihi": fmt_date(b["kayit_tarihi"]),
        "durum": b["durum"],
    } for b in satirlar]

    return {
        "stats": [
            {"label": "Toplam Bayi", "value": str(len(satirlar))},
            {"label": "Aktif",
             "value": str(sum(1 for b in satirlar if b["durum"] == "Aktif"))},
            {"label": "Pasif",
             "value": str(sum(1 for b in satirlar if b["durum"] == "Pasif"))},
            {"label": "Bölge Sayısı",
             "value": str(len({b["bolge"] for b in satirlar}))},
        ],
        "columns": [
            {"key": "bayi_kodu", "label": "Bayi Kodu"},
            {"key": "bayi_adi", "label": "Bayi Adı"},
            {"key": "bolge", "label": "Bölge"},
            {"key": "yetkili", "label": "Yetkili"},
            {"key": "telefon", "label": "Telefon"},
            {"key": "kayit_tarihi", "label": "Kayıt Tarihi"},
            {"key": "durum", "label": "Durum", "badge": True},
        ],
        "rows": rows,
        "total_rows": len(rows),
    }


_BUILDERS = {
    "gelir-raporlari": _build_gelir,
    "dolum-hakedis": _build_dolum_hakedis,
    "yolcu-istatistikleri": _build_yolcu,
    "kart-islemleri": _build_kart,
    "bayi-yonetimi": _build_bayi,
}
