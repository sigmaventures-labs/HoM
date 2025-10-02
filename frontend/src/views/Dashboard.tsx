import React, { useEffect, useState } from "react";
import { MetricCard } from "../components/dashboard/MetricCard";
import type { MetricContext } from "../components/dashboard/MetricCard";
import type { SparkDatum } from "../components/dashboard/Sparkline";
import { ChatInterface } from "../components/chat/ChatInterface";
import { Dialog, DialogContent } from "../components/ui/dialog";

type ApiMetricStatus = "red" | "yellow" | "green" | null;
type UiStatus = "good" | "warning" | "critical";

interface ApiMetricPoint {
  metric_key: string;
  value: number | null;
  status?: ApiMetricStatus;
  period_start?: string | null;
  period_end?: string | null;
  target_value?: number | null;
  thresholds?: Record<string, number> | null;
}

interface CardData {
  key: string;
  title: string;
  value: string | number;
  change: number;
  target?: number;
  trend: "up" | "down" | "flat";
  status: UiStatus;
  sparkline: SparkDatum[];
  breakdown?: { [k: string]: number };
}

const metricTitles: Record<string, string> = {
  headcount: "Headcount",
  absenteeism_rate: "Absenteeism Rate",
  turnover_rate: "Turnover Rate",
  overtime_rate: "Overtime",
};

const toUiStatus = (s?: ApiMetricStatus): UiStatus => {
  if (s === "green") return "good";
  if (s === "yellow") return "warning";
  if (s === "red") return "critical";
  return "warning";
};

const isRate = (key: string) => key === "absenteeism_rate" || key === "overtime_rate" || key === "turnover_rate";

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return (await res.json()) as T;
}

export function Dashboard() {
  const [chatMetric, setChatMetric] = useState<string | null>(null);
  const [chatContext, setChatContext] = useState<MetricContext | null>(null);
  const [cards, setCards] = useState<CardData[] | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const openChat = (metricTitle: string, context?: MetricContext) => {
    const key = metricTitle.toLowerCase().includes("headcount")
      ? "headcount"
      : metricTitle.toLowerCase().includes("absentee")
      ? "absenteeism_rate"
      : metricTitle.toLowerCase().includes("turnover")
      ? "turnover_rate"
      : metricTitle.toLowerCase().includes("overtime")
      ? "overtime_rate"
      : metricTitle.toLowerCase();
    setChatMetric(key);
    setChatContext(context || null);
  };

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const current = await fetchJson<ApiMetricPoint[]>("/api/metrics/current");

        const keys = ["headcount", "absenteeism_rate", "turnover_rate", "overtime_rate"] as const;
        const trendResults = await Promise.all(
          keys.map((k) => fetchJson<ApiMetricPoint[]>(`/api/metrics/trend?metric_key=${k}&weeks=12`))
        );
        const headcountBreakdown = await fetchJson<Record<string, number>>(`/api/metrics/headcount/breakdown`);

        // Map to cards in a fixed order
        const mapped: CardData[] = keys.map((k, idx) => {
          const cur = current.find((m) => m.metric_key === k);
          const trend = trendResults[idx] || [];
          const latest = cur?.value ?? null;
          const prev = trend.length >= 2 ? (trend[trend.length - 2].value ?? null) : null;

          // Compute change: for headcount use percent change; for rates use pct-point change
          let change = 0;
          if (latest !== null && prev !== null && prev !== 0) {
            if (isRate(k)) {
              change = ((latest - prev) * 100);
            } else {
              change = ((latest - prev) / prev) * 100;
            }
          }

          const trendDir: "up" | "down" | "flat" = change > 0.0001 ? "up" : change < -0.0001 ? "down" : "flat";

          const valueDisplay: string | number = latest === null
            ? "N/A"
            : isRate(k)
              ? `${(latest * 100).toFixed(1)}%`
              : Math.round(latest);

          const sparkline: SparkDatum[] = (trend || []).map((p, i) => ({
            label: i + 1,
            value: typeof p.value === "number" ? (isRate(k) ? p.value * 100 : p.value) : 0,
          }));

          const target = isRate(k) && typeof cur?.target_value === "number" ? cur.target_value * 100 : undefined;
          const status = toUiStatus(cur?.status ?? null);

          const card: CardData = {
            key: k,
            title: metricTitles[k],
            value: valueDisplay,
            change: Number.isFinite(change) ? Number(change.toFixed(1)) : 0,
            target: typeof target === "number" ? Number(target.toFixed(1)) : undefined,
            trend: trendDir,
            status,
            sparkline,
          };
          if (k === "headcount") {
            card.breakdown = headcountBreakdown;
          }
          return card;
        });

        setCards(mapped);
      } catch (e: any) {
        setError(e?.message || "Failed to load metrics");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  return (
    <div className="relative">
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 p-6">
        {loading && (
          <div className="col-span-1 md:col-span-2 xl:col-span-4 text-center text-muted-foreground">Loading metrics…</div>
        )}
        {error && !loading && (
          <div className="col-span-1 md:col-span-2 xl:col-span-4 text-center text-destructive">{error}</div>
        )}
        {!loading && !error && cards && cards.map((c) => (
          <div key={c.key}>
            <MetricCard
              title={c.title}
              value={c.value}
              change={c.change}
              target={c.target}
              trend={c.trend}
              status={c.status}
              sparkline={c.sparkline}
              onAskAI={(ctx) => openChat(c.title, ctx)}
            />
          </div>
        ))}
      </div>

      <Dialog open={!!chatMetric} onOpenChange={(open) => { if (!open) { setChatMetric(null); setChatContext(null); } }}>
        <DialogContent className="max-w-3xl p-0 border-0 bg-transparent shadow-none">
          {chatMetric && (
            <ChatInterface
              metric={chatMetric}
              context={chatContext || undefined}
              initialPrompt={chatContext ? `Tell me about ${chatContext.title}` : undefined}
              autoSendInitial={true}
              onClose={() => { setChatMetric(null); setChatContext(null); }}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}


