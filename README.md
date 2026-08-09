# Asis Chatbot — EÜTS Rapor Portalı

Asis Elektronik ve Bilişim Sistemleri staj projesi: siteye entegre edilebilir,
kural tabanlı bir **yönlendirme chatbotu** ve üzerinde çalıştığı EÜTS temalı örnek website.

Kullanıcı sohbet balonuna yapmak istediği işlemi yazar
(örn. *"Bayilerin dolum hakedişini görmek istiyorum"*), chatbot ilgili sayfanın
tıklanabilir linkini döner. Emin olamazsa en yakın 3 sayfayı önerir.

**v2 ile:** rapor sayfaları dinamikleşti (backend'den deterministik mock veri +
tarih ve rapora özel filtreler) ve chatbot çok adımlı filtre diyaloğu yapabiliyor:
*"haziran ayı"*, *"son 1 sene"*, *"bu hafta"*, *"1 haziran - 15 temmuz"*,
*"sadece metro"* gibi ifadeleri anlayıp açık sayfadaki filtreyi sayfa yenilenmeden
uygular; başka sayfadaysanız filtre, hedef sayfa açılırken uygulanır.

## Kurulum (Windows / PowerShell)

```powershell
cd "D:\Asis Chatbot"
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Çalıştırma

```powershell
uvicorn backend.main:app --reload --port 8000
```


- Site: http://localhost:8000
- API dokümantasyonu: http://localhost:8000/docs

## API Örnekleri

```powershell
# Chatbot (v1 uyumlu — context opsiyonel)
Invoke-RestMethod -Uri http://localhost:8000/api/chat -Method Post `
  -ContentType "application/json; charset=utf-8" `
  -Body '{"message": "haziran ayı", "context": {"report_id": "gelir-raporlari"}}'

# Rapor verisi (tarih + rapora özel filtreler)
Invoke-RestMethod "http://localhost:8000/api/reports/gelir-raporlari?start=2026-06-01&end=2026-06-30"
Invoke-RestMethod "http://localhost:8000/api/reports/yolcu-istatistikleri?mod=Metro"
```

Rapor kimlikleri: `dolum-hakedis`, `gelir-raporlari`, `yolcu-istatistikleri`,
`kart-islemleri`, `bayi-yonetimi`.

## Testler

```powershell
# Türkçe tarih ayrıştırıcı öz-testleri (sunucu gerekmez)
.\venv\Scripts\python.exe -m backend.chatbot.date_parser

# Uçtan uca duman testi (sunucu çalışırken, ayrı terminalde)
.\venv\Scripts\python.exe scripts\smoke_test.py
```

## Proje Detayları

Mimari, rapor API sözleşmesi ve değişiklik günlüğü için `CLAUDE.md` dosyasına bakın.
