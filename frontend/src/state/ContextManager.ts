function uuidv4(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return (crypto as any).randomUUID();
  }
  // Fallback RFC4122 v4-ish
  const rnd = (len: number) => Array.from({ length: len }, () => Math.floor(Math.random() * 16).toString(16)).join("");
  return `${rnd(8)}-${rnd(4)}-4${rnd(3)}-${((8 + Math.floor(Math.random() * 4)).toString(16))}${rnd(3)}-${rnd(12)}`;
}

export type ChatRole = "user" | "ai";

export interface PersistedMessage {
  id: string;
  type: ChatRole;
  content: string;
  timestamp: string; // ISO string for persistence
}

export interface ConversationState {
  sessionId: string;
  metric: string;
  messages: PersistedMessage[];
  createdAt: string;
  updatedAt: string;
}

const STORAGE_KEY = "hom.chat.sessions.v1";

type SessionIndex = Record<string, ConversationState>; // key: metric

function safeParse<T>(text: string | null): T | null {
  if (!text) return null;
  try {
    return JSON.parse(text) as T;
  } catch {
    return null;
  }
}

function loadIndex(): SessionIndex {
  const raw = typeof window !== "undefined" ? window.localStorage.getItem(STORAGE_KEY) : null;
  const obj = safeParse<SessionIndex>(raw);
  return obj || {};
}

function saveIndex(index: SessionIndex): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(index));
  } catch {
    // ignore quota or storage errors
  }
}

export function getOrCreateSession(metric: string): ConversationState {
  const nowIso = new Date().toISOString();
  const index = loadIndex();
  const existing = index[metric];
  if (existing) {
    return existing;
  }
  const state: ConversationState = {
    sessionId: uuidv4(),
    metric,
    messages: [],
    createdAt: nowIso,
    updatedAt: nowIso,
  };
  index[metric] = state;
  saveIndex(index);
  return state;
}

export function appendMessage(metric: string, message: Omit<PersistedMessage, "id" | "timestamp"> & { id?: string; timestamp?: string }): ConversationState {
  const index = loadIndex();
  const state = index[metric] || getOrCreateSession(metric);
  const msg: PersistedMessage = {
    id: message.id || String(Date.now()),
    type: message.type,
    content: message.content,
    timestamp: message.timestamp || new Date().toISOString(),
  };
  const next: ConversationState = {
    ...state,
    messages: [...state.messages, msg],
    updatedAt: new Date().toISOString(),
  };
  index[metric] = next;
  saveIndex(index);
  return next;
}

export function updateMessage(metric: string, id: string, updater: (curr: PersistedMessage) => PersistedMessage): ConversationState {
  const index = loadIndex();
  const state = index[metric] || getOrCreateSession(metric);
  const nextMessages = state.messages.map((m) => (m.id === id ? updater(m) : m));
  const next: ConversationState = { ...state, messages: nextMessages, updatedAt: new Date().toISOString() };
  index[metric] = next;
  saveIndex(index);
  return next;
}

export function replaceMessages(metric: string, messages: PersistedMessage[]): ConversationState {
  const index = loadIndex();
  const state = index[metric] || getOrCreateSession(metric);
  const next: ConversationState = { ...state, messages: messages.slice(), updatedAt: new Date().toISOString() };
  index[metric] = next;
  saveIndex(index);
  return next;
}

export function clearSession(metric: string): void {
  const index = loadIndex();
  delete index[metric];
  saveIndex(index);
}


