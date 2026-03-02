const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8081";

export type ChatResponse = {
  answer: string;
  cypher_used: string | null;
  nodes_returned: number;
  visualization_hint: string;
};

export async function postChat(question: string): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getStats(): Promise<{
  summary: { restaurants: number; reviewers: number; communities: number; shared_reviewer_edges: number };
  top_betweenness: Array<{ name: string; betweenness: number }>;
}> {
  const res = await fetch(`${API_BASE}/api/stats`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getGraphNodes(communityId?: number, limit = 500) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (communityId != null) params.set("community_id", String(communityId));
  const res = await fetch(`${API_BASE}/api/graph/nodes?${params}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getGraphEdges(communityId?: number, limit = 1000) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (communityId != null) params.set("community_id", String(communityId));
  const res = await fetch(`${API_BASE}/api/graph/edges?${params}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getCentrality(centralityType = "betweenness", limit = 20) {
  const res = await fetch(
    `${API_BASE}/api/metrics/centrality?centrality_type=${centralityType}&limit=${limit}`
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getInfluenceTest() {
  const res = await fetch(`${API_BASE}/api/temporal/influence-test`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
