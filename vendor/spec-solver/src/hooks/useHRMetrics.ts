import { useState, useEffect } from 'react';

export interface HRMetric {
  id: string;
  title: string;
  value: string | number;
  change: number;
  target?: number;
  breakdown?: { [key: string]: number };
  trend: 'up' | 'down' | 'flat';
  status: 'good' | 'warning' | 'critical';
}

type ApiMetricStatus = 'red' | 'yellow' | 'green' | null;
type UiStatus = 'good' | 'warning' | 'critical';

interface ApiMetricPoint {
  metric_key: string;
  value: number | null;
  status?: ApiMetricStatus;
  target_value?: number | null;
}

const titles: Record<string, string> = {
  headcount: 'Headcount',
  absenteeism_rate: 'Absenteeism Rate',
  turnover_rate: 'Turnover Rate',
  overtime_rate: 'Overtime',
};

const isRate = (k: string) => k === 'absenteeism_rate' || k === 'turnover_rate' || k === 'overtime_rate';
const toUiStatus = (s?: ApiMetricStatus): UiStatus => (s === 'green' ? 'good' : s === 'yellow' ? 'warning' : s === 'red' ? 'critical' : 'warning');

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return (await res.json()) as T;
}

export const useHRMetrics = () => {
  const [metrics, setMetrics] = useState<HRMetric[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const current = await fetchJson<ApiMetricPoint[]>(`/api/metrics/current`);
        const keys = ['headcount', 'absenteeism_rate', 'turnover_rate', 'overtime_rate'] as const;
        const trend = await Promise.all(keys.map((k) => fetchJson<ApiMetricPoint[]>(`/api/metrics/trend?metric_key=${k}&weeks=12`)));
        const hcBreakdown = await fetchJson<Record<string, number>>(`/api/metrics/headcount/breakdown`);

        const mapped: HRMetric[] = keys.map((k, idx) => {
          const cur = current.find((m) => m.metric_key === k);
          const t = trend[idx] || [];
          const latest = cur?.value ?? null;
          const prev = t.length >= 2 ? (t[t.length - 2].value ?? null) : null;
          let change = 0;
          if (latest !== null && prev !== null && prev !== 0) {
            change = isRate(k) ? (latest - prev) * 100 : ((latest - prev) / prev) * 100;
          }
          const metric: HRMetric = {
            id: k,
            title: titles[k],
            value: latest === null ? 'N/A' : isRate(k) ? `${(latest * 100).toFixed(1)}%` : Math.round(latest),
            change: Number.isFinite(change) ? Number(change.toFixed(1)) : 0,
            target: isRate(k) && typeof cur?.target_value === 'number' ? Number((cur!.target_value * 100).toFixed(1)) : undefined,
            trend: change > 0.0001 ? 'up' : change < -0.0001 ? 'down' : 'flat',
            status: toUiStatus(cur?.status ?? null),
          };
          if (k === 'headcount') {
            metric.breakdown = hcBreakdown;
          }
          return metric;
        });
        setMetrics(mapped);
      } catch (e) {
        setMetrics([]);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  return { metrics, loading };
};