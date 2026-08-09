"""Türkçe tarih ifadesi ayrıştırıcı — kural tabanlı, yalnız stdlib.

"haziran ayı", "son 1 sene", "bu hafta", "1 haziran - 15 temmuz",
"01.06.2026" gibi ifadeleri (start, end) tarih aralığına çevirir.

ÖNEMLİ: Bu modül HAM mesaj üzerinde çalışmalıdır. intent_matcher.normalize()
noktalama işaretlerini (`.` `/` `-`) sildiği için "01.06.2026" gibi ifadeleri
bozar; buradaki _norm() yalnız Türkçe'ye duyarlı küçük harfe çevirir ve
karakter sayısını korur (dönen span'lar ham metinde de geçerlidir).

Hızlı regresyon testi:  python -m backend.chatbot.date_parser
"""

import re
from calendar import monthrange
from datetime import date, timedelta

_TR_LOWER = str.maketrans("IİÇĞÖŞÜ", "ıiçğöşü")


def _norm(text: str) -> str:
    """Uzunluğu koruyan Türkçe küçük harf dönüşümü (noktalama silinmez)."""
    return text.translate(_TR_LOWER).lower()


AY_ADLARI = {
    "ocak": 1, "şubat": 2, "subat": 2, "mart": 3, "nisan": 4,
    "mayıs": 5, "mayis": 5, "haziran": 6, "temmuz": 7,
    "ağustos": 8, "agustos": 8, "eylül": 9, "eylul": 9, "ekim": 10,
    "kasım": 11, "kasim": 11, "aralık": 12, "aralik": 12,
}
AY_ETIKET = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
             "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]

SAYI_SOZLERI = {"bir": 1, "iki": 2, "üç": 3, "uc": 3, "dört": 4, "dort": 4,
                "beş": 5, "bes": 5, "altı": 6, "alti": 6, "yedi": 7,
                "sekiz": 8, "dokuz": 9, "on": 10}

_AY_RX = "|".join(AY_ADLARI)
_SAYI_RX = r"\d+|" + "|".join(SAYI_SOZLERI)
_EK = r"[a-zçğıöşü']*"  # Türkçe ek toleransı: "haziranda", "martın", "ayının"

# Tek taraflı tarih "atomları" (aralığın iki yanında da kullanılır)
_ATOM_RX = (
    r"(?:\d{4}-\d{1,2}-\d{1,2}"          # ISO: 2026-06-01
    r"|\d{1,2}[./]\d{1,2}[./]\d{4}"      # 01.06.2026, 1/6/2026
    r"|\d{1,2}[./]\d{1,2}(?![./]?\d)"    # 01.06
    rf"|\d{{1,2}}\s+(?:{_AY_RX}){_EK}(?:\s+\d{{4}})?"  # 1 haziran [2026]
    rf"|(?:{_AY_RX}){_EK}(?:\s+\d{{4}})?"              # haziran [2026]
    r"|20\d{2})"                          # 2022
)

_RE_ISO = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$")
_RE_TAM = re.compile(r"^(\d{1,2})[./](\d{1,2})[./](\d{4})$")
_RE_KISA = re.compile(r"^(\d{1,2})[./](\d{1,2})$")
_RE_GUN_AY = re.compile(rf"^(\d{{1,2}})\s+({_AY_RX}){_EK}(?:\s+(\d{{4}}))?$")
_RE_AY = re.compile(rf"^({_AY_RX}){_EK}(?:\s+(\d{{4}}))?$")
_RE_YIL = re.compile(r"^(20\d{2})(?:\s+(?:yılı|yili|senesi))?$")


def _shift_months(d: date, n: int) -> date:
    ay = d.month - 1 + n
    yil = d.year + ay // 12
    ay = ay % 12 + 1
    return date(yil, ay, min(d.day, monthrange(yil, ay)[1]))


def _ay_araligi(yil: int, ay: int) -> tuple[date, date]:
    return date(yil, ay, 1), date(yil, ay, monthrange(yil, ay)[1])


def _fmt(d: date) -> str:
    return d.strftime("%d.%m.%Y")


