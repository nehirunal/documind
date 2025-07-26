"use client";

import { useState } from "react";

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [summary, setSummary] = useState("");
  const [loading, setLoading] = useState(false);

  const handleUpload = async () => {
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    setLoading(true);
    try {
      const response = await fetch("http://localhost:8000/summarize", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();
      setSummary(data.summary);
    } catch (err) {
      console.error("Özetleme hatası:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-gray-100 flex flex-col items-center p-6">
      <h1 className="text-4xl font-bold mb-6 text-indigo-600">DocuMind</h1>

      <div className="bg-white p-6 rounded-2xl shadow-md w-full max-w-xl flex flex-col gap-4">
        <label className="inline-block">
          <span className="bg-indigo-600 text-white px-4 py-2 rounded cursor-pointer hover:bg-indigo-700 transition">
            Dosya Seç
          </span>
          <input
            type="file"
            accept=".pdf"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="hidden"
          />
        </label>
        <p
          className={`text-xs ml-1 ${
            file ? "text-black font-semibold" : "text-gray-400"
          }`}
        >
          {file ? file.name : "Dosya seçilmedi"}
        </p>



        <button
          onClick={handleUpload}
          disabled={loading || !file}
          className="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700 transition"
        >
          {loading ? "Özetleniyor..." : "📌 Özetle"}
        </button>

        {summary && (
          <div className="mt-4">
            <h2 className="text-lg font-semibold mb-2">📝 Özet</h2>
            <p className="whitespace-pre-wrap bg-gray-50 p-4 rounded-md">
              {summary}
            </p>
          </div>
        )}
      </div>

      {/* Chatbot UI - Küçültülmüş versiyon */}
      <div className="bg-white w-full max-w-md mt-10 p-4 rounded-xl shadow-sm border border-gray-200">
        <h2 className="text-md font-semibold text-gray-700 mb-1">
          💬 DocuMind Chatbot
        </h2>
        <div className="h-24 border rounded-md p-3 text-gray-400 flex items-center justify-center text-sm italic">
          Belgeyle ilgili sorularınızı yakında buraya yazabileceksiniz...
        </div>
      </div>
    </main>
  );
}
