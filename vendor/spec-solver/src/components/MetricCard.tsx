import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { TrendingUp, TrendingDown, MessageCircle } from "lucide-react";
import { Sparkline, type SparkDatum } from "@/components/Sparkline";

interface MetricCardProps {
  title: string;
  value: string | number;
  change: number;
  target?: number;
  breakdown?: { [key: string]: number };
  trend: 'up' | 'down' | 'flat';
  status: 'good' | 'warning' | 'critical';
  onAskAI: () => void;
  sparkline?: SparkDatum[];
}

export function MetricCard({ 
  title, 
  value, 
  change, 
  target, 
  breakdown, 
  trend, 
  status, 
  onAskAI,
  sparkline
}: MetricCardProps) {
  const getStatusColor = () => {
    switch (status) {
      case 'good': return 'gradient-success text-success-foreground glow-success';
      case 'warning': return 'gradient-warning text-warning-foreground glow-warning';
      case 'critical': return 'gradient-destructive text-destructive-foreground glow-destructive';
      default: return 'bg-muted text-muted-foreground';
    }
  };

  const getStatusGlow = () => {
    switch (status) {
      case 'good': return 'glow-success';
      case 'warning': return 'glow-warning';
      case 'critical': return 'glow-destructive';
      default: return '';
    }
  };

  const getTrendIcon = () => {
    if (trend === 'up') return <TrendingUp className="h-4 w-4" />;
    if (trend === 'down') return <TrendingDown className="h-4 w-4" />;
    return null;
  };

  const formatChange = (value: number) => {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value}%`;
  };

  return (
    <Card className={`relative glass-effect hover:scale-105 transition-all duration-300 border-0 ${getStatusGlow()}`}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <CardTitle className="text-lg font-semibold bg-gradient-to-r from-foreground to-muted-foreground bg-clip-text text-transparent">
          {title}
        </CardTitle>
        <Badge className={`${getStatusColor()} border-0 px-3 py-1 text-xs font-semibold`}>
          {status.charAt(0).toUpperCase() + status.slice(1)}
        </Badge>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="text-4xl font-bold bg-gradient-to-br from-foreground via-primary to-accent bg-clip-text text-transparent">
            {value}
          </div>
          <div className="flex items-center space-x-2 text-sm">
            {getTrendIcon()}
            <span className={`font-semibold ${trend === 'up' ? 'text-success' : trend === 'down' ? 'text-destructive' : 'text-muted-foreground'}`}>
              {formatChange(change)}
            </span>
          </div>
        </div>
        {sparkline && sparkline.length > 0 && (
          <div className="-mt-2">
            <Sparkline data={sparkline} height={60} color="#4f46e5" />
          </div>
        )}
        
        {target && (
          <div className="flex items-center justify-between p-3 rounded-lg bg-muted/30 border border-border/50">
            <span className="text-sm text-muted-foreground">Target:</span>
            <span className="text-sm font-semibold">{target}%</span>
          </div>
        )}
        
        {breakdown && (
          <div className="space-y-2 p-3 rounded-lg bg-muted/20 border border-border/30">
            {Object.entries(breakdown).map(([key, val]) => (
              <div key={key} className="flex justify-between items-center text-sm">
                <span className="text-muted-foreground">{key}:</span>
                <span className="font-semibold text-foreground">{val}</span>
              </div>
            ))}
          </div>
        )}
        
        <Button 
          onClick={onAskAI}
          className="w-full gradient-primary hover:scale-[1.02] transition-all duration-200 glow-primary border-0 text-white font-semibold"
        >
          <MessageCircle className="h-4 w-4 mr-2" />
          Ask AI
        </Button>
      </CardContent>
    </Card>
  );
}