def _parse_atom(parca: str, today: date):
    """Tek bir tarih parçasını (start, end, label) olarak çözer; olmadıysa None."""
    parca = parca.strip()

    m = _RE_ISO.match(parca) or _RE_TAM.match(parca)
    if m:
        a, b, c = (int(g) for g in m.groups())
        yil, ay, gun = (a, b, c) if _RE_ISO.match(parca) else (c, b, a)
        try:
            d = date(yil, ay, gun)
        except ValueError:
            return None
        return d, d, _fmt(d)

    m = _RE_KISA.match(parca)
    if m:
        gun, ay = int(m.group(1)), int(m.group(2))
        try:
            d = date(today.year, ay, gun)
        except ValueError:
            return None
        if d > today:
            d = d.replace(year=today.year - 1)
        return d, d, _fmt(d)

    m = _RE_GUN_AY.match(parca)
    if m:
        gun = int(m.group(1))
        ay = AY_ADLARI[m.group(2)]
        yil = int(m.group(3)) if m.group(3) else today.year
        try:
            d = date(yil, ay, gun)
        except ValueError:
            return None
        # Yıl verilmediyse ve tarih gelecekteyse geçen yıl kastedilmiştir
        if not m.group(3) and d > today:
            d = d.replace(year=yil - 1)
        return d, d, _fmt(d)

    m = _RE_AY.match(parca)
    if m:
        ay = AY_ADLARI[m.group(1)]
        if m.group(2):
            yil = int(m.group(2))
        else:
            yil = today.year
            # Ay bu yıl henüz başlamadıysa geçen yılki kastedilmiştir
            if date(yil, ay, 1) > today:
                yil -= 1
        start, end = _ay_araligi(yil, ay)
        return start, end, f"{AY_ETIKET[ay - 1]} {yil}"

    m = _RE_YIL.match(parca)
    if m:
        yil = int(m.group(1))
        if not 2015 <= yil <= today.year + 1:
            return None
        return date(yil, 1, 1), date(yil, 12, 31), f"{yil} Yılı"

    return None


def _sayi(s: str) -> int:
    return int(s) if s.isdigit() else SAYI_SOZLERI[s]


# --- Desenler (öncelik sırasıyla denenir; ilk eşleşen kazanır) ---------------

def _h_aralik(m, today):
    sol = _parse_atom(m.group("sol"), today)
    sag = _parse_atom(m.group("sag"), today)
    if sol is None or sag is None:
        return None
    start, end = sol[0], sag[1]
    return start, end, f"{_fmt(start)} – {_fmt(end)}"


def _h_atom(m, today):
    return _parse_atom(m.group(0), today)


def _h_bugun(m, today):
    return today, today, "Bugün"


def _h_dun(m, today):
    d = today - timedelta(days=1)
    return d, d, "Dün"


def _h_bu_hafta(m, today):
    return today - timedelta(days=today.weekday()), today, "Bu Hafta"


def _h_gecen_hafta(m, today):
    pazartesi = today - timedelta(days=today.weekday() + 7)
    return pazartesi, pazartesi + timedelta(days=6), "Geçen Hafta"


def _h_bu_ay(m, today):
    return today.replace(day=1), today, "Bu Ay"


def _h_gecen_ay(m, today):
    onceki = today.replace(day=1) - timedelta(days=1)
    start, end = _ay_araligi(onceki.year, onceki.month)
    return start, end, f"Geçen Ay ({AY_ETIKET[onceki.month - 1]} {onceki.year})"


def _h_bu_yil(m, today):
    return today.replace(month=1, day=1), today, "Bu Yıl"


def _h_gecen_yil(m, today):
    yil = today.year - 1
    return date(yil, 1, 1), date(yil, 12, 31), f"Geçen Yıl ({yil})"


