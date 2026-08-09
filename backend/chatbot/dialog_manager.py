"""Diyalog yöneticisi — çok adımlı filtre diyaloğunun orkestrasyon katmanı.

IntentMatcher'ı DEĞİŞTİRMEDEN sarar (match() arayüzü ileride LLM'e geçiş için
korunuyor). Akış:

1. HAM mesajdan tarih ifadesi (date_parser) ve — bir rapor bağlamı varsa —
   enum filtre değerleri (bölge, işlem tipi, mod, durum) çıkarılır.
   (normalize() noktaları sildiği için tarih ayrıştırma matcher'dan ÖNCE ve
   ham metin üzerinde yapılmak zorundadır.)
2. Tüketilen karakter aralıkları mesajdan çıkarılır; kalan metin v1
   IntentMatcher'a verilir. Bu sıralama kelime çakışmalarını çözer:
   yolcu sayfasında "sadece metro" bir filtredir, ana sayfada
   "metro istatistikleri" bir yönlendirmedir.
3. Karar: rapor niyeti doğrudan eşleşti → navigate (+ varsa filtreler);
   niyet zayıf ama filtre + hedef var → apply_filters;
   filtre var hedef yok → hangi rapor sorusu;
   hiçbiri → v1 davranışı aynen.

Yanıt, v1 anahtarlarına (reply, link, link_text, suggestions) üç ek alan
katar: action ("navigate" | "apply_filters" | None), report_id, filters.
"""

import re
from datetime import date

from backend.chatbot import date_parser
from backend.chatbot.intent_matcher import IntentMatcher
from backend.reports.registry import REPORTS

# Niyetin link'i ile rapor kaydını eşle (intents.json'a alan eklemeye gerek yok)
PAGE_TO_REPORT = {meta["page"]: rid for rid, meta in REPORTS.items()}

# Aksan katlama: kullanıcı "kadikoy" da yazsa "Kadıköy" ile eşleşsin
_TR_FOLD = str.maketrans("çğıöşü", "cgiosu")

_TOKEN_RX = re.compile(r"[a-zçğıöşü0-9]+")


def _fold(s: str) -> str:
    return date_parser._norm(s).translate(_TR_FOLD)


