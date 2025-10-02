import { useState } from 'react';
import { MetricCard } from '@/components/MetricCard';
import { ChatInterface } from '@/components/ChatInterface';
import { useHRMetrics } from '@/hooks/useHRMetrics';
import { Skeleton } from '@/components/ui/skeleton';

const Index = () => {
  const { metrics, loading } = useHRMetrics();
  const [selectedMetric, setSelectedMetric] = useState<string | null>(null);

  const handleMetricChat = (metricId: string) => {
    setSelectedMetric(metricId);
  };

  const handleCloseChat = () => {
    setSelectedMetric(null);
  };

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
      {/* Animated background elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-primary/10 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-accent/10 rounded-full blur-3xl animate-pulse delay-1000"></div>
      </div>
      
      <div className="relative z-10 max-w-7xl mx-auto p-8">
        <header className="mb-12 text-center">
          <h1 className="text-5xl font-bold bg-gradient-to-r from-primary via-accent to-primary bg-clip-text text-transparent mb-4">
            HR Intelligence Platform
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Real-time workforce insights powered by advanced AI analytics
          </p>
          <div className="w-24 h-1 bg-gradient-to-r from-primary to-accent mx-auto mt-6 rounded-full"></div>
        </header>

        <div className="flex gap-8">
          <div className={`${selectedMetric ? 'w-1/2' : 'w-full'} transition-all duration-500 ease-in-out`}>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {metrics.map((metric, index) => (
                <div
                  key={metric.id}
                  className="animate-fade-in"
                  style={{ animationDelay: `${index * 100}ms` }}
                >
                  <MetricCard
                    title={metric.title}
                    value={metric.value}
                    change={metric.change}
                    target={metric.target}
                    breakdown={metric.breakdown}
                    trend={metric.trend}
                    status={metric.status}
                    onAskAI={() => handleMetricChat(metric.id)}
                  />
                </div>
              ))}
            </div>
          </div>

          {selectedMetric && (
            <div className="w-1/2 transition-all duration-500 ease-in-out animate-slide-in-right">
              <ChatInterface
                metric={selectedMetric}
                onClose={handleCloseChat}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Index;
