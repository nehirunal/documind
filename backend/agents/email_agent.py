# backend/agents/email_agent.py
import os
import json
import asyncio
import websockets
import urllib.parse as urlparse
import time, uuid
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI

from langchain_core.messages import SystemMessage, HumanMessage

import aiohttp
from datetime import datetime

load_dotenv()

NEWSLY_API_URL = os.getenv("NEWSLY_API_URL", "http://localhost:8000/newsletters/import")
NEWSLY_API_KEY = os.getenv("NEWSLY_API_KEY", "dev-key")
USER_EMAIL = os.getenv("USER_EMAIL")  


WS_URI = os.getenv("MCP_WS", "ws://localhost:8080")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Hızlı ve ekonomik model
llm = ChatOpenAI(model="gpt-4o-mini", api_key=OPENAI_API_KEY)

async def push_to_newsly(full_items: list):
    """Full içerikleri Newsly API'ye gönder."""
    payload = {
        "user_email": USER_EMAIL,
        "items": [{
            "gmail_id": it.get("id") or it.get("gmail_id") or "",
            "subject": it.get("subject") or "",
            "sender": it.get("from") or "",
            "body": it.get("content") or it.get("snippet") or "",
            "category": it.get("category") or None,
            "received_at": it.get("internalDate") or datetime.utcnow().isoformat()
        } for it in full_items]
    }
    async with aiohttp.ClientSession() as sess:
        async with sess.post(
            NEWSLY_API_URL,
            json=payload,
            headers={"x-api-key": NEWSLY_API_KEY, "Content-Type": "application/json"}
        ) as resp:
            if resp.status != 200:
                txt = await resp.text()
                raise RuntimeError(f"Newsly import failed: {resp.status} {txt}")
            data = await resp.json()
            print(">>> NEWSLY IMPORT:", data)
            return data

# ---------------- MCP yardımcıları ----------------
async def mcp_call(ws, type_, payload=None):
    """MCP server'a araç çağrısı yapar; connected ve ara paketleri atlar."""
    await ws.send(json.dumps({"type": type_, "payload": payload or {}}))
    while True:
        raw = await ws.recv()
        msg = json.loads(raw)
        mtype = msg.get("type", "")
        if mtype == "connected":
            continue
        if mtype == f"{type_}.result" and "result" in msg:
            return msg
        if mtype == f"{type_}.error" or "error" in msg:
            err = msg.get("error") or msg.get("result", {}).get("error") or "unknown_error"
            raise RuntimeError(f"MCP error ({type_}): {err}")
        # farklı tip mesaj geldiyse okumaya devam

async def ensure_oauth():
    """Callback'siz: tarayıcıdaki TAM URL'yi veya sadece code'u yapıştır."""
    # 1) URL al
    async with websockets.connect(WS_URI) as ws:
        await ws.send(json.dumps({"type": "connect", "agent_name": "EmailAgent", "version": "1.0"}))
        r1 = await mcp_call(ws, "gmail.oauth_url")
        auth_url = r1["result"]["auth_url"]
        print("🔗 OAuth URL:", auth_url)
        try:
            import webbrowser; webbrowser.open(auth_url)
        except Exception:
            pass

    # 2) Kullanıcıdan tam URL veya code al
    print("\nTarayıcı onayından sonra:")
    print("- Adres çubuğundaki TAM URL'yi yapıştırabilir")
    print("- Ya da sadece 'code' değerini yapıştırabilirsin.\n")
    raw = input("Tam URL veya sadece code: ").strip()

    if raw.startswith("http"):
        parsed = urlparse.urlparse(raw)
        q = urlparse.parse_qs(parsed.query)
        frag = urlparse.parse_qs(parsed.fragment)
        code = (q.get("code", [""])[0]) or (frag.get("code", [""])[0])
    else:
        code = raw

    if not code:
        raise RuntimeError("Code bulunamadı. Tam URL'yi veya yalnız code'u yapıştır.")

    # 3) Code'u token ile değiş
    async with websockets.connect(WS_URI) as ws:
        await ws.send(json.dumps({"type": "connect", "agent_name": "EmailAgent", "version": "1.0"}))
        r2 = await mcp_call(ws, "gmail.exchange_code", {"code": code})
        if r2.get("result", {}).get("status") == "ok":
            print("🔐 OAuth tamamlandı ve token kaydedildi (backend/token.json).")
        else:
            err = r2.get("error") or r2.get("result", {}).get("error")
            raise RuntimeError(f"OAuth hata: {err or r2}")

async def fetch_gmail_messages(limit=10, query=None):
    async with websockets.connect(WS_URI) as ws:
        await ws.send(json.dumps({"type": "connect", "agent_name": "EmailAgent", "version": "1.0"}))
        payload = {"max_results": limit}
        if query:
            payload["q"] = query 
            payload["query"] = query               # <-- Gmail API'de param adı 'q'
        print(">>> LIST PAYLOAD:", payload)     # DEBUG

        r = await mcp_call(ws, "gmail.list_messages", payload)
        ids = [m["id"] for m in r["result"].get("messages", [])]
        print(">>> LIST IDS:", ids)             # DEBUG

        items = []
        for mid in ids:
            d = await mcp_call(ws, "gmail.get_message", {"id": mid})
            items.append(d["result"])
        # ilk birkaç konuyu yazalım
        print(">>> SUBJECTS:", [i.get("subject") for i in items])
        return items


