import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { X, Send, User, Bot, TrendingUp, Users, Clock, DollarSign } from "lucide-react";

interface ChatMessage {
  id: string;
  type: 'user' | 'ai';
  content: string;
  timestamp: Date;
  actions?: string[];
}

interface ChatInterfaceProps {
  metric: string;
  onClose: () => void;
}

export function ChatInterface({ metric, onClose }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      type: 'ai',
      content: `I can help you understand your ${metric} metric. What would you like to know?`,
      timestamp: new Date(),
    }
  ]);
  const [input, setInput] = useState('');

  const getMetricIcon = () => {
    switch (metric) {
      case 'headcount': return <Users className="h-5 w-5" />;
      case 'turnover': return <TrendingUp className="h-5 w-5" />;
      case 'absenteeism': return <Clock className="h-5 w-5" />;
      case 'overtime': return <DollarSign className="h-5 w-5" />;
      default: return <Bot className="h-5 w-5" />;
    }
  };

  const getAIResponse = (userMessage: string): string => {
    const responses = {
      headcount: [
        "Your headcount is currently 245 employees, up 2.3% from last quarter. The growth is primarily in Direct Labor (180 employees) with Indirect Labor stable at 65. This aligns with your production scale-up initiative.",
        "The headcount increase correlates with the Q3 expansion. Most new hires are in manufacturing roles. Retention in the first 90 days is 85%, which is above industry average."
      ],
      turnover: [
        "Your turnover rate is 18%, up from 15% last quarter. The main drivers are: Better Opportunity (44%), Compensation (22%), and Work Environment (17%). The spike in 'Better Opportunity' correlates with a competitor opening nearby.",
        "The 90-day turnover at 35% suggests onboarding challenges. Exit interviews show new hires feel disconnected from team culture. I recommend implementing a mentor program."
      ],
      absenteeism: [
        "Absenteeism is at 8.5%, above your 5% target. Peak absences occur on Mondays (22%) and Fridays (18%). The manufacturing department shows highest rates at 12%.",
        "Seasonal patterns show increases during flu season and school holidays. Unplanned absences cost approximately $3,200 per percentage point above target."
      ],
      overtime: [
        "Overtime is 15% of regular hours, costing $125,000 monthly. The packaging department drives 40% of total OT due to equipment bottlenecks during peak shifts.",
        "Weekend overtime spikes during month-end order fulfillment. Implementing a third shift could reduce OT costs by 60% while improving work-life balance."
      ]
    };

    const metricResponses = responses[metric as keyof typeof responses] || ['I can help analyze this metric for you.'];
    return metricResponses[Math.floor(Math.random() * metricResponses.length)];
  };

  const handleSend = () => {
    if (!input.trim()) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: input,
      timestamp: new Date(),
    };

    const aiResponse: ChatMessage = {
      id: (Date.now() + 1).toString(),
      type: 'ai',
      content: getAIResponse(input),
      timestamp: new Date(),
      actions: input.toLowerCase().includes('fix') || input.toLowerCase().includes('improve') ? [
        'Implement mentor program for new hires',
        'Conduct stay interviews with high performers',
        'Review compensation benchmarks for critical roles'
      ] : undefined
    };

    setMessages(prev => [...prev, userMessage, aiResponse]);
    setInput('');
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <Card className="h-full flex flex-col glass-effect border-0 glow-primary">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4 border-b border-border/50">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg gradient-primary glow-primary">
            {getMetricIcon()}
          </div>
          <CardTitle className="capitalize text-xl font-semibold bg-gradient-to-r from-foreground to-primary bg-clip-text text-transparent">
            {metric} Analysis
          </CardTitle>
        </div>
        <Button variant="ghost" size="sm" onClick={onClose} className="hover:bg-destructive/20 hover:text-destructive">
          <X className="h-4 w-4" />
        </Button>
      </CardHeader>
      
      <CardContent className="flex-1 flex flex-col">
        <ScrollArea className="flex-1 mb-4 h-96">
          <div className="space-y-4">
            {messages.map((message) => (
              <div 
                key={message.id} 
                className={`flex items-start space-x-2 ${message.type === 'user' ? 'justify-end' : ''}`}
              >
                {message.type === 'ai' && (
                  <div className="w-10 h-10 rounded-full gradient-primary flex items-center justify-center glow-primary">
                    <Bot className="h-5 w-5 text-white" />
                  </div>
                )}
                
                <div className={`max-w-[80%] ${message.type === 'user' ? 'order-first' : ''}`}>
                  <div className={`rounded-xl p-4 shadow-lg ${
                    message.type === 'user' 
                      ? 'gradient-primary text-white ml-auto glow-primary' 
                      : 'glass-effect border border-border/50'
                  }`}>
                    {message.content}
                  </div>
                  
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
                
                {message.type === 'user' && (
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
            onKeyPress={handleKeyPress}
            placeholder="Ask about this metric..."
            className="flex-1 border-0 bg-transparent focus:ring-2 focus:ring-primary/50 placeholder:text-muted-foreground/70"
          />
          <Button onClick={handleSend} className="gradient-primary glow-primary hover:scale-105 transition-all duration-200">
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}