"use client";
import React, { useState } from "react";

type Candidate = {
  id?: string;
  name: string;
  sender: string;
  count30d: number;
  selected: boolean;
};

export default function NewsletterSelector() {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [isScanning, setIsScanning] = useState(false);
  const [scanError, setScanError] = useState<string | null>(null);
  const [manualSender, setManualSender] = useState("");

  async function handleScan() {
    try {
      setIsScanning(true);
      setScanError(null);

      const resp = await fetch("/api/newsletters/scan", { method: "POST" });
      if (!resp.ok) throw new Error(`Scan failed: ${resp.status}`);
      const data = await resp.json();
      setCandidates(
        (data?.candidates || []).map((c: any) => ({
          id: c.id ?? c.sender,
          name: c.name,
          sender: c.sender,
          count30d: c.count30d ?? 0,
          selected: c.selected ?? true,
        }))
      );
    } catch (e: any) {
      setScanError(e?.message ?? "Tarama sırasında bir hata oluştu");
    } finally {
      setIsScanning(false);
    }
  }

  async function handleSave() {
    const selected = candidates.filter((c) => c.selected);
    const resp = await fetch("/api/newsletters/selection", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        selected: selected.map((c) => ({
          name: c.name,
          sender: c.sender,
          count30d: c.count30d,
          selected: true,
        })),
      }),
    });
    if (!resp.ok) {
      alert("Kaydetme hatası");
      return;
    }
    alert(`${selected.length} bülten kaydedildi`);
  }

  function toggle(id?: string) {
    setCandidates((prev) =>
      prev.map((c) =>
        (c.id ?? c.sender) === (id ?? "") ? { ...c, selected: !c.selected } : c
      )
    );
  }

  function remove(id?: string) {
    setCandidates((prev) =>
      prev.filter((c) => (c.id ?? c.sender) !== (id ?? ""))
    );
  }

  function addManual() {
    const trimmed = manualSender.trim();
    if (!trimmed) return;
    if (candidates.some((c) => c.sender.toLowerCase() === trimmed.toLowerCase()))
      return;

    const base =
      trimmed.split("@")[1]?.split(".")[0]?.replace(/[._-]/g, " ") || "Bülten";
    const name = base
      .split(" ")
      .filter(Boolean)
      .map((w) => w[0].toUpperCase() + w.slice(1))
      .join(" ");

    setCandidates((prev) => [
      ...prev,
      { id: `manual-${Date.now()}`, name: `${name} (Manual)`, sender: trimmed, count30d: 0, selected: true },
    ]);
    setManualSender("");
  }

  const selectedCount = candidates.filter((c) => c.selected).length;

  return (
    <div className="mx-auto max-w-3xl p-6">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Bültenlerini Seç</h1>
          <p className="text-sm text-gray-600">
            Son 30 günde tespit edilen newsletter'lar. İstemediğin tikleri kaldır.
          </p>
        </div>
        <button
          onClick={handleScan}
          disabled={isScanning}
          className="rounded-xl border px-4 py-2 text-sm hover:bg-gray-50 disabled:opacity-60"
        >
          {isScanning ? "Taranıyor…" : "Gmail'de Tara"}
        </button>
      </div>

      {scanError && (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {scanError}
        </div>
      )}

      <div className="grid gap-3">
        {candidates.map((c) => (
          <div key={c.id ?? c.sender} className="flex items-center justify-between rounded-2xl border bg-white p-4 shadow-sm">
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={c.selected}
                onChange={() => toggle(c.id ?? c.sender)}
                className="h-5 w-5"
              />
              <div>
                <div className="font-medium">{c.name}</div>
                <div className="text-xs text-gray-500">
                  {c.sender} · Son 30 günde {c.count30d} sayı
                </div>
              </div>
            </div>
            <button onClick={() => remove(c.id ?? c.sender)} className="rounded-xl border px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50">
              Kaldır
            </button>
          </div>
        ))}
      </div>

      <div className="mt-6 rounded-2xl border bg-white p-4 shadow-sm">
        <div className="text-sm font-semibold text-gray-700">+ Bülten Ekle (Gönderen adresi)</div>
        <div className="mt-2 flex items-center gap-2">
          <input
            value={manualSender}
            onChange={(e) => setManualSender(e.target.value)}
            placeholder="newsletter@orneksite.com"
            className="flex-1 rounded-xl border px-3 py-2 outline-none focus:ring"
          />
          <button onClick={addManual} className="rounded-xl border px-3 py-2 text-sm hover:bg-gray-50">
            Ekle
          </button>
        </div>
        <p className="mt-2 text-xs text-gray-500">
          İpucu: Gönderen adresini eklediğinde sonraki sayılar otomatik tanınır.
        </p>
      </div>

      <div className="sticky bottom-0 mt-8 flex items-center justify-between rounded-2xl border bg-white p-4 shadow-lg">
        <div className="text-sm text-gray-600">
          Seçili: <span className="font-semibold text-gray-900">{selectedCount}</span> bülten
        </div>
        <button onClick={handleSave} className="rounded-xl bg-black px-4 py-2 text-white hover:opacity-90">
          Devam Et
        </button>
      </div>
    </div>
  );
}
