import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";
import { Line, LineChart, ResponsiveContainer, XAxis, YAxis } from "recharts";

export interface SparkDatum {
  label: string | number;
  value: number;
}

export function Sparkline({ data, height = 60, color = "#6366f1" }: { data: SparkDatum[]; height?: number; color?: string }) {
  return (
    <div style={{ height }}>
      <ChartContainer config={{ value: { label: "Value", color } }}>
        <ResponsiveContainer>
          <LineChart data={data} margin={{ left: 0, right: 0, top: 8, bottom: 0 }}>
            <XAxis dataKey="label" hide tickLine={false} axisLine={false} />
            <YAxis hide domain={["dataMin", "dataMax"]} />
            <Line type="monotone" dataKey="value" stroke={color} strokeWidth={2} dot={false} />
            <ChartTooltip content={<ChartTooltipContent hideLabel />} />
          </LineChart>
        </ResponsiveContainer>
      </ChartContainer>
    </div>
  );
}


