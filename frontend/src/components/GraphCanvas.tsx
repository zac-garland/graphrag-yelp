"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Network } from "lucide-react";
import { Network as VisNetwork } from "vis-network/standalone";
import { DataSet } from "vis-data";
import { getGraphCommunities, getGraphNodes, getGraphEdges } from "@/lib/api";
import { useStore } from "@/store/useStore";

const COLOR_BY_CUISINE = [
  "#06b6d4", // cyan
  "#22c55e", // green
  "#f97316", // orange
  "#a855f7", // purple
  "#ef4444", // red
  "#3b82f6", // blue
  "#f59e0b", // amber
  "#10b981", // emerald
  "#ec4899", // pink
  "#8b5cf6", // violet
  "#14b8a6", // teal
  "#eab308", // yellow
];

function firstCuisine(categories?: string): string | null {
  if (!categories) return null;
  const first = categories.split(",")[0]?.trim();
  return first && first.length > 0 ? first : null;
}

function colorForCuisine(cuisine: string | null): string {
  if (!cuisine) return "#64748b"; // slate fallback
  let hash = 0;
  for (let i = 0; i < cuisine.length; i += 1) {
    hash = (hash * 31 + cuisine.charCodeAt(i)) >>> 0;
  }
  return COLOR_BY_CUISINE[hash % COLOR_BY_CUISINE.length] ?? "#64748b";
}

type CyRef = { current: { get: () => unknown } | null };

type CommunityOption = { community_id: number; restaurant_count: number };

