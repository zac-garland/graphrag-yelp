"use client";

import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip } from "recharts";
import { getStats, getCentrality } from "@/lib/api";

type Stats = {
  summary: { restaurants: number; reviewers: number; communities: number; shared_reviewer_edges: number };
  top_betweenness: Array<{ name: string; betweenness: number }>;
};

export default function DashboardCards() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [centrality, setCentrality] = useState<Array<{ name: string; value: number }>>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getStats()
      .then(setStats)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
    getCentrality("betweenness", 15)
      .then((r) => setCentrality((r.rankings as Array<{ name: string; value: number }>) ?? []))
      .catch(() => {});
  }, []);

  if (error) {
    return (
      <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-4 dark:border-zinc-700 dark:bg-zinc-800">
        <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Card label="Restaurants" value={stats?.summary.restaurants ?? "—"} />
        <Card label="Reviewers" value={stats?.summary.reviewers ?? "—"} />
        <Card label="Communities" value={stats?.summary.communities ?? "—"} />
        <Card label="Edges" value={stats?.summary.shared_reviewer_edges ?? "—"} />
      </div>
      <div className="rounded-lg border border-zinc-200 bg-white p-3 dark:border-zinc-700 dark:bg-zinc-900">
        <h3 className="mb-2 text-sm font-semibold text-zinc-800 dark:text-zinc-100">Top betweenness (bridge restaurants)</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={centrality} margin={{ top: 5, right: 5, left: 5, bottom: 60 }}>
              <XAxis dataKey="name" tick={{ fontSize: 10 }} angle={-45} textAnchor="end" interval={0} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip formatter={(v: number | undefined) => (v != null ? v.toExponential(2) : "")} />
              <Bar dataKey="value" fill="#e11d48" name="Betweenness" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
      {stats?.top_betweenness && stats.top_betweenness.length > 0 && (
        <div className="rounded-lg border border-zinc-200 bg-white p-3 dark:border-zinc-700 dark:bg-zinc-900">
          <h3 className="mb-2 text-sm font-semibold text-zinc-800 dark:text-zinc-100">Top 5 bridges</h3>
          <ul className="space-y-1 text-sm text-zinc-600 dark:text-zinc-300">
            {stats.top_betweenness.map((r, i) => (
              <li key={i}>{r.name} — {typeof r.betweenness === "number" ? r.betweenness.toExponential(2) : r.betweenness}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function Card({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-3 dark:border-zinc-700 dark:bg-zinc-900">
      <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">{label}</p>
      <p className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">{value}</p>
    </div>
  );
}
