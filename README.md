# 📖 NEWSLY.AI – Newsletter Summarizer (Gmail + AI)

Newsly.AI, Gmail’inize gelen bültenleri tarar, istediğiniz göndericileri seçmenizi sağlar ve bunları OpenAI ile **özetler; mini başlıklar, key insights ve etiketler üretir**  
Abone olan kullanıcılara her gün saat **18:00’de otomatik olarak günlük özet maili gönderir**.
Aşağıdaki adımlarla **kendi Gmail hesabınızla** güvenli bir şekilde çalıştırabilirsiniz.

- **Frontend**: Next.js → http://localhost:3000  
- **Backend**: FastAPI → http://localhost:8000 (API) & http://localhost:8001 (DailyDigestAgent)

> **Özet akış:**  
> **MCP Gmail Sunucusu** (websocket) ⇄ **Gmail API** → içerik çekme/gönderme  
> **FastAPI Backend** → özet çıkarma ve API’ler  
> **DailyDigestAgent** → özetleri HTML e-postaya dönüştürme ve gönderme (18:00 scheduler)


---

## İçindekiler

1. [Önkoşullar](#önkoşullar)  
2. [Dizin Yapısı](#dizin-yapısı)  
3. [Python Ortamının Kurulumu](#python-ortamının-kurulumu) 
4. [Ortam Değişkenleri (.env)](#ortam-değişkenleri-env)   
5. [Google Cloud’da Gmail API ve OAuth Client Oluşturma](#google-cloudda-gmail-api-ve-oauth-client-oluşturma)  
6. [MCP Gmail Sunucusunu Çalıştırma (OAuth adımı burada tetiklenir)](#mcp-gmail-sunucusunu-çalıştırma-oauth-adımı-burada-tetiklenir)  
7. [Çalıştırma](#backend-api’yi-ve-frontend-api'yi-çalıştırma )  
8. [Gönderici Tara & Seç → Kartları Hazırla](#gönderici-tara--seç--kartları-hazırla)  
9. [DailyDigestAgent’i Çalıştır ve E-posta Gönderimini Test Et](#dailydigestagenti-çalıştır-ve-e-posta-gönderimini-test-et)    
10. [Sık Karşılaşılan Sorunlar (Troubleshooting)](#sık-karşılaşılan-sorunlar-troubleshooting)  


---

## Önkoşullar

- **Python 3.10+** (önerilir)
- **Google Cloud** hesabı
- macOS / Linux / Windows (komutlar örneklerle verildi)

> Windows’ta PowerShell kullanıyorsanız `source venv/Scripts/activate` yerine `.\venv\Scripts\activate` yazın.

---

## Dizin Yapısı

Projede temel olarak iki kısım vardır:

```
/backend
  ├─ agents/                 # DailyDigestAgent ve ilgili yardımcılar
  ├─ mcp/                    # Gmail için websocket MCP server
  ├─ routes/                 # FastAPI route'ları (newsletters vb.)
  ├─ summarizer/             # OpenAI tabanlı özetleyici
  ├─ utils/                  # Gmail client, scanning vb.
  ├─ data/                   # Çalışma verileri (token.json vb.) *git dışı*
  ├─ config/credentials/     # client_secret_*.json *git dışı*
  ├─ main.py                 # FastAPI app giriş noktası
  └─ requirements.txt
/frontend
  (opsiyonel Next.js arayüzü)
```

---

## 📦 Kurulum

### 1. Repo’yu klonlayın
```bash
git clone <https://github.com/nehirunal/documind>
cd documind
```

### 2. Backend ortamı
```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Frontend ortamı
```bash
cd frontend
npm install
```

---

## ⚙️ Ortam Değişkenleri (.env)

Kök dizindeki `.env.example` dosyasını kopyalayın:

```bash
cd backend
cp .env.example .env
```

`.env.example`  dosyasında şablon olarak gerekli tüm alanlar verilmiştir. Kendi bilgilerinize göre placeholderları doldurmanız yeterlidir. 

> 📌 Not: `GMAIL_SCOPES` sayesinde uygulama **mail okuma ve gönderme** yetkisine sahip olur.


## ⚙️ Frontend Ortam Değişkenleri (.env.local)

Frontend (Next.js) tarafında ayrıca `.env.local` dosyası gereklidir.  
Kök dizinde `frontend` klasörüne girip aşağıdaki dosyayı oluşturun:  

```bash
cd frontend
touch .env.local
```
İçerisine aşağıdakileri ekleyiniz:
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
NEXT_PUBLIC_BACKEND_URL=http://127.0.0.1:8001

>  📌 Not: Eğer backend’i veya agent’ı farklı portlarda çalıştırırsanız, buradaki URL’leri ona göre güncellemeniz gerekir. Varsayılan kurulumda 8000 (backend API) ve 8001 (DailyDigestAgent) kullanılır.
---

## 🔑 Gmail API Ayarları

Bu proje Gmail API ile çalışır. Her kullanıcının kendi Gmail hesabını bağlaması gerekir.  

NEW PROJECT;

1. **APIs & Services → Library**: “**Gmail API**”yi bulun ve **Enable** edin. 
 
2. **APIs & Services → OAuth consent screen**: 
   - Get started: App Name, Support email vb. doldurun
   - Audience: **External** (test modu yeterli)  
   -  → **Save and Continue**  
   
3. **APIs & Services → OAuth consent screen → Data Access**: Add or Remove Scopes
     Gmail okuma (restricted):
     https://www.googleapis.com/auth/gmail.modify
     Açıklama: Bülten e-postalarının içeriğini okuyup özet çıkarabilmek için okuma izni.
     Gmail gönderme (sensitive):
     https://www.googleapis.com/auth/gmail.send
     Açıklama: Günlük özet e-postasını kullanıcının kendi hesabından göndermek için.
     SAVE
     
3. **APIs & Services → OAuth consent screen → Audience**: Test Users
     Add Users → “Test users” listesine kendi Gmail adresinizi ekleyin.   
     
4. **APIs & Services → Credentials → Create Credentials → OAuth Client ID**:  
   - Application type: **Desktop app** (bu proje Desktop Flow kullanıyor)  
   - Oluşan `client_secret_*.json` dosyasını indirin.  
5. Dosyayı repoda **`backend/config/credentials/`** dizinine yerleştirin.  
6. `.env` içindeki `GOOGLE_CLIENT_SECRETS_FILE` değerini bu dosya yoluna göre güncelleyin.

> **Not:** Desktop Flow kullandığımız için `redirect_uri_mismatch` gibi web-redirect sorunlarıyla uğraşmazsınız.

---


## MCP Gmail Sunucusunu Çalıştırma (OAuth adımı burada tetiklenir)

Aşağıdaki komutla MCP’yi başlatın (venv aktifken, repo kökünden):

```bash
cd documind
source backend/venv/bin/activate
python backend/mcp/server.py
```

- Konsolda `✅ MCP listening ws://localhost:8080` çıktısını görürsünüz.  
- **İlk Gmail çağrısında** (örn. `gmail.send`, `gmail.list_messages`) tarayıcı **otomatik açılır**, Google hesabınızla giriş yapıp izin verirsiniz.  
- Yetkilendirme sonrası token dosyası, `.env`’de belirtilen yol altında **otomatik** oluşturulur (örn. `backend/data/token.json`).

---

## ▶️ Çalıştırma

### Backend’i başlat
```bash
cd documind
source backend/venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

İlk çalıştırmada Google hesabınızla giriş yapmanız istenir. OAuth tamamlanınca `token.json` oluşur. Sonraki çalıştırmalarda tekrar giriş gerekmez.

### Frontend’i başlat
```bash
cd documind/frontend
npm run dev
```

UI → [http://localhost:3000]

---

## 📰 Adım 1 – Scan (Bültenleri Tara)

`/api/newsletters/featured` çıktı üretebilmesi için önce “hangi göndericilerden bülten çekileceğini” bilmesi gerekir. Bunu **scan + selection** ile yaparsınız:

### 1. Tarama (Scan)
İlk olarak Gmail hesabınızda son **30 gün içinde gelen bültenleri** taramak için şu adrese gidin:  👉 [http://localhost:3000]

Ana sayfadan **“Get Email Scan”** butonuna basarak Gmail’inizdeki bülten taramasını başlatın. (Scan işleminin yapıldığı adres:  👉 [http://localhost:3000/newsletters])

Burada sistem Gmail’inizi tarar. Bu işlem gelen kutunuzun yoğunluğuna bağlı olarak **2-3 dakikayı bulabilir**.

---

## ✅ Adım 2 – Selection (Bültenleri Seç)

- İstemediğiniz bültenlerin **onay kutusunu kaldırın**.  
- Sağ üstten manuel olarak **“Add manual”** alanından istediğiniz gönderici adresini ekleyebilirsiniz.  
- **Save Preferences** diyerek seçimlerinizi kaydedin.  

> Seçimler `backend/data/selected_newsletters.json` dosyasına yazılır.
> Artık sistem sadece bu listede yer alan bültenleri özetleyecektir. ✅

---

## ✨ Adım 3 – Featured (Özetleri Görüntüle)

`http://localhost:3000` ana sayfasına giderek:  
- Seçtiğiniz bültenlerin özetlerini (today ve earlier olarak iki gurupta)  ve 
- Key Insights kartlarını görebilirsiniz. Bu işlem bültenlerin uzunluğuna göre 3-4 dakika sürebilir.  


> ⚠️ Not: Özetler OpenAI üzerinden yapılır.  
> Ama `.env` dosyanızda **doğrudan `OPENAI_API_KEY` yerine size verilen `SUMMARY_PROXY_URL` değerini** kullanmalısınız.  
> Bu proxy, özetleme isteklerini benim backend sunucuma yönlendirir. Böylece kendi OpenAI anahtarınızı girmenize gerek kalmaz.

---

## ⏰ Adım 4 – Abonelik ve Günlük 18:00 Gönderimi

- Abonelikler `backend/data/newsly.db` dosyasındaki **subscribers** tablosunda tutulur.  
- Uygulama üzerinden **Subscribe for free** butonuna tıklayarak kendi e‑postanızı abone edebilirsiniz.  
- ⚠️ DailyDigestAgent (port **8001**) çalışıyorsa, her gün saat **18:00’de son gelen 5 bültenin özet maili** otomatik gönderilir.


```bash
cd documind
source backend/venv/bin/activate
python backend/agents/daily_digest_agent.py
```

### 2) ANLIK GÖNDERİM (kendinize e-posta gönderir)
```bash
curl -s -X POST "http://127.0.0.1:8001/api/digest/now" \
  -H "Content-Type: application/json" \
  -d '{"email":"KENDİ_ADRESİNİZ@gmail.com"}' | jq
```

> Bu işlem 4-5 dakika sürebilir.
> `MCP_WS=ws://localhost:8080` ayarı sayesinde agent, MCP’ye bağlanır ve Gmail API ile HTML e-postayı gönderir.


### 1) ÖNİZLEME (HTML)
```bash
curl "http://127.0.0.1:8001/api/digest/preview"
```
Tarayıcıda da açabilirsiniz. Örnek: `http://127.0.0.1:8001/api/digest/preview`


---

## ✅ Özet

1. Gmail API → kendi client_secret.json dosyanızı oluşturun.  
2. `.env` ayarlarını doldurun.  
3. Backend & frontend başlatın.  
4. Newsletters → Scan → Selection → Featured adımlarını takip edin.  
5. İsterseniz abone olun, her akşam 18:00’de özet maili alın.

🚀 🚀 Newsly.AI’yi kullanmaya hazırsınız! İlginiz için teşekkürler, iyi keşifler.


---

## Sık Karşılaşılan Sorunlar (Troubleshooting)

- **`invalid_client` / **`unauthorized_client`**:**  
  `client_secret_*.json` dosyasını doğru dizine koyduğunuzdan ve `.env` yolunu doğru verdiğinizden emin olun. Gmail API **Enable** mı?
  
- **`insufficient permissions` / `403`**:**  
  Scopelar `.env` içinde `gmail.readonly` + `gmail.send` olarak girilmiş mi? Consent screen’de test kullanıcı listesine e-posta eklendi mi?

- **Tarayıcı açılmıyor / token oluşmuyor:**  
  MCP başlatıldıktan **sonra** ilk Gmail çağrısı (örn. `/api/digest/now`) tarayıcıyı tetikler. Token dosyası konumu yazılabilir olmalı (`backend/data/`).

- **`redirect_uri_mismatch`:**  
  Desktop app client kullandığınızdan emin olun (Web app değil).

- **OpenAI hataları:**  
  `OPENAI_API_KEY` boş/yanlışsa özetleme fallback’e düşebilir veya başarısız olur. Doğru olduğunu doğrulayın.

- **Zamanlayıcı 18:00’de çalışmadı:**  
  Agent çalışıyor mu? Abonelik tablosunda e-posta + timezone kaydı var mı? Sistem saati doğru mu?

- **`SSL`/`cert` uyarıları (Windows):**  
  Gerekirse `pip install certifi` ve `python -m pip install --upgrade pip` deneyin.

---