def _h_son_n(m, today):
    n = _sayi(m.group(1))
    birim = m.group(2)
    if birim.startswith(("gün", "gun")):
        start = today - timedelta(days=n - 1)
        etiket = f"Son {n} Gün"
    elif birim.startswith("hafta"):
        start = today - timedelta(days=n * 7 - 1)
        etiket = f"Son {n} Hafta"
    elif birim.startswith("ay"):
        start = _shift_months(today, -n)
        etiket = f"Son {n} Ay"
    else:  # yıl / sene
        start = _shift_months(today, -12 * n)
        etiket = f"Son {n} Yıl"
    return start, today, etiket


_PATTERNS = [
    # Açık aralık: "1 haziran - 15 temmuz", "01.06.2026 ile 30.06.2026 arası"
    (re.compile(rf"(?P<sol>{_ATOM_RX})\s*(?:-|–|—|\bile\b)\s*(?P<sag>{_ATOM_RX})"
                rf"(?:\s+aras{_EK})?"), _h_aralik),
    # Göreli ifadeler
    (re.compile(rf"\bson\s+({_SAYI_RX})\s+(gün|gun|hafta|ay|yıl|yil|sene){_EK}"),
     _h_son_n),
    (re.compile(r"\bbugün\w*|\bbugun\w*"), _h_bugun),
    (re.compile(r"\bdün\b|\bdünkü\b|\bdunku\b"), _h_dun),
    (re.compile(rf"\bbu\s+hafta{_EK}"), _h_bu_hafta),
    (re.compile(rf"\b(?:geçen|gecen|önceki|onceki)\s+hafta{_EK}"), _h_gecen_hafta),
    (re.compile(rf"\bbu\s+ay{_EK}"), _h_bu_ay),
    (re.compile(rf"\b(?:geçen|gecen|önceki|onceki)\s+ay{_EK}"), _h_gecen_ay),
    (re.compile(rf"\bbu\s+(?:yıl|yil|sene){_EK}"), _h_bu_yil),
    (re.compile(rf"\b(?:geçen|gecen|önceki|onceki)\s+(?:yıl|yil|sene){_EK}"),
     _h_gecen_yil),
    # Tekil atomlar: tam tarih, gün+ay, ay adı ("haziran ayı" dahil), yıl
    (re.compile(rf"\b\d{{4}}-\d{{1,2}}-\d{{1,2}}\b"), _h_atom),
    (re.compile(r"\b\d{1,2}[./]\d{1,2}[./]\d{4}\b"), _h_atom),
    (re.compile(r"\b\d{1,2}[./]\d{1,2}\b(?![./]?\d)"), _h_atom),
    (re.compile(rf"\b\d{{1,2}}\s+(?:{_AY_RX}){_EK}(?:\s+\d{{4}})?"), _h_atom),
    (re.compile(rf"\b(?:{_AY_RX}){_EK}(?:\s+\d{{4}})?"), _h_atom),
    (re.compile(r"\b20\d{2}\b(?:\s+(?:yılı|yili|senesi))?"), _h_atom),
]

# "haziran ayı(nın/na...)" kalıbında ay kelimesini de tüket
_AY_SONEK = re.compile(rf"^\s+ay{_EK}")


def parse_date_expression(text: str, today: date | None = None):
    """Metindeki ilk tarih ifadesini çözer.

    Dönüş: ({"start": date, "end": date, "label": str}, [(bas, son)]) ya da None.
    span'lar ham metindeki karakter aralıklarıdır (normalizasyon uzunluk korur).
    """
    today = today or date.today()
    metin = _norm(text)

    for desen, handler in _PATTERNS:
        m = desen.search(metin)
        if m is None:
            continue
        sonuc = handler(m, today)
        if sonuc is None:
            continue  # örn. geçersiz gün/ay değerleri: sıradaki deseni dene
        start, end, etiket = sonuc
        if start > end:
            start, end = end, start
        end = min(end, today)
        start = min(start, end)

        bas, son = m.span()
        ek = _AY_SONEK.match(metin[son:])
        if ek:
            son += ek.end()
        return {"start": start, "end": end, "label": etiket}, [(bas, son)]

    return None


# --- Öz-test -----------------------------------------------------------------