class DialogManager:
    def __init__(self, matcher: IntentMatcher | None = None):
        self.matcher = matcher or IntentMatcher()
        # report_id -> {katlanmış aday: kanonik değer} sözlükleri (bir kez kur)
        self._enum_index = {}
        for rid, meta in REPORTS.items():
            index = {}
            for anahtar, tanim in meta["enum_filters"].items():
                adaylar = {_fold(v): v for v in tanim["values"]}
                adaylar.update({_fold(s): v for s, v in tanim["synonyms"].items()})
                index[anahtar] = adaylar
            self._enum_index[rid] = index

    # ---------- Filtre çıkarımı ----------

    def _extract_enums(self, message: str, report_id: str | None):
        """Mesajdaki enum filtre değerlerini ve tüketilen aralıkları bulur.

        Yalnız hedef raporun sözlüğüne bakılır; böylece "metro" kelimesi ancak
        yolcu bağlamı varken bir filtre sayılır.
        """
        filters, spans = {}, []
        if report_id not in self._enum_index:
            return filters, spans
        norm = date_parser._norm(message)
        for anahtar, adaylar in self._enum_index[report_id].items():
            for m in _TOKEN_RX.finditer(norm):
                token = _fold(m.group(0))
                bulunan = adaylar.get(token)
                if bulunan is None:
                    # Türkçe ek toleransı: "dolumlar" -> Dolum, "bekleyenleri" -> Bekliyor
                    for aday, deger in adaylar.items():
                        if len(aday) >= 4 and token.startswith(aday):
                            bulunan = deger
                            break
                if bulunan is not None:
                    filters[anahtar] = bulunan
                    spans.append(m.span())
                    break
        return filters, spans

    @staticmethod
    def _strip(text: str, spans) -> str:
        karakterler = list(text)
        for bas, son in spans:
            for i in range(bas, son):
                karakterler[i] = " "
        return "".join(karakterler)

    @staticmethod
    def _filters_for(filters: dict, report_id: str) -> dict:
        """Filtreleri hedef raporun desteklediği anahtarlara indirger."""
        izinli = {"start", "end", "label"} | set(REPORTS[report_id]["enum_filters"])
        return {k: v for k, v in filters.items() if k in izinli}

    @staticmethod
    def _filter_cumlesi(filters: dict, report_id: str) -> str:
        """'Haziran 2026 · Bölge: Kadıköy' gibi okunur bir özet üretir."""
        parcalar = []
        if filters.get("label"):
            parcalar.append(filters["label"])
        for anahtar, tanim in REPORTS[report_id]["enum_filters"].items():
            if anahtar in filters:
                parcalar.append(f"{tanim['label']}: {filters[anahtar]}")
        return " · ".join(parcalar)

    # ---------- Ana giriş ----------

    def respond(self, message: str, context: dict | None = None,
                today: date | None = None) -> dict:
        context = context or {}
        target = context.get("report_id") or context.get("last_report_id")
        if target not in REPORTS:
            target = None

        tarih = date_parser.parse_date_expression(message, today=today)
        spans = list(tarih[1]) if tarih else []
        enum_filters, enum_spans = self._extract_enums(message, target)
        spans += enum_spans

        filters = {}
        if tarih:
            filters["start"] = tarih[0]["start"].isoformat()
            filters["end"] = tarih[0]["end"].isoformat()
            filters["label"] = tarih[0]["label"]
        filters.update(enum_filters)

        # Filtre olarak tüketilen kelimeler çıkarılıp kalan niyete sorulur
        result = self.matcher.match(self._strip(message, spans) if spans else message)
        base = {**result, "action": None, "report_id": None, "filters": None}

        # 1) Doğrudan eşleşme bir rapor sayfasıysa -> navigate (+ varsa filtre)
        rid = PAGE_TO_REPORT.get(result["link"]) if result["link"] else None
        if rid is not None:
            meta = REPORTS[rid]
            uygulanan = self._filters_for(filters, rid) if filters else None
            if uygulanan and set(uygulanan) - {"label"}:
                ozet = self._filter_cumlesi(uygulanan, rid)
                reply = f"{result['reply']}\n\n{ozet} filtresiyle açıyorum."
            else:
                uygulanan = None
                reply = f"{result['reply']}\n\n{meta['filter_hint']}"
            return {**base, "reply": reply, "action": "navigate",
                    "report_id": rid, "filters": uygulanan}

        # Doğrudan eşleşme rapor dışı bir niyetse (iletişim/selamlama/teşekkür)
        if result["link"] or not filters:
            # 4) filtre de yoksa: v1 davranışı aynen (öneriler/fallback dahil)
            return base

        # 2) Niyet zayıf ama filtre bulundu ve bir rapor bağlamı var -> uygula
        if target is not None:
            meta = REPORTS[target]
            uygulanan = self._filters_for(filters, target)
            ozet = self._filter_cumlesi(uygulanan, target)
            sayfada = context.get("report_id") == target
            if sayfada:
                reply = f"Elbette — {ozet} filtresini uyguladım, tablo güncellendi."
                link, link_text = None, None
            else:
                reply = (f"{ozet} filtresini hazırladım. "
                         f"{meta['title']} sayfasını açtığınızda uygulanacak:")
                link, link_text = meta["page"], meta["title"]
            return {"reply": reply, "link": link, "link_text": link_text,
                    "suggestions": [], "action": "apply_filters",
                    "report_id": target, "filters": uygulanan}

        # 3) Filtre var ama hangi rapor için olduğu belirsiz
        ozet = filters.get("label") or "istediğiniz"
        return {
            "reply": (f"{ozet} dönemini not ettim. Hangi raporu görmek "
                      "istersiniz? Aşağıdan seçin veya yazın:"),
            "link": None, "link_text": None,
            "suggestions": [
                {"link": meta["page"], "link_text": meta["title"]}
                for meta in REPORTS.values()
            ],
            "action": None, "report_id": None, "filters": filters,
        }
