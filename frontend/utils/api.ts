export const API =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export async function fetchFeatured() {
  const r = await fetch(`${API}/api/newsletters/featured`, {
    // Next.js CSR, cache istemiyoruz
    method: "GET",
  });
  if (!r.ok) throw new Error(`featured ${r.status}`);
  const data = await r.json();
  return (data?.items ?? []) as {
    id: number;
    title: string;
    topic: string;
    minutes: number;
    description: string;
    sender: string;
  }[];
}
