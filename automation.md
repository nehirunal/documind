\# 🧠 **4\. Otomasyon ve Ajans Mantığı** 

\## 🎯 Amaç

Bu projede, kullanıcıların e-posta adreslerini girerek **günlük haber özetlerine abone olabilecekleri** ve her sabah bu özetleri otomatik olarak e-posta yoluyla alabilecekleri bir sistem geliştirilmiştir. 

Günümüzde zaman en değerli kaynaklardan biridir ve kullanıcıların onlarca haber sitesini gezmek yerine hızlıca özetlenmiş bilgiye ulaşma ihtiyacı giderek artmaktadır. Bu ihtiyaçtan yola çıkarak geliştirilen sistem, haberleri kullanıcının yerine takip eder, özetler ve her sabah zahmetsizce e-posta kutularına ulaştırır.

Süreç tamamen otomatiktir ve **LangChain** tabanlı bir agent ile çalışmaktadır. Agent, haber kaynaklarını analiz eder, doğal dilde özetler üretir ve bu içerikleri her sabah ilgili kullanıcılara ulaştırır.

Kullanıcı tarafında ise işlem son derece basittir: **"Günlük Haber Özeti"** butonuna tıklanarak e-posta adresi girilir ve bu e-posta adresi sistemde ( dosya yapısında) saklanır. Bu sayede sonraki her gün, kullanıcının müdahalesine gerek kalmadan, günün haber özeti otomatik olarak kendisine iletilir.

Bu sistem hem manuel olarak tetiklenebilir hem de her gün belirli saatte `cron` üzerinden otomatik olarak başlatılır.


\---

\## 🔗 GitHub Reposu  
https://github.com/nehirunal/documind

\## 🤖 Kullanılan Agent Mimarisi

\### 📦 Teknolojiler

\- \*\*LangChain ChatOpenAI (gpt-3.5-turbo)\*\*

\- \*\*FastAPI (REST endpoint'ler için)\*\*

\- \*\*RSS Reader\*\* (\`ntv.com.tr/turkiye.rss\`)

\- \*\*SMTP E-posta Gönderimi\*\* (Gmail üzerinden)

\- \*\*E-posta Abonelik Sistemi\*\* (\`subscribers.txt\`)

\- \*\*Zamanlama için CronJob\*\*

\---

\## 🧠 Agent Davranışı

1\. \*\*Haber Toplama:\*\*

\- \`rss\_reader.py\` ile \`https://www.ntv.com.tr/turkiye.rss\` üzerinden en güncel 5 haber başlığı çekilir.

\- Başlıklar ve linkler birleştirilir ve 2000 karakterden fazlaysa kırpılır.

2\. \*\*Özetleme (LangChain Agent):\*\*

\- \`email\_agent.py\` dosyasındaki agent, başlıkları tek tek özetler.

\- System prompt: \`"Sen haberleri özetleyen bir asistansın."\`

3\. \*\*E-posta Gönderimi:\*\*

\- Tüm abonelerin listesi \`data/subscribers.txt\` içinden alınır.

\- Her e-posta için özet içeriği gönderilir.

\---

### ✋ Sistemi Manuel Olarak Çalıştırmak

E-posta özeti sisteminin çalışabilmesi için önce **abonelik** işlemi yapılmalıdır. Kullanıcılar, frontend arayüzündeki **"Günlük Haber Özeti"** butonuna tıklayarak **e-posta adreslerini sisteme kaydetmelidir**. Bu işlem sonucunda e-posta adresleri `backend/data/subscribers.txt` dosyasına otomatik olarak eklenir.

> ❗ Eğer kullanıcı e-posta adresini bırakmamışsa, sistem haber özetini hiçbir kullanıcıya gönderemez.

---

#### 🔹 Terminal Üzerinden Manuel Çalıştırma

```bash
# Proje dizinine git
cd ~/Desktop/documind

# Sanal ortamı aktifleştir
source backend/venv/bin/activate

# Agent'i manuel olarak çalıştır
python backend/agents/email_agent.py


#FastAPI Üzerinden (GET endpoint)
Backend çalışıyorsa aşağıdaki endpoint ile sistem tetiklenebilir:
GET http://localhost:8000/run-agent



\## ⚙️ FastAPI Endpoint’leri (\`main.py\`)

| Route | Açıklama |

|-------|----------|

| \`POST /summarize\` | PDF dosyasından özet alır, isteğe bağlı olarak e-posta gönderir. |

| \`POST /summarize-url\` | Verilen URL'den içerik özetler. |

| \`POST /subscribe-news\` | Kullanıcının e-posta adresini kaydeder. |

| \`POST /send-email\` | Belirli bir e-posta adresine manuel içerik gönderir. |

| \`GET /run-agent\` | Manuel olarak agent çalıştırır, özet oluşturur ve test e-postası gönderir. |

| \`GET /send-to-all\` | Tüm abonelere haber özeti gönderir. |

\> Not: \`/run-agent\` sadece tek bir test e-postası gönderirken, \`/send-to-all\` tüm abone listesine gönderim yapar.

\---

\## ⏰ Zamanlama – Cron Job

Bu sistemin sabahları otomatik olarak çalışması için aşağıdaki \*\*cron görevi\*\* yapılandırılmıştır:

\`\`\`cron

0 9 \* \* \* /usr/bin/python3 /path/to/project/agents/email\_agent.py

**📄 email_log.txt**

Bu dosya, agent'ın gerçekten tetiklendiğini ve çıktılar ürettiğini göstermektedir.
