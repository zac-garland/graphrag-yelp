"use client";

import { useState } from "react";
import { MessageSquare, Send, ChevronDown, ChevronRight, Trash2 } from "lucide-react";
import { postChat } from "@/lib/api";
import { useStore, type ChatMessage } from "@/store/useStore";

const STARTER_QUESTIONS = [
  "Top 5 restaurants by betweenness centrality?",
  "Which restaurants share the most reviewers with Reading Terminal Market?",
  "Restaurants in community 0?",
  "Top elite reviewers by review count?",
  "Show me the highest k-core restaurants.",
];

export default function ChatPanel() {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [showCypher, setShowCypher] = useState<Record<string, boolean>>({});
  const { chatHistory, addMessage, clearChat, setActiveTab } = useStore();

  async function handleSend() {
    const q = input.trim();
    if (!q || loading) return;
    setInput("");
    addMessage({ id: crypto.randomUUID(), role: "user", content: q });
    setLoading(true);
    try {
      const res = await postChat(q);
      addMessage({
        id: crypto.randomUUID(),
        role: "assistant",
        content: res.answer,
        cypher: res.cypher_used ?? undefined,
        vizHint: res.visualization_hint,
      });
      if (res.visualization_hint && res.visualization_hint !== "table") {
        if (res.visualization_hint === "network_subgraph") setActiveTab("graph");
        else if (res.visualization_hint === "bar_chart") setActiveTab("dashboard");
        else if (res.visualization_hint === "timeline") setActiveTab("temporal");
      }
    } catch (e) {
      addMessage({
        id: crypto.randomUUID(),
        role: "assistant",
        content: `Error: ${e instanceof Error ? e.message : String(e)}`,
      });
    } finally {
      setLoading(false);
    }
  }

  function toggleCypher(id: string) {
    setShowCypher((s) => ({ ...s, [id]: !s[id] }));
  }

  return (
    <div className="flex h-full flex-col rounded-lg border border-zinc-200 bg-white dark:border-zinc-700 dark:bg-zinc-900">
      <div className="flex items-center justify-between border-b border-zinc-200 px-3 py-2 dark:border-zinc-700">
        <span className="flex items-center gap-2 font-medium text-zinc-800 dark:text-zinc-100">
          <MessageSquare className="h-4 w-4" /> Chat
        </span>
        <button
          type="button"
          onClick={clearChat}
          className="rounded p-1 text-zinc-500 hover:bg-zinc-100 hover:text-zinc-700 dark:hover:bg-zinc-700 dark:hover:text-zinc-300"
          title="Clear chat"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {chatHistory.length === 0 && (
          <div className="space-y-2">
            <p className="text-sm text-zinc-500 dark:text-zinc-400">Ask about Philadelphia restaurants, reviewers, or the graph.</p>
            <div className="flex flex-wrap gap-2">
              {STARTER_QUESTIONS.map((q) => (
                <button
                  key={q}
                  type="button"
                  onClick={() => setInput(q)}
                  className="rounded-full bg-red-50 px-3 py-1.5 text-left text-xs font-medium text-red-800 hover:bg-red-100 dark:bg-red-900/30 dark:text-red-200 dark:hover:bg-red-900/50"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}
        {chatHistory.map((m) => (
          <MessageBubble key={m.id} message={m} showCypher={showCypher[m.id]} onToggleCypher={() => toggleCypher(m.id)} />
        ))}
        {loading && (
          <div className="flex items-center gap-2 text-sm text-zinc-500">
            <span className="h-2 w-2 animate-pulse rounded-full bg-red-500" /> Thinking…
          </div>
        )}
      </div>
      <div className="border-t border-zinc-200 p-2 dark:border-zinc-700">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
            placeholder="Ask a question…"
            className="flex-1 rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm outline-none focus:border-red-500 focus:ring-1 focus:ring-red-500 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-100"
            disabled={loading}
          />
          <button
            type="button"
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="rounded-lg bg-red-600 px-4 py-2 text-white hover:bg-red-700 disabled:opacity-50"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

function MessageBubble({
  message,
  showCypher,
  onToggleCypher,
}: {
  message: ChatMessage;
  showCypher: boolean;
  onToggleCypher: () => void;
}) {
  const isUser = message.role === "user";
  return (
    <div className={isUser ? "flex justify-end" : ""}>
      <div
        className={`max-w-[90%] rounded-lg px-3 py-2 text-sm ${
          isUser
            ? "bg-red-600 text-white"
            : "bg-zinc-100 text-zinc-800 dark:bg-zinc-700 dark:text-zinc-200"
        }`}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
        {!isUser && message.cypher && (
          <div className="mt-2 border-t border-zinc-200 pt-2 dark:border-zinc-600">
            <button
              type="button"
              onClick={onToggleCypher}
              className="flex items-center gap-1 text-xs font-medium text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300"
            >
              {showCypher ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
              Show Cypher
            </button>
            {showCypher && (
              <pre className="mt-1 overflow-x-auto rounded bg-zinc-800 p-2 text-xs text-zinc-200">
                {message.cypher}
              </pre>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
