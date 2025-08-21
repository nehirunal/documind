"use client";

import { useState } from "react";
import { Mail, Search, Plus, Check, X, Sparkles, Settings, BookOpen, Clock } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export default function NewsletterScan() {
  const [candidates, setCandidates] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [showAddManual, setShowAddManual] = useState(false);
  const [manualNewsletter, setManualNewsletter] = useState({ name: "", sender: "" });

  const handleScan = async () => {
    setLoading(true);
    setMessage("");
    try {
      const resp = await fetch(`${API}/api/newsletters/scan`, { method: "POST" });
      if (!resp.ok) throw new Error(`scan ${resp.status}`);
      const data = await resp.json();
      setCandidates(data.candidates || []);
    } catch (err) {
      setMessage("Tarama sırasında hata oluştu.");
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const selected = candidates.filter((c) => c.selected);
      const resp = await fetch(`${API}/api/newsletters/selection`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ selected }),
      });
      if (!resp.ok) throw new Error(`save ${resp.status}`);
      setMessage("Your selections have been saved successfully ✅");
    } catch (err) {
      setMessage("Kaydetme sırasında hata oluştu.");
    } finally {
      setSaving(false);
    }
  };

  const handleAddManual = () => {
    if (manualNewsletter.name && manualNewsletter.sender) {
      setCandidates(prev => [...prev, {
        name: manualNewsletter.name,
        sender: manualNewsletter.sender,
        count30d: 0,
        selected: true,
        manual: true
      }]);
      setManualNewsletter({ name: "", sender: "" });
      setShowAddManual(false);
    }
  };

  const selectedCount = candidates.filter(c => c.selected).length;
  const totalCount = candidates.length;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-50">
      {/* Header */}
      <div className="bg-white/80 backdrop-blur-sm border-b border-slate-200 sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-6 py-6">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-gradient-to-br from-red-500 to-orange-500 rounded-xl flex items-center justify-center">
              <Mail className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-900">Newsletter Setup</h1>
              <p className="text-slate-600">Configure your personalized newsletter preferences</p>
            </div>
          </div>
        </div>
      </div>

      <main className="max-w-6xl mx-auto px-6 py-12">
        {/* Welcome Card */}
        <div className="bg-gradient-to-r from-orange-50 to-red-50 border border-orange-200 rounded-2xl p-8 mb-12">
          <div className="flex items-start gap-4">
            <div className="w-14 h-14 bg-gradient-to-br from-red-500 to-orange-500 rounded-xl flex items-center justify-center flex-shrink-0">
              <Sparkles className="w-7 h-7 text-white" />
            </div>
            <div className="flex-1">
              <h2 className="text-2xl font-bold text-slate-900 mb-3">
                Welcome to Newsly.AI! 🎉
              </h2>
              <p className="text-slate-700 mb-4 leading-relaxed">
                Let's set up your personalized newsletter experience. We'll scan your Gmail to find newsletters 
                you're subscribed to, and you can choose which ones you'd like to receive AI-powered summaries for.
              </p>
              <div className="flex flex-wrap gap-2 text-sm">
                <span className="bg-white/60 text-slate-700 px-3 py-1 rounded-full border border-orange-200">
                  ✨ AI-powered summaries
                </span>
                <span className="bg-white/60 text-slate-700 px-3 py-1 rounded-full border border-orange-200">
                  📧 Gmail integration
                </span>
                <span className="bg-white/60 text-slate-700 px-3 py-1 rounded-full border border-orange-200">
                  🎯 Personalized content
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Scan Section */}
        <div className="bg-white border border-slate-200 rounded-2xl p-8 mb-8 shadow-sm">
          <div className="text-center mb-8">
            <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Search className="w-8 h-8 text-slate-600" />
            </div>
            <h3 className="text-xl font-semibold text-slate-900 mb-2">Scan Your Gmail</h3>
            <p className="text-slate-600 max-w-md mx-auto">
              We'll analyze your email to find newsletter subscriptions from the last 30 days.
            </p>
          </div>

          <div className="flex justify-center">
            <button
              onClick={handleScan}
              disabled={loading}
              className={`px-8 py-4 rounded-xl font-semibold transition-all flex items-center gap-3 ${
                loading
                  ? "bg-slate-100 text-slate-500 cursor-not-allowed"
                  : "bg-gradient-to-r from-red-500 to-orange-500 text-white hover:shadow-lg hover:scale-105"
              }`}
            >
              {loading ? (
                <>
                  <div className="w-5 h-5 border-2 border-slate-400 border-t-transparent rounded-full animate-spin" />
                  Scanning Gmail...
                </>
              ) : (
                <>
                  <Search className="w-5 h-5" />
                  Start Gmail Scan
                </>
              )}
            </button>
          </div>
        </div>

        {/* Results Section */}
        {candidates.length > 0 && (
          <div className="bg-white border border-slate-200 rounded-2xl p-8 shadow-sm">
            {/* Results Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
              <div className="flex items-center gap-3">
                <BookOpen className="w-6 h-6 text-slate-700" />
                <div>
                  <h3 className="text-xl font-semibold text-slate-900">Found Newsletters</h3>
                  <p className="text-sm text-slate-600">
                    {selectedCount} of {totalCount} newsletters selected
                  </p>
                </div>
              </div>
              
              <button
                onClick={() => setShowAddManual(!showAddManual)}
                className="flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl transition-all font-medium"
              >
                <Plus className="w-4 h-4" />
                Add Manual
              </button>
            </div>

            {/* Manual Add Form */}
            {showAddManual && (
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-6 mb-6">
                <h4 className="font-semibold text-slate-900 mb-4">Add Newsletter Manually</h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <input
                    type="text"
                    placeholder="Newsletter name (e.g., Tech Weekly)"
                    value={manualNewsletter.name}
                    onChange={(e) => setManualNewsletter(prev => ({ ...prev, name: e.target.value }))}
                    className="px-4 py-3 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                  />
                  <input
                    type="email"
                    placeholder="Sender email (e.g., hello@newsletter.com)"
                    value={manualNewsletter.sender}
                    onChange={(e) => setManualNewsletter(prev => ({ ...prev, sender: e.target.value }))}
                    className="px-4 py-3 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                  />
                </div>
                <div className="flex gap-3 mt-4">
                  <button
                    onClick={handleAddManual}
                    disabled={!manualNewsletter.name || !manualNewsletter.sender}
                    className="px-4 py-2 bg-green-500 hover:bg-green-600 disabled:bg-slate-300 text-white rounded-lg font-medium transition-all disabled:cursor-not-allowed"
                  >
                    Add Newsletter
                  </button>
                  <button
                    onClick={() => {
                      setShowAddManual(false);
                      setManualNewsletter({ name: "", sender: "" });
                    }}
                    className="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 rounded-lg font-medium transition-all"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}

            {/* Progress Bar */}
            <div className="mb-6">
              <div className="flex justify-between text-sm text-slate-600 mb-2">
                <span>Selected newsletters</span>
                <span>{selectedCount}/{totalCount}</span>
              </div>
              <div className="w-full bg-slate-200 rounded-full h-2">
                <div 
                  className="bg-gradient-to-r from-red-500 to-orange-500 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${totalCount > 0 ? (selectedCount / totalCount) * 100 : 0}%` }}
                ></div>
              </div>
            </div>

            {/* Newsletter Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
              {candidates.map((c, idx) => (
                <div 
                  key={idx} 
                  className={`p-5 border-2 rounded-xl transition-all cursor-pointer hover:shadow-md ${
                    c.selected 
                      ? "border-orange-200 bg-orange-50" 
                      : "border-slate-200 bg-white hover:border-slate-300"
                  }`}
                  onClick={() =>
                    setCandidates(prev =>
                      prev.map((item, i) => i === idx ? { ...item, selected: !item.selected } : item)
                    )
                  }
                >
                  <div className="flex items-start gap-3">
                    <div className={`w-6 h-6 rounded-lg border-2 flex items-center justify-center flex-shrink-0 transition-all ${
                      c.selected 
                        ? "bg-gradient-to-br from-red-500 to-orange-500 border-orange-500" 
                        : "border-slate-300 bg-white"
                    }`}>
                      {c.selected && <Check className="w-4 h-4 text-white" />}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h4 className="font-semibold text-slate-900 truncate">
                          {c.name || c.sender}
                        </h4>
                        {c.manual && (
                          <span className="bg-blue-100 text-blue-700 text-xs px-2 py-0.5 rounded-full font-medium">
                            Manual
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-slate-600 truncate">{c.sender}</p>
                      <div className="flex items-center gap-1 mt-2">
                        <Clock className="w-3 h-3 text-slate-400" />
                        <span className="text-xs text-slate-500">
                          {c.count30d ?? 0} emails in 30 days
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Action Buttons */}
            <div className="flex flex-col sm:flex-row gap-4 items-center justify-between pt-6 border-t border-slate-200">
              <div className="text-sm text-slate-600">
                {selectedCount > 0 
                  ? `${selectedCount} newsletter${selectedCount > 1 ? 's' : ''} selected for AI summaries`
                  : "No newsletters selected"
                }
              </div>
              
              <div className="flex gap-3">
                <button
                  onClick={() => setCandidates(prev => prev.map(c => ({ ...c, selected: false })))}
                  className="px-4 py-2 text-slate-600 hover:text-slate-800 font-medium transition-all"
                >
                  Deselect All
                </button>
                <button
                  onClick={() => setCandidates(prev => prev.map(c => ({ ...c, selected: true })))}
                  className="px-4 py-2 text-slate-600 hover:text-slate-800 font-medium transition-all"
                >
                  Select All
                </button>
                <button
                  onClick={handleSave}
                  disabled={saving || selectedCount === 0}
                  className={`px-8 py-3 rounded-xl font-semibold transition-all flex items-center gap-2 ${
                    saving || selectedCount === 0
                      ? "bg-slate-200 text-slate-500 cursor-not-allowed"
                      : "bg-gradient-to-r from-red-500 to-orange-500 text-white hover:shadow-lg hover:scale-105"
                  }`}
                >
                  {saving ? (
                    <>
                      <div className="w-4 h-4 border-2 border-slate-400 border-t-transparent rounded-full animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Settings className="w-4 h-4" />
                      Save Preferences
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Message Display */}
        {message && (
          <div className={`mt-6 p-4 rounded-xl border ${
            message.includes("✅") 
              ? "bg-green-50 border-green-200 text-green-800" 
              : "bg-red-50 border-red-200 text-red-800"
          }`}>
            <div className="flex items-center gap-2">
              {message.includes("✅") ? (
                <Check className="w-5 h-5 text-green-600" />
              ) : (
                <X className="w-5 h-5 text-red-600" />
              )}
              <span className="font-medium">{message}</span>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}