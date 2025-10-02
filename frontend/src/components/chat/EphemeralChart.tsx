import { useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "../ui/chart";
import { Line, LineChart, ReferenceLine, ResponsiveContainer, XAxis, YAxis } from "recharts";

type ChartPoint = { x: string | number; y: number | null };

type EphemeralAnnotation =
  | { type: "horizontal_line"; y: number; label?: string }
  | { type: string; [k: string]: unknown };

export type EphemeralUiSpec = {
  version: number;
  mode: string;
  components: Array<
    | {
        type: "chart";
        kind: "line"; // MVP
        title?: string;
        data: ChartPoint[];
        yFormat?: "%" | "number";
        annotations?: EphemeralAnnotation[];
      }
    | {
        type: "table";
        title?: string;
        rows: { label: string; value?: string | number | null }[];
      }
  >;
  meta?: Record<string, unknown>;
};

export function EphemeralChart({ spec }: { spec: EphemeralUiSpec | null | undefined }) {
  const chart = useMemo(() => (spec?.components || []).find((c: any) => c.type === "chart"), [spec]);
  const table = useMemo(() => (spec?.components || []).find((c: any) => c.type === "table"), [spec]);

  if (!spec) return null;

  return (
    <div className="space-y-3">
      {chart && (
        <Card className="glass-effect border border-border/50">
          {chart.title ? (
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-medium">{chart.title}</CardTitle>
            </CardHeader>
          ) : null}
          <CardContent>
            <div style={{ height: 220 }}>
              <ChartContainer className="h-full w-full aspect-auto" config={{ value: { label: "Value", color: "var(--primary)" } }}>
                <LineChart data={(chart as any).data} margin={{ left: 8, right: 8, top: 8, bottom: 8 }}>
                  <XAxis dataKey="x" tickLine={false} axisLine={false} />
                  <YAxis hide domain={["auto", "auto"]} />
                  <Line type="monotone" dataKey="y" stroke="var(--color-value)" strokeWidth={2} dot={false} isAnimationActive={false} />
                  {Array.isArray((chart as any).annotations) && (chart as any).annotations.map((a: EphemeralAnnotation, idx: number) => {
                    if (a.type === "horizontal_line" && typeof (a as any).y === "number") {
                      return <ReferenceLine key={idx} y={(a as any).y} stroke="var(--muted-foreground)" strokeDasharray="4 4" label={(a as any).label || ""} />;
                    }
                    return null;
                  })}
                  <ChartTooltip content={<ChartTooltipContent hideLabel />} />
                </LineChart>
              </ChartContainer>
            </div>
          </CardContent>
        </Card>
      )}

      {table && (
        <Card className="glass-effect border border-border/50">
          {table.title ? (
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-medium">{table.title}</CardTitle>
            </CardHeader>
          ) : null}
          <CardContent>
            <div className="grid grid-cols-2 gap-y-2 text-sm">
              {(table as any).rows?.map((row: any, idx: number) => (
                <div key={`row-${idx}`} className="contents">
                  <div className="text-muted-foreground">{row.label}</div>
                  <div className="text-right font-mono tabular-nums">{row.value ?? "—"}</div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export function buildDevFallbackSpec(): EphemeralUiSpec {
  const now = Date.now();
  const series = Array.from({ length: 12 }).map((_, i) => ({ x: new Date(now - (11 - i) * 7 * 24 * 3600 * 1000).toISOString().slice(0, 10), y: 0.2 + Math.sin(i / 2) * 0.05 }));
  return {
    version: 1,
    mode: "explanation",
    components: [
      { type: "chart", kind: "line", title: "Sample Trend", data: series, yFormat: "%", annotations: [{ type: "horizontal_line", y: 0.25, label: "Target" }] },
      { type: "table", title: "Summary", rows: [ { label: "Current", value: "24.5%" }, { label: "Change", value: "+1.2%" }, { label: "Status", value: "OK" } ] },
    ],
  };
}


