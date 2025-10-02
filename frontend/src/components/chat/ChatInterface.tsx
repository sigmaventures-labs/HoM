import { useEffect, useRef, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Badge } from "../ui/badge";
import { ScrollArea } from "../ui/scroll-area";
import { X, Send, User, Bot, TrendingUp, Users, Clock, DollarSign } from "lucide-react";
import { EphemeralChart, type EphemeralUiSpec, buildDevFallbackSpec } from "./EphemeralChart";

interface ChatMessage {
  id: string;
  type: "user" | "ai";
  content: string;
  timestamp: Date;
  actions?: string[];
  uiSpec?: EphemeralUiSpec;
}

export interface ChatInterfaceProps {
  metric: string;
  context?: {
    title: string;
    value: string | number;
    change: number;
    target?: number;
    breakdown?: { [key: string]: number };
    trend: "up" | "down" | "flat";
    status: "good" | "warning" | "critical";
    sparkline?: { label: string | number; value: number }[];
  };
  initialPrompt?: string;
  autoSendInitial?: boolean;
  onClose: () => void;
}

export function ChatInterface({ metric, context, initialPrompt, autoSendInitial, onClose }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "1",
      type: "ai",
      content: `I can help you understand your ${metric} metric. ${
        context ? `Current value: ${context.value}. Change: ${context.change}%.` : ""
      } What would you like to know?`,
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const getMetricIcon = () => {
    switch (metric.toLowerCase()) {
      case "headcount":
        return <Users className="h-5 w-5" />;
      case "absenteeism_rate":
      case "absenteeism":
        return <Clock className="h-5 w-5" />;
      case "turnover_rate":
      case "turnover":
        return <TrendingUp className="h-5 w-5" />;
      case "overtime_rate":
      case "overtime":
        return <DollarSign className="h-5 w-5" />;
      default:
        return <Bot className="h-5 w-5" />;
    }
  };

  // Auto-scroll to the bottom when messages change
  useEffect(() => {
    const el = scrollRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [messages]);

  const appendToAssistant = (assistantId: string, text: string) => {
    setMessages((prev) =>
      prev.map((m) => (m.id === assistantId ? { ...m, content: (m.content || "") + text } : m))
    );
  };

  const tryServerStream = async (
    prompt: string,
    assistantId: string,
    signal: AbortSignal
  ): Promise<boolean> => {
    const endpoints = [
      "/api/ai/chat/stream",
      "/api/chat/stream",
    ];

    for (const path of endpoints) {
      try {
        const res = await fetch(path, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "text/event-stream, text/plain",
          },
          body: JSON.stringify({ message: prompt, metric, mode: "explanation" }),
          signal,
        });

        if (!res.ok || !res.body) continue;

        const contentType = res.headers.get("content-type") || "";
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });

          if (contentType.includes("text/event-stream")) {
            buffer += chunk;
            const parts = buffer.split("\n\n");
            buffer = parts.pop() || "";
            for (const part of parts) {
              const lines = part.split("\n");
              for (const line of lines) {
                if (line.startsWith("data:")) {
                  const data = line.slice(5).trim();
                  if (data === "[DONE]") {
                    return true;
                  }
                  if (data) {
                    try {
                      const obj = JSON.parse(data);
                      if (obj && typeof obj === "object") {
                        if (typeof obj.delta === "string") {
                          appendToAssistant(assistantId, obj.delta);
                        }
                        if (obj.ui_spec) {
                          setMessages((prev) => prev.map((m) => (m.id === assistantId ? { ...m, uiSpec: obj.ui_spec } : m)));
                        }
                      } else {
                        appendToAssistant(assistantId, String(data));
                      }
                    } catch {
                      // plain text token
                      appendToAssistant(assistantId, data);
                    }
                  }
                }
              }
            }
          } else {
            appendToAssistant(assistantId, chunk);
          }
        }

        return true;
      } catch (_) {
        // try next endpoint or fall back
        continue;
      }
    }
    return false;
  };

  const mockStream = async (prompt: string, assistantId: string, signal: AbortSignal) => {
    const sentences = [
      `Here is an overview of ${metric}.`,
      "Analyzing recent patterns and seasonality...",
      "Highlighting key drivers and segments...",
      "Suggesting next steps you can take.",
    ];
    for (const sentence of sentences) {
      if (signal.aborted) break;
      await new Promise((r) => setTimeout(r, 450));
      appendToAssistant(assistantId, (assistantId ? (messages.length ? " " : "") : "") + sentence + " ");
    }
  };

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: "user",
      content: input,
      timestamp: new Date(),
    };

    const assistantId = (Date.now() + 1).toString();
    const assistantPlaceholder: ChatMessage = {
      id: assistantId,
      type: "ai",
      content: "",
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage, assistantPlaceholder]);
    setInput("");

    // Start streaming
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setIsStreaming(true);
    try {
      const streamed = await tryServerStream(userMessage.content, assistantId, controller.signal);
      if (!streamed) {
        await mockStream(userMessage.content, assistantId, controller.signal);
      }
      // Attach a development fallback UI spec if none provided by server
      setMessages((prev) => prev.map((m) => (m.id === assistantId ? { ...m, uiSpec: m.uiSpec || buildDevFallbackSpec() } : m)));
    } finally {
      setIsStreaming(false);
    }
  };

  // Auto-send initial prompt if provided
  useEffect(() => {
    if (autoSendInitial && initialPrompt && !isStreaming && messages.length === 1) {
      setInput(initialPrompt);
      // Microtask to ensure state updates before send
      Promise.resolve().then(() => handleSend());
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoSendInitial, initialPrompt]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <Card className="h-full flex flex-col glass-effect border-0 glow-primary">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4 border-b border-border/50">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg gradient-primary glow-primary">{getMetricIcon()}</div>
          <CardTitle className="capitalize text-xl font-semibold bg-gradient-to-r from-foreground to-primary bg-clip-text text-transparent">
            {metric} Analysis
          </CardTitle>
        </div>
        <Button variant="ghost" size="sm" onClick={onClose} className="hover:bg-destructive/20 hover:text-destructive">
          <X className="h-4 w-4" />
        </Button>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col">
        <ScrollArea ref={scrollRef} className="flex-1 mb-4 h-96">
          <div className="space-y-4">
            {messages.map((message) => (
              <div key={message.id} className={`flex items-start space-x-2 ${message.type === "user" ? "justify-end" : ""}`}>
                {message.type === "ai" && (
                  <div className="w-10 h-10 rounded-full gradient-primary flex items-center justify-center glow-primary">
                    <Bot className="h-5 w-5 text-white" />
                  </div>
                )}

                <div className={`max-w-[80%] ${message.type === "user" ? "order-first" : ""}`}>
                  <div
                    className={`rounded-xl p-4 shadow-lg ${
                      message.type === "user"
                        ? "gradient-primary text-white ml-auto glow-primary"
                        : "glass-effect border border-border/50"
                    }`}
                  >
                    {message.content || (message.type === "ai" && isStreaming ? "Typing…" : "")}
                  </div>

                  {message.type === "ai" && message.uiSpec && (
                    <div className="mt-3">
                      <EphemeralChart spec={message.uiSpec} />
                    </div>
                  )}

                  {message.actions && (
                    <div className="mt-2 space-y-1">
                      <div className="text-sm font-medium">Recommended Actions:</div>
                      {message.actions.map((action, index) => (
                        <Badge key={index} variant="outline" className="mr-1 mb-1">
                          {action}
                        </Badge>
                      ))}
                    </div>
                  )}
                </div>

                {message.type === "user" && (
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-secondary to-accent flex items-center justify-center border border-border/50">
                    <User className="h-5 w-5 text-foreground" />
                  </div>
                )}
              </div>
            ))}
          </div>
        </ScrollArea>

        <div className="flex space-x-3 p-4 glass-effect rounded-xl border border-border/50">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about this metric..."
            className="flex-1 border-0 bg-transparent focus:ring-2 focus:ring-primary/50 placeholder:text-muted-foreground/70"
          />
          {isStreaming ? (
            <Button onClick={() => { abortRef.current?.abort(); setIsStreaming(false); }} variant="secondary" className="hover:scale-105 transition-all duration-200">
              Stop
            </Button>
          ) : (
            <Button onClick={handleSend} disabled={!input.trim()} className="gradient-primary glow-primary hover:scale-105 transition-all duration-200">
              <Send className="h-4 w-4" />
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}


