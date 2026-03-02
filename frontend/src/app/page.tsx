"use client";

import { BarChart3, Network, Clock } from "lucide-react";
import ChatPanel from "@/components/ChatPanel";
import GraphCanvas from "@/components/GraphCanvas";
import DashboardCards from "@/components/DashboardCards";
import TemporalSlider from "@/components/TemporalSlider";
import { useStore, type TabId } from "@/store/useStore";

const TABS: { id: TabId; label: string; icon: React.ReactNode }[] = [
  { id: "graph", label: "Graph", icon: <Network className="h-4 w-4" /> },
  { id: "dashboard", label: "Dashboard", icon: <BarChart3 className="h-4 w-4" /> },
  { id: "temporal", label: "Temporal", icon: <Clock className="h-4 w-4" /> },
];

export default function Home() {
  const { activeTab, setActiveTab } = useStore();

  return (
    <div className="flex h-screen flex-col bg-zinc-100 dark:bg-zinc-950">
      <header className="border-b border-zinc-200 bg-white px-4 py-2 dark:border-zinc-800 dark:bg-zinc-900">
        <h1 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
          Restaurant Hype GraphRAG — Philadelphia
        </h1>
      </header>
      <div className="flex flex-1 min-h-0">
        <aside className="w-[35%] min-w-[280px] shrink-0 border-r border-zinc-200 bg-zinc-50 p-2 dark:border-zinc-800 dark:bg-zinc-900">
          <ChatPanel />
        </aside>
        <main className="flex flex-1 flex-col min-w-0">
          <div className="flex border-b border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? "border-red-600 text-red-600 dark:border-red-500 dark:text-red-400"
                    : "border-transparent text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100"
                }`}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
          </div>
          <div className="flex-1 overflow-auto p-4">
            {activeTab === "graph" && (
              <div className="h-[calc(100vh-12rem)] min-h-[400px]">
                <GraphCanvas />
              </div>
            )}
            {activeTab === "dashboard" && <DashboardCards />}
            {activeTab === "temporal" && <TemporalSlider />}
          </div>
        </main>
      </div>
    </div>
  );
}
