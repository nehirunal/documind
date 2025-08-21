import os
from openai import OpenAI

def generate_bullet_summary(text: str, bullets: int = 3):
    """
    Temiz metinden 3 maddelik kısa özet çıkarır.
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    prompt = f"""
    Metni oku ve 3 maddelik kısa bir özet çıkar:
    - Her madde 2 cümle olsun.
    - Gereksiz detay, tarih, URL olmasın.
    
    Metin:
    {text}
    """

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200
    )

    bullets = resp.choices[0].message.content.strip().split("\n")
    return [b.strip("-• ") for b in bullets if b.strip()]
