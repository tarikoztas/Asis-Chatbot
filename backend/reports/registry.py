"""Rapor kayıt defteri — tek doğruluk kaynağı.

Her raporun sayfası, başlığı, filtreleri ve varsayılan dönemi burada tanımlıdır.
API (router/service), chatbot (dialog_manager) ve frontend filtre çubuğu
(available_filters alanı üzerinden) hep bu tanımlardan beslenir.
"""

BOLGELER = [
    "Kadıköy", "Üsküdar", "Beşiktaş", "Maltepe", "Fatih",
    "Bakırköy", "Sarıyer", "Pendik", "Eminönü",
]

MODLAR = ["Otobüs", "Metro", "Tramvay", "Metrobüs"]

ISLEM_TIPLERI = ["Dolum", "Biniş", "Aktarma", "İndirimli"]

REPORTS = {
    "dolum-hakedis": {
        "title": "Bayi Dolum Hakedişleri",
        "subtitle": "Bayi bazlı dolum tutarları, komisyon ve hakediş özetleri",
        "page": "/pages/dolum-hakedis.html",
        "intent_id": "dolum_hakedis",
        "default_period": "bu ay",
        "enum_filters": {
            "bolge": {"label": "Bölge", "values": BOLGELER, "synonyms": {}},
            "durum": {
                "label": "Durum",
                "values": ["Ödendi", "Bekliyor"],
                "synonyms": {
                    "ödenmiş": "Ödendi", "ödenen": "Ödendi", "ödenenler": "Ödendi",
                    "bekleyen": "Bekliyor", "bekleyenler": "Bekliyor",
                    "ödenmemiş": "Bekliyor", "ödenmeyen": "Bekliyor",
                },
            },
        },
        "filter_hint": (
            "İsterseniz bir tarih aralığı veya bölge yazın; sonuçları ona göre "
            "filtreleyeyim (örn. \"haziran ayı\", \"son 3 ay\", \"sadece Kadıköy\")."
        ),
    },
    "gelir-raporlari": {
        "title": "EÜTS Gelir Raporları",
        "subtitle": "Aylık gelir özeti — tüm ulaşım modları",
        "page": "/pages/gelir-raporlari.html",
        "intent_id": "gelir_raporu",
        "default_period": "bu yıl",
        "enum_filters": {},
        "filter_hint": (
            "İsterseniz bir tarih aralığı yazın; raporu ona göre getireyim "
            "(örn. \"haziran ayı\", \"son 1 sene\", \"ocak - mart\")."
        ),
    },
    "yolcu-istatistikleri": {
        "title": "Yolcu İstatistikleri",
        "subtitle": "Hat bazlı günlük ortalama biniş sayıları",
        "page": "/pages/yolcu-istatistikleri.html",
        "intent_id": "yolcu_istatistik",
        "default_period": "son 30 gün",
        "enum_filters": {
            "mod": {"label": "Ulaşım Modu", "values": MODLAR, "synonyms": {}},
        },
        "filter_hint": (
            "İsterseniz bir tarih aralığı veya ulaşım modu yazın "
            "(örn. \"bu hafta\", \"geçen ay\", \"sadece metro\")."
        ),
    },
    "kart-islemleri": {
        "title": "Kart İşlemleri",
        "subtitle": "Akıllı kart dolum ve kullanım işlemleri",
        "page": "/pages/kart-islemleri.html",
        "intent_id": "kart_islemleri",
        "default_period": "son 7 gün",
        "enum_filters": {
            "islem_tipi": {
                "label": "İşlem Tipi",
                "values": ISLEM_TIPLERI,
                "synonyms": {"indirimli biniş": "İndirimli"},
            },
        },
        "filter_hint": (
            "İsterseniz bir tarih aralığı veya işlem tipi yazın "
            "(örn. \"bugün\", \"son 7 gün\", \"sadece dolumlar\")."
        ),
    },
    "bayi-yonetimi": {
        "title": "Bayi Yönetimi",
        "subtitle": "Kayıtlı dolum noktaları ve durumları",
        "page": "/pages/bayi-yonetimi.html",
        "intent_id": "bayi_yonetimi",
        "default_period": None,  # tarih filtresi kayıt tarihine uygulanır; varsayılan = tümü
        "enum_filters": {
            "bolge": {"label": "Bölge", "values": BOLGELER, "synonyms": {}},
            "durum": {
                "label": "Durum",
                "values": ["Aktif", "Pasif"],
                "synonyms": {"çalışan": "Aktif", "kapalı": "Pasif"},
            },
        },
        "filter_hint": (
            "İsterseniz bölge, durum veya kayıt tarihi aralığı yazın "
            "(örn. \"sadece Pendik\", \"pasif bayiler\", \"2022 yılı kayıtları\")."
        ),
    },
}

INTENT_TO_REPORT = {v["intent_id"]: k for k, v in REPORTS.items()}