async def gmail_send(to, subject, body):
    async with websockets.connect(WS_URI) as ws:
        await ws.send(json.dumps({"type": "connect", "agent_name": "EmailAgent", "version": "1.0"}))
        r = await mcp_call(ws, "gmail.send", {"to": to, "subject": subject, "body": body})
        if r.get("result", {}).get("status") != "ok":
            raise RuntimeError(f"Gönderim hatası: {r}")

# ---------------- Özetleme ----------------
def summarize_threads_turkish(messages) -> str:
    joined = "\n\n".join([
        f"---\nKonu: {m.get('subject','(yok)')}\nGönderen: {m.get('from','')}\nİçerik:\n{(m.get('content') or m.get('snippet') or '')[:4000]}"
        for m in messages
    ])
    prompt = (
        "Aşağıda farklı bülten e-postalarından parçalar var.\n"
        "Türkçe, 120-150 kelime, 3-6 madde işaretli özet yaz.\n"
        "Sonda 1-2 maddelik 'Eylem önerisi' ekle.\n\n"
        f"{joined}"
    )
    # __call__ yerine invoke kullanıyoruz
    resp = llm.invoke([SystemMessage(content="Kısa ve aksiyon odaklı Türkçe bülten özetleyicisin."),
                       HumanMessage(content=prompt)])
    return resp.content.strip()

def _filter_for_summary(messages):
    filtered = []
    for m in messages:
        subj = (m.get('subject') or '').strip()
        text = (m.get('content') or m.get('snippet') or '')
        if subj.startswith('[GMAIL]'):
            continue
        if 'SOURCE=GMAIL_API' in text:
            continue
        filtered.append(m)
    return filtered

# ---------------- Seed + Özet + Gönder ----------------
async def seed_fake_newsletters(to_email: str):
    samples = [
        ("Tech Weekly Digest - Test",
         """Yapay zeka dünyasında son haftada öne çıkan gelişmeler:
- OpenAI ve Google, yeni dil modelleri için ortak veri seti standardı üzerinde anlaştı.
- Avrupa'da yapay zeka regülasyonları yürürlüğe girdi; startup ekosisteminde hareketlilik var.
- Amazon, kuantum girişimlerine 500M$ yatırım planlıyor.
Röportajlar ve 2025 teknoloji trendlerine dair öngörüler bu sayıda."""),
        ("Business Insider Daily - Test",
         """Güne piyasa özeti:
- ABD borsaları faiz beklentileriyle dalgalı, teknoloji hisselerinde toparlanma.
- Türkiye’de EV pazarında %35 büyüme.
- Çin teşvik paketi Asya piyasalarında olumlu karşılandı.
Analizde: Önümüzdeki çeyrek hangi sektörler öne çıkacak?"""),
        ("Design Inspiration Weekly - Test",
         """Tasarım ilhamları:
- 2025 minimalist UI trendleri ve renk paletleri.
- Mobil onboarding’i iyileştiren 7 örnek.
- Vision Pro için tasarım rehberi notları.
Dribbble/Behance seçkisi dahildir."""),
        ("AI Research Updates - Test",
         """Araştırma özetleri:
- Yeni nesil LLM’lerde parametre optimizasyon teknikleri.
- Az veride yüksek performans RL yaklaşımı.
- Görüntü üretiminde gerçekçi ışık modelleme.
Haftanın konferans ve CFP duyuruları içeride."""),
        ("Marketing Growth Brief - Test",
         """Büyüme/pazarlama:
- TikTok alışveriş entegrasyonu ile sosyal ticaretin yükselişi.
- Google Ads’te yapay zekâ destekli bütçe optimizasyonu.
- E-posta kişiselleştirmenin dönüşüme etkisi.
Başarılı A/B test kurguları vaka çalışmalarıyla."""),
    ]
    for subj, body in samples:
        await gmail_send(to_email, subj + " [SEED]", f"{body}\n\n(This is a test newsletter)")
        await asyncio.sleep(1.5)
    return f"{len(samples)} sahte bülten gönderildi."

import time, uuid

async def summarize_gmail_and_send(target_email: str, limit=10, query=None):
    items = await fetch_gmail_messages(limit=limit, query=query)
    print(">>> BEFORE FILTER SUBJECTS:", [i.get("subject") for i in items])
    items = _filter_for_summary(items)
    print(">>> AFTER  FILTER SUBJECTS:", [i.get("subject") for i in items])

    if not items:
        return "Güncel e-posta bulunamadı."

    # 1) FULL içerikleri Newsly'ye push et
    await push_to_newsly(items)

    # 2) Özetle + sana e-posta olarak gönder
    tok = uuid.uuid4().hex[:8].upper()
    header = f"SOURCE=GMAIL_API\nSUMMARY_TOKEN={tok}\nITEMS={len(items)}\n"
    summary = header + "\n" + summarize_threads_turkish(items)
    subject = f"[GMAIL][TEST {time.strftime('%H:%M:%S')}] {len(items)} mail · {tok}"

    print(">>> SUBJECT:", subject)
    print(">>> BODY-HEAD:\n", header)

    await gmail_send(target_email, subject, summary)
    return "Özet üretildi ve e-posta gönderildi."




# email_agent.py (en alt)

if __name__ == "__main__":
    import asyncio

    async def _just_seed():
        # 1) MCP server açık olmalı: python -m backend.mcp.server
        # 2) (İlk kez ise) OAuth almış olman lazım: ensure_oauth()
        # 3) Seed gönder (SENİN adresinle değiştir)
        result = await seed_fake_newsletters("nehiru789@gmail.com")
        print(result)  # "5 sahte bülten gönderildi." gibi

    asyncio.run(_just_seed())





