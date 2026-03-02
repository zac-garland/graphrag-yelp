"use client";

import { useEffect, useState } from "react";
import { getInfluenceTest } from "@/lib/api";

export default function TemporalSlider() {
  const [influence, setInfluence] = useState<{
    friend_jaccard?: number;
    random_jaccard?: number;
    ratio?: number;
    n_friend_pairs?: number;
    n_random_pairs?: number;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getInfluenceTest()
      .then(setInfluence)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
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
      <h3 className="text-sm font-semibold text-zinc-800 dark:text-zinc-100">Homophily vs influence (Jaccard)</h3>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <div className="rounded-lg border border-zinc-200 bg-white p-3 dark:border-zinc-700 dark:bg-zinc-900">
          <p className="text-xs text-zinc-500 dark:text-zinc-400">Friend pairs Jaccard</p>
          <p className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
            {influence?.friend_jaccard != null ? influence.friend_jaccard.toFixed(4) : "—"}
          </p>
        </div>
        <div className="rounded-lg border border-zinc-200 bg-white p-3 dark:border-zinc-700 dark:bg-zinc-900">
          <p className="text-xs text-zinc-500 dark:text-zinc-400">Random pairs Jaccard</p>
          <p className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
            {influence?.random_jaccard != null ? influence.random_jaccard.toExponential(2) : "—"}
          </p>
        </div>
        <div className="rounded-lg border border-zinc-200 bg-white p-3 dark:border-zinc-700 dark:bg-zinc-900">
          <p className="text-xs text-zinc-500 dark:text-zinc-400">Ratio (friend / random)</p>
          <p className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
            {influence?.ratio != null ? Math.round(influence.ratio) : "—"}
          </p>
        </div>
      </div>
      <p className="text-xs text-zinc-500 dark:text-zinc-400">
        Time-range and hype event animation can be wired to /api/temporal/growth/ and hype_events data in a later iteration.
      </p>
    </div>
  );
}