if __name__ == "__main__":
    BUGUN = date(2026, 8, 5)  # Çarşamba

    def d(y, m, g):
        return date(y, m, g)

    VAKALAR = [
        ("haziran ayı", d(2026, 6, 1), d(2026, 6, 30)),
        ("haziran ayı raporlarını istiyorum", d(2026, 6, 1), d(2026, 6, 30)),
        ("Haziran raporları", d(2026, 6, 1), d(2026, 6, 30)),
        ("haziranda ne kadar gelir oldu", d(2026, 6, 1), d(2026, 6, 30)),
        ("aralık", d(2025, 12, 1), d(2025, 12, 31)),
        ("haziran 2025", d(2025, 6, 1), d(2025, 6, 30)),
        ("son 1 sene", d(2025, 8, 5), d(2026, 8, 5)),
        ("son 1 senelik raporlar", d(2025, 8, 5), d(2026, 8, 5)),
        ("son bir yıl", d(2025, 8, 5), d(2026, 8, 5)),
        ("son 3 ay", d(2026, 5, 5), d(2026, 8, 5)),
        ("son 30 gün", d(2026, 7, 7), d(2026, 8, 5)),
        ("son 2 hafta", d(2026, 7, 23), d(2026, 8, 5)),
        ("bu hafta", d(2026, 8, 3), d(2026, 8, 5)),
        ("geçen hafta", d(2026, 7, 27), d(2026, 8, 2)),
        ("bu ay", d(2026, 8, 1), d(2026, 8, 5)),
        ("geçen ay", d(2026, 7, 1), d(2026, 7, 31)),
        ("gecen ayin verileri", d(2026, 7, 1), d(2026, 7, 31)),
        ("bu yıl", d(2026, 1, 1), d(2026, 8, 5)),
        ("geçen sene", d(2025, 1, 1), d(2025, 12, 31)),
        ("bugün", d(2026, 8, 5), d(2026, 8, 5)),
        ("dün", d(2026, 8, 4), d(2026, 8, 4)),
        ("01.06.2026", d(2026, 6, 1), d(2026, 6, 1)),
        ("1/6/2026", d(2026, 6, 1), d(2026, 6, 1)),
        ("2026-06-01", d(2026, 6, 1), d(2026, 6, 1)),
        ("01.06.2026 - 30.06.2026", d(2026, 6, 1), d(2026, 6, 30)),
        ("1 haziran - 15 temmuz", d(2026, 6, 1), d(2026, 7, 15)),
        ("1 haziran ile 15 temmuz arası", d(2026, 6, 1), d(2026, 7, 15)),
        ("ocak - mart", d(2026, 1, 1), d(2026, 3, 31)),
        ("1 haziran", d(2026, 6, 1), d(2026, 6, 1)),
        ("15 temmuz 2025", d(2025, 7, 15), d(2025, 7, 15)),
        ("2025 yılı", d(2025, 1, 1), d(2025, 12, 31)),
        ("2026 yılı kayıtları", d(2026, 1, 1), d(2026, 8, 5)),  # bugüne kıskaçlanır
    ]
    YOKLAR = ["merhaba", "bayilerin hakedişini görmek istiyorum",
              "kart işlemleri", "yolcu istatistikleri", "teşekkürler"]

    hata = 0
    for metin, start, end in VAKALAR:
        sonuc = parse_date_expression(metin, today=BUGUN)
        if sonuc is None:
            print(f"HATA: {metin!r} -> None (beklenen {start}..{end})")
            hata += 1
            continue
        aralik = sonuc[0]
        if (aralik["start"], aralik["end"]) != (start, end):
            print(f"HATA: {metin!r} -> {aralik['start']}..{aralik['end']} "
                  f"(beklenen {start}..{end})")
            hata += 1
    for metin in YOKLAR:
        sonuc = parse_date_expression(metin, today=BUGUN)
        if sonuc is not None:
            print(f"HATA: {metin!r} tarih içermemeli, bulundu: {sonuc[0]}")
            hata += 1

    toplam = len(VAKALAR) + len(YOKLAR)
    print(f"{toplam - hata}/{toplam} vaka geçti" + (" — SORUN VAR" if hata else ""))
