"""v2 uçtan uca duman testi — yalnız stdlib (urllib).

Çalışan bir sunucu gerektirir:
    uvicorn backend.main:app --port 8000
Çalıştırma:
    python scripts/smoke_test.py [http://localhost:8000]

Tarihe bağımlı senaryolarda mutlak tarihler ("01.06.2026") ya da yapısal
kontroller (action / report_id / filtre anahtarları) kullanılır; böylece test
"bugün" ilerledikçe bozulmaz.
"""

import json
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
HATALAR = []


def kontrol(ad, kosul, detay=""):
    durum = "OK  " if kosul else "FAIL"
    print(f"[{durum}] {ad}")
    if not kosul:
        HATALAR.append(f"{ad}: {detay}")


def get(path):
    with urllib.request.urlopen(BASE + path) as r:
        return r.status, json.loads(r.read().decode("utf-8"))


def get_status(path):
    try:
        with urllib.request.urlopen(BASE + path) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def chat(message, context=None):
    govde = {"message": message}
    if context is not None:
        govde["context"] = context
    istek = urllib.request.Request(
        BASE + "/api/chat",
        data=json.dumps(govde).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with urllib.request.urlopen(istek) as r:
        return json.loads(r.read().decode("utf-8"))


# --- Rapor API'si ------------------------------------------------------------

_, r1 = get("/api/reports/gelir-raporlari?start=2026-06-01&end=2026-06-30")
_, r2 = get("/api/reports/gelir-raporlari?start=2026-06-01&end=2026-06-30")
kontrol("rapor determinizmi", r1 == r2)
kontrol("gelir haziran tek satır", len(r1["rows"]) == 1
        and r1["rows"][0]["ay"] == "Haziran 2026", str(r1["rows"]))

_, r = get("/api/reports/dolum-hakedis?start=2026-06-01&end=2026-06-30"
           + "&" + urllib.parse.urlencode({"bolge": "Kadıköy"}))
kontrol("dolum bölge filtresi", r["rows"]
        and all(s["bolge"] == "Kadıköy" for s in r["rows"]), str(r["rows"][:2]))

_, r = get("/api/reports/bayi-yonetimi")
kontrol("bayi 52/48/4", [s["value"] for s in r["stats"]][:3] == ["52", "48", "4"],
        str(r["stats"]))

_, r = get("/api/reports/kart-islemleri?start=2026-06-01&end=2026-06-30&limit=50")
kontrol("kart satır kesme", len(r["rows"]) == 50 and r["total_rows"] > 50,
        f"rows={len(r['rows'])} total={r['total_rows']}")

kontrol("bilinmeyen rapor 404", get_status("/api/reports/olmayan") == 404)
kontrol("bozuk tarih 422", get_status("/api/reports/gelir-raporlari?start=x") == 422)
kontrol("geçersiz enum 422",
        get_status("/api/reports/yolcu-istatistikleri?mod=Feribot") == 422)

# --- Chatbot: v1 davranışı (bağlamsız yönlendirme senaryoları) ---------------

V1_YONLENDIRME = {
    "bayilerin dolum hakedişini görmek istiyorum": "/pages/dolum-hakedis.html",
    "gelir raporlarını göster": "/pages/gelir-raporlari.html",
    "yolcu istatistikleri": "/pages/yolcu-istatistikleri.html",
    "kart işlemlerine bak": "/pages/kart-islemleri.html",
    "bayi yönetimi sayfasını aç": "/pages/bayi-yonetimi.html",
    "sizinle nasıl iletişime geçebilirim": "/pages/iletisim.html",
}
for mesaj, link in V1_YONLENDIRME.items():
    r = chat(mesaj)
    kontrol(f"v1 yönlendirme: {mesaj!r}", r["link"] == link, str(r))

r = chat("merhaba")
kontrol("v1 selamlama", r["link"] is None and r["action"] is None, str(r))
r = chat("rapor")
kontrol("v1 'rapor' önerileri", r["link"] is None and len(r["suggestions"]) == 3,
        str(r))
r = chat("asdfgh qwerty")
kontrol("v1 fallback", r["link"] is None and len(r["suggestions"]) == 6, str(r))

# --- Chatbot: v2 filtre diyaloğu ---------------------------------------------

r = chat("gelir raporlarını göster")
kontrol("navigate + ipucu", r["action"] == "navigate"
        and r["report_id"] == "gelir-raporlari" and r["filters"] is None
        and "tarih aralığı" in r["reply"], str(r))

r = chat("01.06.2026 - 30.06.2026", {"last_report_id": "gelir-raporlari"})
kontrol("takip mesajı: aralık + link (bekleyen)",
        r["action"] == "apply_filters"
        and r["filters"]["start"] == "2026-06-01"
        and r["filters"]["end"] == "2026-06-30"
        and r["link"] == "/pages/gelir-raporlari.html", str(r))

r = chat("haziran ayı", {"report_id": "gelir-raporlari"})
kontrol("sayfada: haziran canlı filtre",
        r["action"] == "apply_filters" and r["link"] is None
        and r["filters"]["start"].endswith("-06-01"), str(r))

r = chat("son 1 sene", {"report_id": "kart-islemleri"})
kontrol("son 1 sene", r["action"] == "apply_filters"
        and r["filters"] and "start" in r["filters"], str(r))

r = chat("bu hafta", {"report_id": "yolcu-istatistikleri"})
kontrol("bu hafta", r["action"] == "apply_filters", str(r))

r = chat("sadece metro", {"report_id": "yolcu-istatistikleri"})
kontrol("enum: sadece metro", r["action"] == "apply_filters"
        and r["filters"] == {"mod": "Metro"}, str(r))

r = chat("metro istatistikleri")
kontrol("bağlamsız 'metro istatistikleri' yönlendirir",
        r["action"] == "navigate" and r["report_id"] == "yolcu-istatistikleri",
        str(r))

r = chat("haziran ayı dolum hakedişleri")
kontrol("tek turda niyet+filtre", r["action"] == "navigate"
        and r["report_id"] == "dolum-hakedis"
        and r["filters"] and r["filters"]["start"].endswith("-06-01"), str(r))

r = chat("1 haziran")
kontrol("hedefsiz filtre: hangi rapor?", r["action"] is None
        and r["filters"] and len(r["suggestions"]) == 5, str(r))

r = chat("bekleyen hakedişler", {"report_id": "dolum-hakedis"})
kontrol("enum eş anlamlı: bekleyen", r["filters"]
        and r["filters"].get("durum") == "Bekliyor", str(r))

r = chat("teşekkürler", {"report_id": "gelir-raporlari"})
kontrol("bağlamda teşekkür filtre üretmez", r["action"] is None
        and r["filters"] is None, str(r))

# --- Sonuç -------------------------------------------------------------------

print()
if HATALAR:
    print(f"{len(HATALAR)} HATA:")
    for h in HATALAR:
        print(" -", h)
    sys.exit(1)
print("Tüm duman testleri geçti.")
