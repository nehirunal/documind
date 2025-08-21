"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  User,
  Mail,
  Sparkles,
  BookOpen,
  Clock,
  Filter,
  X,
  ExternalLink,
  LogOut,
} from "lucide-react";


const fetcher = (url: string) => fetch(url).then(res => res.json())
const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

async function jsonFetch<T>(url: string, init?: RequestInit) {
  const res = await fetch(url, { ...init, headers: { "Content-Type": "application/json", ...(init?.headers || {}) } });
  if (!res.ok) {
    let msg = `${res.status} ${res.statusText}`;
    try { const j = await res.json(); msg = j?.error || j?.detail || msg; } catch { }
    throw new Error(msg);
  }
  return (await res.json()) as T;
}

/* ----- Tipler ----- */
type FeaturedItem = {
  id: number | string;
  title: string;
  topic: string;
  category?: string;  // etiket (Trump, OpenAI, Instagram ...)
  minutes: number;
  description: string;
  sender: string;
  date?: string;
  teaser?: string;
  long_summary?: string;
  full_summary?: string[];
  highlights?: string[];
};


export default function Home() {

  // Bilinen etiketler için renk map'i
  const BADGE_MAP: Record<string, string> = {
    general: "bg-slate-50 text-slate-700 border-slate-200",
    technology: "bg-blue-50 text-blue-700 border-blue-200",
    relationships: "bg-green-50 text-green-700 border-green-200",
    // SIK GELEBİLECEK yeni örnekler:
    trump: "bg-red-50 text-red-700 border-red-200",
    "us politics": "bg-red-50 text-red-700 border-red-200",
    openai: "bg-indigo-50 text-indigo-700 border-indigo-200",
    instagram: "bg-pink-50 text-pink-700 border-pink-200",
    tiktok: "bg-fuchsia-50 text-fuchsia-700 border-fuchsia-200",
    nvidia: "bg-emerald-50 text-emerald-700 border-emerald-200",
  };

  // Bilinmeyen etiketler için fallback renkleri
  const BADGE_FALLBACKS = [
    "bg-amber-50 text-amber-700 border-amber-200",
    "bg-cyan-50 text-cyan-700 border-cyan-200",
    "bg-lime-50 text-lime-700 border-lime-200",
    "bg-rose-50 text-rose-700 border-rose-200",
    "bg-teal-50 text-teal-700 border-teal-200",
    "bg-violet-50 text-violet-700 border-violet-200",
    "bg-sky-50 text-sky-700 border-sky-200",
  ];

  // Basit, stabil hash → renk seçer
  function hashTagToClass(key: string) {
    let h = 0;
    for (let i = 0; i < key.length; i++) h = (h * 31 + key.charCodeAt(i)) >>> 0;
    return BADGE_FALLBACKS[h % BADGE_FALLBACKS.length];
  }

  const getBadgeClass = (topic?: string) => {
    const key = (topic || "General").toLowerCase();
    return BADGE_MAP[key] ?? hashTagToClass(key);
  };

  /* ----- State ----- */
  const [email, setEmail] = useState("");
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [showSubscriptionModal, setShowSubscriptionModal] = useState(false);


  const [allNewsletters, setAllNewsletters] = useState<FeaturedItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [selectedCategory, setSelectedCategory] = useState<string>("All");
  const [openItem, setOpenItem] = useState<FeaturedItem | null>(null);

  // Profil menüsü
  const [showUserMenu, setShowUserMenu] = useState(false);
  const userBtnRef = useRef<HTMLButtonElement | null>(null);
  const userMenuRef = useRef<HTMLDivElement | null>(null);

  const [showFilters, setShowFilters] = useState<boolean>(false);



  useEffect(() => {
    const onClickOutside = (e: MouseEvent) => {
      if (!showUserMenu) return;
      const target = e.target as Node;
      if (
        userMenuRef.current &&
        !userMenuRef.current.contains(target) &&
        userBtnRef.current &&
        !userBtnRef.current.contains(target)
      ) {
        setShowUserMenu(false);
      }
    };
    window.addEventListener("mousedown", onClickOutside);
    return () => window.removeEventListener("mousedown", onClickOutside);
  }, [showUserMenu]);

  const handleLogout = () => {
    // İsteğe bağlı: auth temizliği
    try {
      localStorage.removeItem("token");
      sessionStorage.clear();
      // Eğer bir API logout u varsa burada çağırabilirsiniz
    } catch { }
    window.location.href = "/login"; // log in sayfasına yönlendir
  };

  /* ----- Backend'den çek ----- */
  useEffect(() => {
    const ctrl = new AbortController();

    const normalize = (item: any): FeaturedItem => ({
      id: item.id ?? `${item.sender ?? "unknown"}-${item.date ?? item.title ?? Math.random()}`,
      title: item.title ?? item.subject ?? "Untitled",
      topic: item.tag ?? item.topic ?? item.category ?? "General",
      minutes: Number(item.minutes ?? item.readMinutes ?? 3),
      description: item.description ?? item.teaser ?? item.snippet ?? "",
      sender: item.sender ?? item.from ?? "Unknown",
      date: item.date ?? item.published_at ?? item.created_at ?? undefined,
      teaser: item.teaser ?? undefined,
      long_summary: item.long_summary ?? undefined,
      full_summary: Array.isArray(item.full_summary)
        ? item.full_summary
        : (Array.isArray(item.summary) ? item.summary : undefined),
      highlights: Array.isArray(item.highlights) ? item.highlights : undefined,
    });

    const fetchFlow = async () => {
      try {
        setLoading(true);
        setLoadError(null);

        // 1) Featured items'ı çek
        let featured = await jsonFetch<{ items: any[] }>(`${API}/api/newsletters/featured`);
        if (!featured || !Array.isArray(featured.items)) {
          featured = { items: [] as any[] };
        }

        // 2) Backend artık her item'da tag döndürüyor => normalize içinde topic: item.tag ... zaten önde
        let items = (featured.items || []).map(normalize);

        // 3) Sırala ve state'e yaz
        items.sort(
          (a, b) => (b.date ? Date.parse(b.date) : 0) - (a.date ? Date.parse(a.date) : 0)
        );
        setAllNewsletters(items);
      } catch (err: any) {
        if (err?.name !== "AbortError") {
          console.error("fetchFlow error:", err);
          setLoadError("İçerikler yüklenemedi. Lütfen daha sonra tekrar deneyin.");
        }
      } finally {
        setLoading(false);
      }
    };

    fetchFlow();
    return () => ctrl.abort();
  }, []);

  /* ----- Filtre ----- */
  const filteredNewsletters = useMemo(() => {
    if (selectedCategory === "All") return allNewsletters;
    if (selectedCategory === "Today") {
      const today = new Date().toDateString();
      return allNewsletters.filter(n =>
        n.date && new Date(n.date).toDateString() === today
      );
    }
    return allNewsletters.filter((n) => (n.category || "General") === selectedCategory);
  }, [selectedCategory, allNewsletters]);


  // Today / Earlier gruplama
  const { todayItems, earlierItems } = useMemo(() => {
    const todayStr = new Date().toDateString();
    const t: FeaturedItem[] = [];
    const e: FeaturedItem[] = [];
    (filteredNewsletters || []).forEach((n) => {
      const isToday = n.date && new Date(n.date).toDateString() === todayStr;
      (isToday ? t : e).push(n);
    });
    return { todayItems: t, earlierItems: e };
  }, [filteredNewsletters]);



  /* ----- Email subscribe (sadece anasayfada tek) ----- */
  const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8001";

  const handleSubscribe = async () => {
    if (!email) return;
    try {
      const res = await fetch(`${BACKEND}/api/subscriptions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, tz: "Europe/Istanbul" }),
      });
      if (!res.ok) throw new Error(await res.text());
      setIsSubscribed(true);
      setTimeout(() => {
        setIsSubscribed(false);
        setShowSubscriptionModal(false);
      }, 2500);
    } catch (e) {
      alert("Abonelik kaydı başarısız: " + (e as Error).message);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-50">
      {/* Header */}
      <header className="border-b border-slate-200 bg-white/80 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-red-500 to-orange-500 rounded-xl flex items-center justify-center">
                <Sparkles className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-slate-900">
                  Newsly<span className="text-orange-500">.AI</span>
                </h1>
                <p className="text-xs text-slate-500">AI-powered newsletter insights</p>
              </div>
            </div>
            <div className="flex items-center gap-3 relative">
              <button
                onClick={() => (window.location.href = 'http://localhost:3000/newsletters')}
                className="bg-gradient-to-r from-red-500 to-orange-500 text-white px-4 py-2 rounded-lg font-medium hover:shadow-lg hover:scale-105 transition-all flex items-center gap-2"
              >
                <Mail className="w-4 h-4" />
                Get Email Scan
              </button>
              {/* Profil / Kullanıcı butonu */}
              <button
                ref={userBtnRef}
                onClick={() => setShowUserMenu((s) => !s)}
                className="p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-all"
                aria-haspopup="menu"
                aria-expanded={showUserMenu}
              >
                <User className="w-5 h-5" />
              </button>

              {/* Dropdown Menü */}
              {showUserMenu && (
                <div
                  ref={userMenuRef}
                  role="menu"
                  className="absolute right-0 top-12 w-44 bg-white border border-slate-200 rounded-xl shadow-lg overflow-hidden animate-in fade-in zoom-in duration-150"
                >
                  <button
                    onClick={handleLogout}
                    className="w-full px-3 py-2 text-left text-slate-700 hover:bg-slate-50 flex items-center gap-2"
                    role="menuitem"
                  >
                    <LogOut className="w-4 h-4" />
                    Logout
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-12">
        {/* Hero + tek subscribe */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 bg-orange-50 border border-orange-200 rounded-full px-4 py-2 text-sm font-medium text-orange-700 mb-6">
            <Sparkles className="w-4 h-4" />
            Your daily dose of smart insights
          </div>

          <h2 className="text-5xl font-bold text-slate-900 mb-4 leading-tight">
            Transform newsletters into
            <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-red-500 to-orange-500">
              key insights
            </span>
          </h2>

          <p className="text-xl text-slate-600 mb-10 max-w-2xl mx-auto">
            Get AI-powered summaries of your favorite newsletters, delivered straight to your inbox.
          </p>

          <div className="flex flex-col items-center gap-4 mb-8">
            <p className="text-slate-600">Agent on duty: delivering daily summaries to your inbox at 6pm. Interested?</p>
            <button
              onClick={() => setShowSubscriptionModal(true)}
              className="bg-gradient-to-r from-red-500 to-orange-500 text-white px-8 py-3 rounded-xl font-semibold hover:shadow-lg hover:scale-105 transition-all flex items-center gap-2"
            >
              <Mail className="w-5 h-5" />
              Subscribe for Free
            </button>
          </div>
        </div>

        {/* Featured Grid */}
        <section>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
            <div className="flex items-center gap-3">
              <BookOpen className="w-6 h-6 text-slate-700" />
              <h3 className="text-2xl font-bold text-slate-900">Featured Newsletters</h3>
              <span className="bg-slate-100 text-slate-700 text-sm px-3 py-1 rounded-full font-medium">
                {filteredNewsletters.length} {filteredNewsletters.length === 1 ? "newsletter" : "newsletters"}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-slate-500" />

              {/* Mobil: Filtreler butonu */}
              <button
                onClick={() => setShowFilters(v => !v)}
                className="md:hidden px-3 py-2 rounded-lg text-sm font-medium bg-white border border-slate-200 text-slate-600 hover:bg-slate-50 hover:border-slate-300"
              >
                {showFilters ? "Hide Filters" : "Show Filters"}
              </button>
            </div>

            {/* Mobil: açılır kapanır grid */}
          </div>


          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="bg-white border border-slate-200 rounded-2xl p-6 animate-pulse">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="h-6 w-20 bg-slate-2 00 rounded-full"></div>
                    <div className="h-4 w-16 bg-slate-200 rounded"></div>
                  </div>
                  <div className="h-6 bg-slate-200 rounded mb-3"></div>
                  <div className="space-y-2">
                    <div className="h-4 bg-slate-200 rounded"></div>
                    <div className="h-4 bg-slate-200 rounded w-3/4"></div>
                  </div>
                  <div className="flex justify-between items-center mt-4">
                    <div className="h-4 w-24 bg-slate-200 rounded"></div>
                    <div className="h-8 w-20 bg-slate-200 rounded"></div>
                  </div>
                </div>
              ))}
            </div>
          ) : loadError ? (
            <div className="text-center py-12 text-red-600">{loadError}</div>
          ) : filteredNewsletters.length === 0 ? (
            <div className="text-center py-12">
              <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <BookOpen className="w-8 h-8 text-slate-400" />
              </div>
              <h4 className="text-lg font-semibold text-slate-900 mb-2">No newsletters found</h4>
              <p className="text-slate-600">
                Try selecting a different category or check back later.
              </p>
            </div>
          ) : (
            <div className="space-y-10">
              {/* TODAY SECTION */}
              {todayItems.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-4">
                    <div className="w-2 h-6 rounded bg-emerald-500"></div>
                    <h4 className="text-3xl font-bold text-slate-900">Today</h4>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {todayItems.map((item) => (
                      <Card key={String(item.id)} item={item} onOpen={() => setOpenItem(item)} getBadgeClass={getBadgeClass} />
                    ))}
                  </div>
                </div>
              )}

              {/* EARLIER SECTION */}
              {earlierItems.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-4">
                    <div className="w-2 h-6 rounded bg-red-500"></div>
                    <h4 className="text-3xl font-bold text-slate-900">Earlier</h4>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {earlierItems.map((item) => (
                      <Card key={String(item.id)} item={item} onOpen={() => setOpenItem(item)} getBadgeClass={getBadgeClass} />
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </section>

        {/* Subscription Modal (anasayfada tek) */}
        {showSubscriptionModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
            <div className="bg-white border border-slate-200 rounded-2xl shadow-xl p-8 max-w-md w-full relative animate-in fade-in duration-300">
              <button
                onClick={() => setShowSubscriptionModal(false)}
                className="absolute right-4 top-4 text-slate-400 hover:text-slate-600 transition-colors"
              >
                <X className="w-6 h-6" />
              </button>

              <div className="flex items-center gap-3 mb-6">
                <div className="w-12 h-12 bg-gradient-to-br from-red-500 to-orange-500 rounded-xl flex items-center justify-center">
                  <Mail className="w-6 h-6 text-white" />
                </div>
                <div className="text-left">
                  <h3 className="font-semibold text-slate-900 text-lg">Stay Updated</h3>
                  <p className="text-sm text-slate-600">Get AI summaries delivered to your inbox</p>
                </div>
              </div>

              <div className="space-y-4">
                <input
                  type="email"
                  placeholder="Enter your email address"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-4 py-3 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent transition-all text-slate-900 placeholder-slate-500"
                />

                <button
                  onClick={handleSubscribe}
                  disabled={!email || isSubscribed}
                  className={`w-full py-3 px-6 rounded-xl font-semibold transition-all ${isSubscribed
                    ? "bg-green-500 text-white"
                    : "bg-gradient-to-r from-red-500 to-orange-500 text-white hover:shadow-lg hover:scale-105 disabled:opacity-50 disabled:hover:scale-100"
                    }`}
                >
                  {isSubscribed ? "✅ Subscribed!" : "Subscribe for Free"}
                </button>

                <p className="text-xs text-slate-500 text-center">Free forever. Unsubscribe anytime.</p>
              </div>
            </div>
          </div>
        )}

        {/* Detay Modal */}
        {openItem && (
          <div className="fixed inset-0 bg-black/60 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-2xl shadow-2xl max-w-3xl w-full max-h-[85vh] relative overflow-hidden">
              <div className="flex items-center justify-between p-6 border-b border-slate-200 bg-slate-50">
                <div className="flex items-center gap-3">
                  <span className={`text-xs px-3 py-1 rounded-full border font-medium ${getBadgeClass(openItem.topic)}`}>
                    {openItem.topic}
                  </span>
                  <div className="flex items-center gap-1 text-slate-500">
                    <Clock className="w-4 h-4" />
                    <span className="text-sm">{openItem.minutes} min read</span>
                  </div>
                </div>
                <button
                  onClick={() => setOpenItem(null)}
                  className="text-slate-400 hover:text-slate-600 transition-colors p-1 hover:bg-slate-200 rounded-lg"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="p-6 overflow-y-auto max-h-[calc(85vh-120px)]">
                <h3 className="text-2xl font-bold text-slate-900 mb-4 leading-tight">{openItem.title}</h3>

                <div className="flex items-center gap-2 mb-6 text-sm text-slate-600">
                  <span className="font-medium">{openItem.sender}</span>
                  <span>•</span>
                  <span>{new Date(openItem.date || Date.now()).toLocaleDateString()}</span>
                </div>

                {/* Highlights - dikkat çekici tasarım */}
                {Array.isArray(openItem.highlights) && openItem.highlights.length > 0 && (
                  <div className="mb-8">
                    <div className="flex items-center gap-3 mb-4">
                      <div className="flex items-center gap-2">
                        <div className="w-6 h-6 bg-gradient-to-br from-orange-400 to-red-500 rounded-lg flex items-center justify-center">
                          <Sparkles className="w-3.5 h-3.5 text-white" />
                        </div>
                        <h4 className="font-semibold text-slate-900">Key Insights</h4>
                      </div>
                      <div className="flex-1 h-px bg-gradient-to-r from-orange-200 to-transparent"></div>
                      <span className="text-xs text-slate-500 bg-slate-50 px-2 py-1 rounded-full">
                        {openItem.highlights.length} insights
                      </span>
                    </div>
                    <div className="grid gap-3">
                      {openItem.highlights.map((h, i) => (
                        <div key={i} className="group bg-gradient-to-r from-orange-50/50 to-red-50/30 border border-orange-100/50 rounded-xl p-4 hover:shadow-md hover:border-orange-200 transition-all duration-200">
                          <div className="flex items-start gap-3">
                            <div className="w-6 h-6 bg-gradient-to-br from-orange-400 to-red-500 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                              <span className="text-white text-xs font-bold">{i + 1}</span>
                            </div>
                            <p className="text-slate-800 font-medium leading-relaxed group-hover:text-slate-900 transition-colors">
                              {h}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Newsletter summary başlığı - geliştirilmiş */}
                <div className="flex items-center gap-3 mb-4">
                  <div className="flex items-center gap-2">
                    <div className="w-5 h-5 bg-gradient-to-br from-slate-600 to-slate-800 rounded flex items-center justify-center">
                      <BookOpen className="w-3 h-3 text-white" />
                    </div>
                    <h4 className="text-sm font-bold text-slate-700 uppercase tracking-wide">
                      Newsletter Summary
                    </h4>
                  </div>
                  <div className="flex-1 h-px bg-gradient-to-r from-slate-200 to-transparent"></div>
                </div>

                {/* Uzun özet */}
                {openItem.long_summary ? (
                  <div className="bg-gradient-to-br from-slate-50/50 to-blue-50/20 rounded-xl p-6 border border-slate-100 shadow-sm">
                    <div className="prose prose-slate max-w-none">
                      <div
                        className="text-slate-700 leading-relaxed text-base"
                        dangerouslySetInnerHTML={{
                          __html: formatNewsletterSummary(openItem.long_summary)
                        }}
                      />
                    </div>
                  </div>
                ) : openItem.full_summary?.length ? (
                  <div className="bg-gradient-to-br from-slate-50/50 to-blue-50/20 rounded-xl p-6 border border-slate-100 shadow-sm">
                    <div className="space-y-4">
                      {openItem.full_summary.map((point, i) => (
                        <div key={i} className="flex items-start gap-3 p-3 bg-white/60 rounded-lg border border-slate-100/50">
                          <div className="w-6 h-6 bg-gradient-to-br from-orange-400 to-red-500 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                            <span className="text-white text-xs font-bold">{i + 1}</span>
                          </div>
                          <p className="text-slate-700 leading-relaxed text-base font-medium">{point}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="bg-gradient-to-br from-slate-50/50 to-blue-50/20 rounded-xl p-6 border border-slate-100 shadow-sm">
                    <div className="prose prose-slate max-w-none">
                      <p className="text-slate-700 leading-relaxed text-base whitespace-pre-line">
                        {openItem.description}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </main>

      <style jsx>{`
        .line-clamp-2 {
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }
        .line-clamp-4 {
          display: -webkit-box;
          -webkit-line-clamp: 4;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }
      `}</style>
    </div>
  );
}

// Kart bileşeni küçük bir refaktör
function Card({ item, onOpen, getBadgeClass }: { item: FeaturedItem; onOpen: () => void; getBadgeClass: (t?: string) => string }) {
  return (
    <div
      onClick={onOpen}
      className="group bg-white border border-slate-200 rounded-2xl p-6 shadow-sm hover:shadow-xl hover:border-slate-300 transition-all duration-300 cursor-pointer h-96 flex flex-col"
    >
      <div className="flex items-center gap-3 mb-3">
        <span className={`text-xs px-3 py-1 rounded-full border font-medium ${getBadgeClass(item.topic)}`}>
          {item.topic}
        </span>
        <div className="flex items-center gap-1 text-slate-500">
          <Clock className="w-3 h-3" />
          <span className="text-xs">{item.minutes} min</span>
        </div>
        {item.date && (
          <div className="flex items-center gap-1 text-slate-500">
            <span className="text-xs">
              {new Date(item.date).toLocaleDateString('tr-TR', {
                day: 'numeric',
                month: 'short'
              })}
            </span>
          </div>
        )}
      </div>

      <h4 className="text-lg font-semibold text-slate-900 mb-2 group-hover:text-orange-600 transition-colors">
        <span className="line-clamp-2">{item.title}</span>
      </h4>

      <div className="flex-1 mb-4 overflow-hidden">
        {Array.isArray(item.highlights) && item.highlights.length ? (
          <div className="space-y-3">
            <div className="flex items-center gap-2 mb-3">
              <Sparkles className="w-4 h-4 text-orange-500" />
              <span className="text-xs font-semibold text-orange-600 uppercase tracking-wide">Key Insights</span>
            </div>
            <div className="space-y-2.5">
              {item.highlights.slice(0, 4).map((h, idx) => (
                <div key={idx} className="flex items-start gap-2 group">
                  <div className="w-1.5 h-1.5 rounded-full bg-gradient-to-r from-orange-400 to-red-500 mt-2 flex-shrink-0"></div>
                  <p className="text-sm text-slate-800 font-medium leading-snug group-hover:text-slate-900 transition-colors">
                    {h}
                  </p>
                </div>
              ))}
            </div>
            {item.highlights.length > 4 && (
              <div className="text-xs text-orange-600 font-medium pt-2 border-t border-orange-100">
                +{item.highlights.length - 4} more insights inside
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-2">
            <div className="flex items-center gap-2 mb-2">
              <BookOpen className="w-3.5 h-3.5 text-slate-500" />
              <span className="text-xs font-medium text-slate-500 uppercase tracking-wide">Preview</span>
            </div>
            <p className="text-sm text-slate-600 leading-relaxed">{item.description}</p>
          </div>
        )}
      </div>

      <div className="flex justify-between items-center mt-3 pt-3 border-t border-slate-100">
        <span className="text-xs text-slate-500 font-medium truncate mr-2">{item.sender}</span>
        <span className="text-xs text-orange-500 hover:text-orange-600 font-medium flex items-center gap-1 flex-shrink-0">
          Read more <ExternalLink className="w-3 h-3" />
        </span>
      </div>
    </div>
  );
}
// Bu satırı dosyanın en sonuna, Card fonksiyonundan da sonra ekle:
// Formatlanmış summary için yardımcı fonksiyon
function formatNewsletterSummary(text: string): string {
  return text
    // İlk cümleyi tab ile başlat ve büyük yap
    .replace(/^([^.]+\.)/, '<p class="mb-4"><span class="inline-block w-8"></span><span class="text-lg font-medium">$1</span></p>')
    // Cümle sonlarından sonra paragraf boşlukları ekle (büyük harfle başlayan cümleler için)
    .replace(/\. ([A-Z][^.]*\.)/g, '.</p><p class="mb-4">$1')
    // Geçiş kelimeleri vurgula
    .replace(/\b(Additionally|Furthermore|Meanwhile|However|Moreover|In addition|On the other hand),/g, '<strong class="text-slate-800">$1,</strong>')
    // Sayıları ve önemli verileri vurgula
    .replace(/\b(\d+%|\$\d+[\d,]*|\d+\.\d+|\d{4})\b/g, '<span class="font-semibold text-slate-900 bg-yellow-50 px-1 rounded">$1</span>')
    // Şirket isimlerini vurgula (büyük harfle başlayan 2+ kelime)
    .replace(/\b([A-Z][a-z]+ [A-Z][a-zA-Z]*(?:\s[A-Z][a-zA-Z]*)*)\b/g, '<span class="font-medium text-blue-700">$1</span>')
    // Lista formatları
    .replace(/\n?[-•]\s/g, '</p><div class="flex items-start gap-3 mb-3"><div class="w-2 h-2 rounded-full bg-orange-400 mt-2 flex-shrink-0"></div><p class="text-slate-700">')
    // Son paragrafı kapat
    .replace(/$/, '</p>')
    // Boş veya çift paragrafları temizle
    .replace(/<p[^>]*><\/p>/g, '')
    .replace(/(<\/p>\s*){2,}/g, '</p>');
}