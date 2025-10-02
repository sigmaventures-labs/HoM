"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ChatInterface = ChatInterface;
const jsx_runtime_1 = require("react/jsx-runtime");
const react_1 = require("react");
const card_1 = require("../ui/card");
const button_1 = require("../ui/button");
const input_1 = require("../ui/input");
const badge_1 = require("../ui/badge");
const scroll_area_1 = require("../ui/scroll-area");
const lucide_react_1 = require("lucide-react");
function ChatInterface({ metric, context, onClose }) {
    const [messages, setMessages] = (0, react_1.useState)([
        {
            id: "1",
            type: "ai",
            content: `I can help you understand your ${metric} metric. ${context ? `Current value: ${context.value}. Change: ${context.change}%.` : ""} What would you like to know?`,
            timestamp: new Date(),
        },
    ]);
    const [input, setInput] = (0, react_1.useState)("");
    const getMetricIcon = () => {
        switch (metric.toLowerCase()) {
            case "headcount":
                return (0, jsx_runtime_1.jsx)(lucide_react_1.Users, { className: "h-5 w-5" });
            case "turnover":
                return (0, jsx_runtime_1.jsx)(lucide_react_1.TrendingUp, { className: "h-5 w-5" });
            case "absenteeism":
                return (0, jsx_runtime_1.jsx)(lucide_react_1.Clock, { className: "h-5 w-5" });
            case "overtime":
                return (0, jsx_runtime_1.jsx)(lucide_react_1.DollarSign, { className: "h-5 w-5" });
            default:
                return (0, jsx_runtime_1.jsx)(lucide_react_1.Bot, { className: "h-5 w-5" });
        }
    };
    const getAIResponse = (userMessage) => {
        const responses = {
            headcount: [
                "Your headcount is currently 245 employees, up 2.3% from last quarter. The growth is primarily in Direct Labor (180 employees) with Indirect Labor stable at 65. This aligns with your production scale-up initiative.",
                "The headcount increase correlates with the Q3 expansion. Most new hires are in manufacturing roles. Retention in the first 90 days is 85%, which is above industry average.",
            ],
            turnover: [
                "Your turnover rate is 18%, up from 15% last quarter. The main drivers are: Better Opportunity (44%), Compensation (22%), and Work Environment (17%). The spike in 'Better Opportunity' correlates with a competitor opening nearby.",
                "The 90-day turnover at 35% suggests onboarding challenges. Exit interviews show new hires feel disconnected from team culture. I recommend implementing a mentor program.",
            ],
            absenteeism: [
                "Absenteeism is at 8.5%, above your 5% target. Peak absences occur on Mondays (22%) and Fridays (18%). The manufacturing department shows highest rates at 12%.",
                "Seasonal patterns show increases during flu season and school holidays. Unplanned absences cost approximately $3,200 per percentage point above target.",
            ],
            overtime: [
                "Overtime is 15% of regular hours, costing $125,000 monthly. The packaging department drives 40% of total OT due to equipment bottlenecks during peak shifts.",
                "Weekend overtime spikes during month-end order fulfillment. Implementing a third shift could reduce OT costs by 60% while improving work-life balance.",
            ],
        };
        const key = metric.toLowerCase();
        const metricResponses = responses[key] || ["I can help analyze this metric for you."];
        return metricResponses[Math.floor(Math.random() * metricResponses.length)];
    };
    const handleSend = () => {
        if (!input.trim())
            return;
        const userMessage = {
            id: Date.now().toString(),
            type: "user",
            content: input,
            timestamp: new Date(),
        };
        const aiResponse = {
            id: (Date.now() + 1).toString(),
            type: "ai",
            content: getAIResponse(input),
            timestamp: new Date(),
            actions: input.toLowerCase().includes("fix") || input.toLowerCase().includes("improve")
                ? [
                    "Implement mentor program for new hires",
                    "Conduct stay interviews with high performers",
                    "Review compensation benchmarks for critical roles",
                ]
                : undefined,
        };
        setMessages((prev) => [...prev, userMessage, aiResponse]);
        setInput("");
    };
    const handleKeyPress = (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };
    return ((0, jsx_runtime_1.jsxs)(card_1.Card, { className: "h-full flex flex-col glass-effect border-0 glow-primary", children: [(0, jsx_runtime_1.jsxs)(card_1.CardHeader, { className: "flex flex-row items-center justify-between space-y-0 pb-4 border-b border-border/50", children: [(0, jsx_runtime_1.jsxs)("div", { className: "flex items-center space-x-3", children: [(0, jsx_runtime_1.jsx)("div", { className: "p-2 rounded-lg gradient-primary glow-primary", children: getMetricIcon() }), (0, jsx_runtime_1.jsxs)(card_1.CardTitle, { className: "capitalize text-xl font-semibold bg-gradient-to-r from-foreground to-primary bg-clip-text text-transparent", children: [metric, " Analysis"] })] }), (0, jsx_runtime_1.jsx)(button_1.Button, { variant: "ghost", size: "sm", onClick: onClose, className: "hover:bg-destructive/20 hover:text-destructive", children: (0, jsx_runtime_1.jsx)(lucide_react_1.X, { className: "h-4 w-4" }) })] }), (0, jsx_runtime_1.jsxs)(card_1.CardContent, { className: "flex-1 flex flex-col", children: [(0, jsx_runtime_1.jsx)(scroll_area_1.ScrollArea, { className: "flex-1 mb-4 h-96", children: (0, jsx_runtime_1.jsx)("div", { className: "space-y-4", children: messages.map((message) => ((0, jsx_runtime_1.jsxs)("div", { className: `flex items-start space-x-2 ${message.type === "user" ? "justify-end" : ""}`, children: [message.type === "ai" && ((0, jsx_runtime_1.jsx)("div", { className: "w-10 h-10 rounded-full gradient-primary flex items-center justify-center glow-primary", children: (0, jsx_runtime_1.jsx)(lucide_react_1.Bot, { className: "h-5 w-5 text-white" }) })), (0, jsx_runtime_1.jsxs)("div", { className: `max-w-[80%] ${message.type === "user" ? "order-first" : ""}`, children: [(0, jsx_runtime_1.jsx)("div", { className: `rounded-xl p-4 shadow-lg ${message.type === "user"
                                                    ? "gradient-primary text-white ml-auto glow-primary"
                                                    : "glass-effect border border-border/50"}`, children: message.content }), message.actions && ((0, jsx_runtime_1.jsxs)("div", { className: "mt-2 space-y-1", children: [(0, jsx_runtime_1.jsx)("div", { className: "text-sm font-medium", children: "Recommended Actions:" }), message.actions.map((action, index) => ((0, jsx_runtime_1.jsx)(badge_1.Badge, { variant: "outline", className: "mr-1 mb-1", children: action }, index)))] }))] }), message.type === "user" && ((0, jsx_runtime_1.jsx)("div", { className: "w-10 h-10 rounded-full bg-gradient-to-br from-secondary to-accent flex items-center justify-center border border-border/50", children: (0, jsx_runtime_1.jsx)(lucide_react_1.User, { className: "h-5 w-5 text-foreground" }) }))] }, message.id))) }) }), (0, jsx_runtime_1.jsxs)("div", { className: "flex space-x-3 p-4 glass-effect rounded-xl border border-border/50", children: [(0, jsx_runtime_1.jsx)(input_1.Input, { value: input, onChange: (e) => setInput(e.target.value), onKeyPress: handleKeyPress, placeholder: "Ask about this metric...", className: "flex-1 border-0 bg-transparent focus:ring-2 focus:ring-primary/50 placeholder:text-muted-foreground/70" }), (0, jsx_runtime_1.jsx)(button_1.Button, { onClick: handleSend, className: "gradient-primary glow-primary hover:scale-105 transition-all duration-200", children: (0, jsx_runtime_1.jsx)(lucide_react_1.Send, { className: "h-4 w-4" }) })] })] })] }));
}