export default function GraphCanvas() {
  const cyRef: CyRef = useRef(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const networkRef = useRef<unknown>(null);
  const dataRef = useRef<{ nodes: any; edges: any } | null>(null);

  type NodeRow = {
    business_id: string;
    name?: string;
    community_id?: number;
    eigenvector?: number;
    categories?: string;
  };
  type EdgeRow = { source: string; target: string; weight?: number };

  const [graphData, setGraphData] = useState<{ nodes: NodeRow[]; edges: EdgeRow[] }>({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [visReady, setVisReady] = useState(false);
  const [communities, setCommunities] = useState<CommunityOption[]>([]);
  const { communityFilter, setCommunityFilter } = useStore();

  const cuisineLegend = (() => {
    const counts = new Map<string, number>();
    for (const n of graphData.nodes) {
      const c = firstCuisine(n.categories) ?? "Unknown";
      counts.set(c, (counts.get(c) ?? 0) + 1);
    }
    const items = Array.from(counts.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 12)
      .map(([cuisine, count]) => ({
        cuisine,
        count,
        color: cuisine === "Unknown" ? "#64748b" : colorForCuisine(cuisine),
      }));
    return items;
  })();

  useEffect(() => {
    getGraphCommunities()
      .then((res) => setCommunities(res.communities ?? []))
      .catch(() => setCommunities([]));
  }, []);

  const loadGraph = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const nodesRes = await getGraphNodes(communityFilter ?? undefined, 200);
      const nodes = (nodesRes.nodes as NodeRow[]) ?? [];
      const nodeIds = nodes.map((n) => n.business_id);
      const edgesRes = await getGraphEdges(communityFilter ?? undefined, 800, nodeIds);
      const edges = (edgesRes.edges as EdgeRow[]) ?? [];
      const nodeIdSet = new Set(nodeIds);
      const validEdges = edges.filter((e) => nodeIdSet.has(e.source) && nodeIdSet.has(e.target));
      setGraphData({ nodes, edges: validEdges });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [communityFilter]);

  useEffect(() => {
    loadGraph();
  }, [loadGraph]);

  // vis-network: initialize once when container exists.
  useEffect(() => {
    if (!containerRef.current) return;
    if (networkRef.current) return;

    const nodes = new DataSet([]);
    const edges = new DataSet([]);
    dataRef.current = { nodes, edges };

    const options = {
      autoResize: true,
      interaction: {
        hover: true,
        tooltipDelay: 150,
        navigationButtons: true,
        keyboard: true,
      },
      nodes: {
        shape: "dot",
        borderWidth: 1,
        color: {
          border: "#111827",
          background: "#22c55e",
          highlight: { border: "#f59e0b", background: "#f59e0b" },
        },
        font: {
          color: "#ffffff",
          size: 12,
          face: "Arial",
          strokeWidth: 2,
          strokeColor: "rgba(0,0,0,0.65)",
        },
        scaling: { min: 6, max: 28 },
      },
      edges: {
        color: { color: "rgba(148,163,184,0.35)" },
        width: 1,
        smooth: { type: "dynamic" },
      },
      physics: {
        enabled: true,
        stabilization: { iterations: 200, fit: true },
        barnesHut: {
          gravitationalConstant: -12000,
          centralGravity: 0.12,
          springLength: 180,
          springConstant: 0.015,
          damping: 0.35,
          avoidOverlap: 0.2,
        },
      },
    } as const;

    networkRef.current = new VisNetwork(containerRef.current, dataRef.current, options);
    setVisReady(true);
  }, []);

  // Destroy network on unmount
  useEffect(() => {
    return () => {
      const net = networkRef.current as any;
      if (net?.destroy) net.destroy();
      networkRef.current = null;
      dataRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!visReady || !dataRef.current) return;

    const maxEv = Math.max(...graphData.nodes.map((n) => n.eigenvector ?? 0), 1e-9);

    const nodes = graphData.nodes.map((n) => {
      const ev = n.eigenvector ?? 0;
      const size = 8 + 24 * Math.min(1, Math.sqrt(ev / maxEv));
      const cuisine = firstCuisine(n.categories);
      const color = colorForCuisine(cuisine);
      return {
        id: n.business_id,
        label: (n.name ?? n.business_id).slice(0, 28),
        value: size,
        color: { background: color, border: "#0b1220" },
        title: cuisine ? `${n.name ?? n.business_id}\n${cuisine}` : (n.name ?? n.business_id),
      };
    });

    const edges = graphData.edges.slice(0, 1200).map((e, i) => ({
      id: `e${i}`,
      from: e.source,
      to: e.target,
      value: e.weight ?? 1,
      width: Math.max(1, Math.min(6, (e.weight ?? 1) / 3)),
    }));

    dataRef.current.nodes.clear();
    dataRef.current.edges.clear();
    dataRef.current.nodes.add(nodes);
    dataRef.current.edges.add(edges);

    const net = networkRef.current as any;
    if (net?.fit) net.fit({ animation: { duration: 500, easingFunction: "easeInOutQuad" } });
    if (net?.redraw) net.redraw();
  }, [graphData, visReady]);

  if (error) {
    return (
      <div className="flex h-full items-center justify-center rounded-lg border border-zinc-200 bg-zinc-50 p-4 dark:border-zinc-700 dark:bg-zinc-800">
        <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        <button type="button" onClick={loadGraph} className="ml-2 text-sm underline">Retry</button>
      </div>
    );
  }

  return (
    <div className="flex h-full w-full flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <label htmlFor="community-filter" className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
          Community:
        </label>
        <select
          id="community-filter"
          value={communityFilter ?? ""}
          onChange={(e) => {
            const v = e.target.value;
            setCommunityFilter(v === "" ? null : Number(v));
          }}
          className="rounded border border-zinc-300 bg-white px-2 py-1 text-sm text-zinc-900 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-100"
          disabled={loading}
        >
          <option value="">All communities</option>
          {communities.map((c) => (
            <option key={c.community_id} value={c.community_id}>
              Community {c.community_id} ({c.restaurant_count} restaurants)
            </option>
          ))}
        </select>
        <div className="ml-2 flex flex-wrap items-center gap-2">
          <span className="text-xs font-medium text-zinc-600 dark:text-zinc-400">Cuisine:</span>
          {cuisineLegend.map((item) => (
            <span
              key={item.cuisine}
              className="inline-flex items-center gap-1 rounded-full border border-zinc-200 bg-white px-2 py-0.5 text-xs text-zinc-700 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200"
              title={`${item.cuisine} (${item.count})`}
            >
              <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: item.color }} />
              <span className="max-w-[9rem] truncate">{item.cuisine}</span>
            </span>
          ))}
        </div>
        <span className="ml-auto text-xs text-zinc-500">
          nodes {graphData.nodes.length} · edges {graphData.edges.length} · vis {visReady ? "ready" : "loading"}
        </span>
      </div>
      <div className="relative min-h-0 flex-1 rounded-lg border border-zinc-200 dark:border-zinc-700">
        <div ref={containerRef} className="h-full w-full min-h-[400px]" />
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/20">
            <span className="flex items-center gap-2 rounded-md bg-zinc-900/70 px-3 py-2 text-sm text-zinc-100">
              <Network className="h-4 w-4 animate-pulse" /> Loading graph…
            </span>
          </div>
        )}
        {!loading && graphData.nodes.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center">
            <p className="text-sm text-zinc-500">No graph data. Start the API and load Neo4j.</p>
          </div>
        )}
      </div>
    </div>
  );
}
