"use client";

import { useState } from "react";

export default function Home() {
  const [email, setEmail] = useState("");
  const [summary, setSummary] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [chatQuestion, setChatQuestion] = useState("");
  const [chatAnswer, setChatAnswer] = useState("");
  const [showSubscription, setShowSubscription] = useState(false);

  const handleFileSummary = async () => {
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    setLoading(true);
    try {
      const res = await fetch("http://localhost:8000/summarize", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      setSummary(data.summary);
    } catch {
      alert("Özetleme hatası.");
    } finally {
      setLoading(false);
    }
  };

  const handleUrlSummary = async () => {
    if (!url) return;
    const formData = new FormData();
    formData.append("url", url);
    setLoading(true);
    try {
      const res = await fetch("http://localhost:8000/summarize-url", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      setSummary(data.summary);
    } catch {
      alert("URL özeti alınamadı.");
    } finally {
      setLoading(false);
    }
  };

  const handleChat = async () => {
    if (!file || !chatQuestion) return;
    const formData = new FormData();
    formData.append("file", file);
    formData.append("question", chatQuestion);
    setLoading(true);
    try {
      const res = await fetch("http://localhost:8000/chat-with-pdf", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      setChatAnswer(data.answer);
    } catch {
      alert("Chatbot cevabı alınamadı.");
    } finally {
      setLoading(false);
    }
  };

  const handleNewsSubscription = async () => {
    if (!email) return;
    const formData = new FormData();
    formData.append("email", email);
    try {
      const res = await fetch("http://localhost:8000/subscribe-news", {
        method: "POST",
        body: formData,
      });
      if (res.ok) alert("✔️ Abonelik başarılı!");
      else alert("Abonelik başarısız.");
    } catch {
      alert("Sunucu hatası.");
    }
  };

  return (
    <main className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-b from-white to-gray-100 px-4 py-10">
      <div className="w-full max-w-4xl text-center">
        <h1 className="text-5xl font-bold bg-gradient-to-r from-purple-600 to-pink-600 text-transparent bg-clip-text mb-2">
          Newsly
        </h1>
        <p className="text-sm text-gray-500 mb-6">newsletter AI</p>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 mb-8">
          <button
            onClick={handleFileSummary}
            className="p-4 rounded-xl bg-white shadow hover:shadow-md text-sm font-medium"
          >
            📑 Dosya Özeti
          </button>
          <button
            onClick={handleUrlSummary}
            className="p-4 rounded-xl bg-white shadow hover:shadow-md text-sm font-medium"
          >
            🔗 URL'den Özet
          </button>
          <button
            onClick={() => setShowSubscription(true)}
            className="p-4 rounded-xl bg-white shadow hover:shadow-md text-sm font-medium"
          >
            📰 Günlük Haber Özeti
          </button>
        </div>

        <div className="bg-white p-6 rounded-xl shadow text-left mb-8 relative">
  <h2 className="text-xl font-semibold text-gray-800 mb-4">💬 Chatbot</h2>
  <div className="relative">
    <textarea
      value={chatQuestion}
      onChange={(e) => setChatQuestion(e.target.value)}
      placeholder="Dosyaya sormak istediğiniz soruyu yazın..."
      className="w-full border border-gray-300 rounded-md p-3 text-sm pr-10 pl-10"
      rows={5}
    />

    {/* Gönder (Ok ikonu) */}
    <button
      onClick={handleChat}
      className="absolute right-3 bottom-3 text-purple-600 hover:text-purple-800 text-xl"
      title="Soruyu Gönder"
    >
      ➤
    </button>

    {/* Dosya Yükleme (Artı ikonu) */}
    <label
      htmlFor="chat-file-upload"
      className="absolute left-3 bottom-3 text-gray-500 hover:text-black text-xl cursor-pointer"
      title="Dosya Yükle"
    >
      ＋
      <input
        id="chat-file-upload"
        type="file"
        className="hidden"
        onChange={(e) => setFile(e.target.files?.[0] || null)}
      />
    </label>
  </div>

  {/* Dosya adı gösterimi */}
  {file && (
    <p className="text-xs text-gray-500 mt-2">Yüklenen dosya: {file.name}</p>
  )}

  {loading && <p className="text-sm text-gray-500 mt-2">Yanıt bekleniyor...</p>}
  {chatAnswer && (
    <div className="bg-gray-50 border border-gray-200 p-4 mt-4 rounded-md">
      <p className="text-sm text-gray-800 whitespace-pre-wrap">{chatAnswer}</p>
    </div>
  )}
</div>



        {/* Özet */}
        {summary && (
          <div className="bg-white p-6 rounded-xl shadow text-left mb-8">
            <h2 className="text-xl font-semibold mb-2 text-gray-700">📝 Özet</h2>
            <p className="text-sm text-gray-700 whitespace-pre-wrap">{summary}</p>
          </div>
        )}

        {/* Abonelik Formu */}
        {showSubscription && (
          <div className="mt-4 flex flex-col sm:flex-row items-center gap-2 justify-center">
            <input
              type="email"
              placeholder="E-posta adresiniz"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="border border-gray-300 px-4 py-2 rounded-md w-full sm:w-80"
            />
            <button
              onClick={handleNewsSubscription}
              className="bg-pink-500 text-white px-5 py-2 rounded-md hover:bg-pink-600 transition"
            >
              Abone Ol
            </button>
          </div>
        )}
      </div>
    </main>
  );
}
