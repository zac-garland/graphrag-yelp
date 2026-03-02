"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { Network } from "lucide-react";
import { getGraphNodes, getGraphEdges } from "@/lib/api";
import { useStore } from "@/store/useStore";

const CytoscapeComponent = dynamic(() => import("react-cytoscapejs"), { ssr: false });

const COLOR_BY_COMMUNITY = [
  "#e11d48", "#2563eb", "#16a34a", "#ca8a04", "#9333ea",
  "#0d9488", "#dc2626", "#4f46e5", "#059669", "#b45309",
];

type CyRef = { current: { get: () => unknown } | null };

export default function GraphCanvas() {
  const cyRef: CyRef = useRef(null);
  type CyElement = { data: Record<string, unknown>; classes?: string };
  const [elements, setElements] = useState<{ nodes: CyElement[]; edges: CyElement[] }>({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { communityFilter } = useStore();

  const loadGraph = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [nodesRes, edgesRes] = await Promise.all([
        getGraphNodes(communityFilter ?? undefined, 400),
        getGraphEdges(communityFilter ?? undefined, 800),
      ]);
      const nodes = (nodesRes.nodes as Array<Record<string, unknown>>) ?? [];
      const edges = (edgesRes.edges as Array<{ source: string; target: string; weight?: number }>) ?? [];
      const nodeIds = new Set(nodes.map((n) => n.business_id as string));
      const validEdges = edges.filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target));
      const maxEv = Math.max(...nodes.map((n) => (n.eigenvector as number) ?? 0), 1e-9);
      setElements({
        nodes: nodes.map((n) => {
          const ev = (n.eigenvector as number) ?? 0;
          const size = 5 + 15 * Math.min(1, Math.sqrt(ev / maxEv));
          return {
            data: {
              id: n.business_id as string,
              label: ((n.name as string) ?? (n.business_id as string)).slice(0, 25),
              community_id: (n.community_id as number) ?? 0,
              size,
            },
            classes: `comm-${(n.community_id as number) ?? 0}`,
          };
        }),
        edges: validEdges.slice(0, 600).map((e, i) => ({
          data: { id: `e${i}`, source: e.source, target: e.target, weight: e.weight ?? 1 },
        })),
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [communityFilter]);

  useEffect(() => {
    loadGraph();
  }, [loadGraph]);

  const stylesheet: Array<{ selector: string; style: Record<string, unknown> }> = [
    { selector: "node", style: { label: "data(label)", "text-valign": "bottom", "text-halign": "center", "font-size": "8px", width: "data(size)", height: "data(size)" } },
    { selector: "edge", style: { width: 0.5, "line-color": "#94a3b8", opacity: 0.6 } },
  ];
  COLOR_BY_COMMUNITY.forEach((color, i) => {
    stylesheet.push({
      selector: `.comm-${i}`,
      style: { "background-color": color },
    });
  });

  const layout = { name: "cose", animate: false, nodeDimensionsIncludeLabels: false };

  if (error) {
    return (
      <div className="flex h-full items-center justify-center rounded-lg border border-zinc-200 bg-zinc-50 p-4 dark:border-zinc-700 dark:bg-zinc-800">
        <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        <button type="button" onClick={loadGraph} className="ml-2 text-sm underline">Retry</button>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center rounded-lg border border-zinc-200 bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-800">
        <span className="flex items-center gap-2 text-zinc-500">
          <Network className="h-5 w-5 animate-pulse" /> Loading graph…
        </span>
      </div>
    );
  }

  const cyElements: CyElement[] = [...elements.nodes, ...elements.edges];
  if (cyElements.length === 0) {
    return (
      <div className="flex h-full items-center justify-center rounded-lg border border-zinc-200 bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-800">
        <p className="text-sm text-zinc-500">No graph data. Start the API and load Neo4j.</p>
      </div>
    );
  }

  return (
    <div className="h-full w-full rounded-lg border border-zinc-200 dark:border-zinc-700">
      <CytoscapeComponent
        elements={cyElements}
        style={{ width: "100%", height: "100%", minHeight: "400px" }}
        stylesheet={stylesheet}
        layout={layout}
      />
    </div>
  );
}
