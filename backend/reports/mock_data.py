"""Deterministik mock veri üreticileri.

Determinizm kuralı: her rastgele çekiliş, string seed'li ayrı bir
``random.Random`` örneğinden yapılır (string seed'ler sha512 ile sayıya
çevrildiğinden çalıştırmalar ve makineler arasında kararlıdır). Gün bazlı
değerlerin seed'i ISO tarihten türetilir; böylece aynı takvim günü her
sorguda aynı değeri üretir, "bugün" ilerledikçe yeni günler eklenir.
"""

from datetime import date, timedelta
from functools import lru_cache
from random import Random

from backend.reports.registry import BOLGELER

# Veri ufku: bugünden bu kadar ay geriye veri üretilir
DATA_MONTHS = 13

# --- Sabit varlık havuzları -------------------------------------------------

# Anadolu yakası bölgeleri 0216, Avrupa yakası 0212 ile başlar
_ANADOLU = {"Kadıköy", "Üsküdar", "Maltepe", "Pendik"}

# v1 sayfalarındaki 9 bayi aynen korunur (kod, ad, bölge, yetkili, telefon,
# kayıt tarihi, durum) — sayfalar tanıdık görünsün diye
_SEED_BAYILER = [
    ("BY-1001", "Merkez Büfe", "Kadıköy", "A. Yılmaz", "0216 555 01 01", date(2021, 3, 12), "Aktif"),
    ("BY-1002", "Gar Market", "Üsküdar", "M. Demir", "0216 555 01 02", date(2021, 6, 25), "Aktif"),
    ("BY-1003", "Durak Tekel", "Beşiktaş", "H. Kaya", "0212 555 01 03", date(2021, 9, 8), "Aktif"),
    ("BY-1004", "Sahil Büfe", "Maltepe", "S. Çelik", "0216 555 01 04", date(2022, 1, 17), "Aktif"),
    ("BY-1005", "Meydan Kırtasiye", "Fatih", "E. Şahin", "0212 555 01 05", date(2022, 4, 3), "Aktif"),
    ("BY-1006", "Terminal Şarküteri", "Bakırköy", "K. Arslan", "0212 555 01 06", date(2022, 7, 21), "Pasif"),
    ("BY-1007", "Kampüs Kafe", "Sarıyer", "D. Koç", "0212 555 01 07", date(2022, 11, 14), "Aktif"),
    ("BY-1008", "Çarşı Büfe", "Pendik", "B. Aydın", "0216 555 01 08", date(2023, 2, 2), "Aktif"),
    ("BY-1009", "İskele Büfe", "Eminönü", "C. Öztürk", "0212 555 01 09", date(2023, 5, 19), "Pasif"),
]

_AD_ON = ["Yeni", "Park", "Liman", "Köprü", "Vadi", "Cadde", "Kule", "Pazar",
          "Okul", "Hastane", "Stadyum", "Rıhtım", "Tünel", "Kavşak", "Site"]
_AD_SON = ["Büfe", "Market", "Tekel", "Kafe", "Şarküteri", "Kırtasiye", "Gazete Bayii"]
_SOYADLAR = ["Yılmaz", "Demir", "Kaya", "Çelik", "Şahin", "Arslan", "Koç", "Aydın",
             "Öztürk", "Polat", "Güneş", "Kurt", "Özdemir", "Aksoy", "Doğan", "Erdem"]
_ADBAS = "ABCDEFGHKLMNOPRSTUYZ"

# Toplam 52 bayi, 48 aktif / 4 pasif (v1 stat kartlarıyla uyumlu):
# ilk 9'da 2 pasif var, üretilenlerden bu ikisi de pasif yapılır
_URETILEN_PASIF = {"BY-1023", "BY-1041"}


def _uretilmis_bayi(idx: int) -> dict:
    """BY-1010..BY-1052 arası bayileri deterministik üretir (idx: 9..51)."""
    kod = f"BY-{1001 + idx}"
    rng = Random(f"bayi:{kod}")
    bolge = BOLGELER[idx % len(BOLGELER)]
    ad = f"{rng.choice(_AD_ON)} {rng.choice(_AD_SON)}"
    yetkili = f"{rng.choice(_ADBAS)}. {rng.choice(_SOYADLAR)}"
    alan = "0216" if bolge in _ANADOLU else "0212"
    telefon = f"{alan} 555 {(1001 + idx) // 100:02d} {(1001 + idx) % 100:02d}"
    # Kayıt tarihi 2021-2025 arasına yayılır
    kayit = date(2021, 1, 1) + timedelta(days=rng.randrange(0, 365 * 5))
    durum = "Pasif" if kod in _URETILEN_PASIF else "Aktif"
    return {"kod": kod, "ad": ad, "bolge": bolge, "yetkili": yetkili,
            "telefon": telefon, "kayit_tarihi": kayit, "durum": durum}


@lru_cache(maxsize=1)
def bayiler() -> tuple:
    liste = [
        {"kod": k, "ad": a, "bolge": b, "yetkili": y, "telefon": t,
         "kayit_tarihi": kt, "durum": d}
        for k, a, b, y, t, kt, d in _SEED_BAYILER
    ]
    liste += [_uretilmis_bayi(i) for i in range(9, 52)]
    return tuple(liste)


