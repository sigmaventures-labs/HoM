import { useHRMetrics } from "@/hooks/useHRMetrics";
import { MetricCard } from "@/components/MetricCard";
import type { SparkDatum } from "@/components/Sparkline";
import { Skeleton } from "@/components/ui/skeleton";

const demoSpark: SparkDatum[] = Array.from({ length: 12 }).map((_, i) => ({ label: i + 1, value: Math.round(50 + Math.sin(i / 2) * 10 + i) }));

export default function HRDashboard() {
  const { metrics, loading } = useHRMetrics();

  if (loading) {
    return (
      <div className="min-h-screen bg-background p-6">
        <div className="max-w-7xl mx-auto">
          <div className="mb-8">
            <Skeleton className="h-8 w-64 mb-2" />
            <Skeleton className="h-4 w-96" />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-64" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background relative overflow-hidden">
      <div className="relative z-10 max-w-7xl mx-auto p-8">
        <header className="mb-8">
          <h2 className="text-3xl font-bold">HR Dashboard</h2>
        </header>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {metrics.map((metric, index) => (
            <div key={metric.id} className="animate-fade-in" style={{ animationDelay: `${index * 100}ms` }}>
              <MetricCard
                title={metric.title}
                value={metric.value}
                change={metric.change}
                target={metric.target}
                breakdown={metric.breakdown}
                trend={metric.trend}
                status={metric.status}
                sparkline={demoSpark}
                onAskAI={() => {}}
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}


