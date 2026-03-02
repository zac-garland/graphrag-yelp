import { create } from "zustand";

export type TabId = "graph" | "dashboard" | "temporal";

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  cypher?: string | null;
  vizHint?: string;
};

type AppState = {
  activeTab: TabId;
  setActiveTab: (tab: TabId) => void;
  chatHistory: ChatMessage[];
  addMessage: (msg: ChatMessage) => void;
  clearChat: () => void;
  selectedNodes: string[];
  setSelectedNodes: (ids: string[]) => void;
  communityFilter: number | null;
  setCommunityFilter: (id: number | null) => void;
  timeWindow: [string, string] | null;
  setTimeWindow: (w: [string, string] | null) => void;
};

export const useStore = create<AppState>((set) => ({
  activeTab: "graph",
  setActiveTab: (activeTab) => set({ activeTab }),
  chatHistory: [],
  addMessage: (msg) => set((s) => ({ chatHistory: [...s.chatHistory, msg] })),
  clearChat: () => set({ chatHistory: [] }),
  selectedNodes: [],
  setSelectedNodes: (selectedNodes) => set({ selectedNodes }),
  communityFilter: null,
  setCommunityFilter: (communityFilter) => set({ communityFilter }),
  timeWindow: null,
  setTimeWindow: (timeWindow) => set({ timeWindow }),
}));