# v1 yolcu sayfasındaki 8 hat: (hat_no, güzergah, mod, hafta içi baz biniş,
# hafta sonu bazın oranı, baz doluluk yüzdesi)
HATLAR = [
    ("34", "Avcılar — Zincirlikuyu", "Metrobüs", 96420, 0.635, 92),
    ("M4", "Kadıköy — Tavşantepe", "Metro", 74850, 0.654, 81),
    ("T1", "Kabataş — Bağcılar", "Tramvay", 58310, 0.723, 88),
    ("500T", "Tuzla — Cevizlibağ", "Otobüs", 41270, 0.643, 76),
    ("E-5", "Söğütlüçeşme — Beylikdüzü", "Otobüs", 38940, 0.639, 73),
    ("M2", "Yenikapı — Hacıosman", "Metro", 67190, 0.655, 79),
    ("15F", "Kadıköy — Üsküdar", "Otobüs", 22480, 0.772, 64),
    ("19", "Beşiktaş — Sarıyer", "Otobüs", 19100, 0.781, 58),
]

# Mevsimsellik: v1 gelir tablosundaki aylık seyre yakın bir eğri (Mayıs zirve)
_AY_CARPANI = {1: 0.98, 2: 0.95, 3: 1.04, 4: 1.06, 5: 1.12, 6: 1.08,
               7: 1.05, 8: 1.02, 9: 1.06, 10: 1.05, 11: 1.00, 12: 0.99}


def _gun_carpani(gun: date, hafta_sonu_orani: float) -> float:
    """Mevsim + hafta sonu etkisi + yıllık ~%12 büyüme."""
    buyume = 1.12 ** (gun.year - 2026)
    hs = hafta_sonu_orani if gun.weekday() >= 5 else 1.0
    return _AY_CARPANI[gun.month] * hs * buyume


@lru_cache(maxsize=None)
def daily_gelir(gun: date) -> dict:
    """Bir günün mod bazlı geliri (TL). v1 tablosundaki aylık seviyelerle uyumlu."""
    rng = Random(f"gelir:{gun.isoformat()}")
    carpan = _gun_carpani(gun, 0.68)
    return {
        "otobus": round(224000 * carpan * rng.uniform(0.96, 1.04)),
        "metro": round(147000 * carpan * rng.uniform(0.96, 1.04)),
        "tramvay": round(66000 * carpan * rng.uniform(0.96, 1.04)),
    }


@lru_cache(maxsize=None)
def daily_binis(hat_no: str, gun: date) -> int:
    """Bir hattın bir günkü biniş sayısı."""
    hat = next(h for h in HATLAR if h[0] == hat_no)
    rng = Random(f"binis:{hat_no}:{gun.isoformat()}")
    return round(hat[3] * _gun_carpani(gun, hat[4]) * rng.uniform(0.94, 1.06))


@lru_cache(maxsize=None)
def daily_dolum(bayi_kodu: str, gun: date) -> int:
    """Bir bayinin bir günkü dolum cirosu (TL). Pasif bayi dolum yapmaz."""
    bayi = next(b for b in bayiler() if b["kod"] == bayi_kodu)
    if bayi["durum"] == "Pasif":
        return 0
    idx = int(bayi_kodu.split("-")[1]) - 1001
    baz = 14000 - idx * 150  # ilk bayiler daha yüksek ciro (v1 sıralamasına yakın)
    rng = Random(f"dolum:{bayi_kodu}:{gun.isoformat()}")
    hs = 0.8 if gun.weekday() >= 5 else 1.0
    return round(baz * hs * rng.uniform(0.75, 1.25) / 10) * 10


_DOLUM_TUTARLARI = [50, 100, 150, 200, 250, 300]
_BINIS_UCRETI = 27.50
_AKTARMA_UCRETI = 13.75
_INDIRIMLI_UCRETI = 13.35


@lru_cache(maxsize=None)
def kart_transactions(gun: date) -> tuple:
    """Bir günün kart işlemleri (30-60 adet), saate göre yeniden eskiye sıralı."""
    rng = Random(f"kart:{gun.isoformat()}")
    adet = rng.randint(30, 60)
    aktif_bayiler = [b for b in bayiler() if b["durum"] == "Aktif"]
    islemler = []
    for i in range(adet):
        tip = rng.choices(
            ["Dolum", "Biniş", "Aktarma", "İndirimli"],
            weights=[22, 50, 14, 14],
        )[0]
        if tip == "Dolum":
            if rng.random() < 0.25:
                nokta = "Mobil Uygulama"
            else:
                b = rng.choice(aktif_bayiler)
                nokta = f"{b['kod']} {b['ad']}"
            tutar = rng.choice(_DOLUM_TUTARLARI)
        else:
            hat = rng.choice(HATLAR)
            nokta = f"{hat[0]} {hat[2]}"
            tutar = {"Biniş": _BINIS_UCRETI, "Aktarma": _AKTARMA_UCRETI,
                     "İndirimli": _INDIRIMLI_UCRETI}[tip]
        saat = f"{rng.randint(6, 23):02d}:{rng.randint(0, 59):02d}"
        islemler.append({
            "tarih": gun,
            "saat": saat,
            "islem_tipi": tip,
            "kart_no": f"5312 **** {rng.randint(1000, 9999)}",
            "nokta": nokta,
            "tutar": tutar,
        })
    islemler.sort(key=lambda x: x["saat"], reverse=True)
    # İşlem no: gün + gün içi sıradan türetilen deterministik numara
    for i, islem in enumerate(islemler):
        islem["islem_no"] = f"TX-9{gun.toordinal() % 10000:04d}{i:02d}"
    return tuple(islemler)


def data_start(bugun: date) -> date:
    """Veri ufkunun başlangıcı: DATA_MONTHS ay öncesinin ay başı."""
    ay = bugun.month - DATA_MONTHS
    yil = bugun.year
    while ay <= 0:
        ay += 12
        yil -= 1
    return date(yil, ay, 1)
