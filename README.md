# Asis Chatbot — EÜTS Rapor Portalı

Asis Elektronik ve Bilişim Sistemleri staj projesi: siteye entegre edilebilir,
kural tabanlı bir **yönlendirme chatbotu** ve üzerinde çalıştığı EÜTS temalı örnek website.

Kullanıcı sohbet balonuna yapmak istediği işlemi yazar
(örn. *"Bayilerin dolum hakedişini görmek istiyorum"*), chatbot ilgili sayfanın
tıklanabilir linkini döner. Emin olamazsa en yakın 3 sayfayı önerir.

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

## Proje Detayları

