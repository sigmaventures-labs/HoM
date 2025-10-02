"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.Dashboard = Dashboard;
const jsx_runtime_1 = require("react/jsx-runtime");
const react_1 = require("react");
const MetricCard_1 = require("../components/dashboard/MetricCard");
const ChatInterface_1 = require("../components/chat/ChatInterface");
const dialog_1 = require("../components/ui/dialog");
const metricTitles = {
    headcount: "Headcount",
    absenteeism_rate: "Absenteeism Rate",
    turnover_rate: "Turnover Rate",
    overtime_rate: "Overtime",
};
const toUiStatus = (s) => {
    if (s === "green")
        return "good";
    if (s === "yellow")
        return "warning";
    if (s === "red")
        return "critical";
    return "warning";
};
const isRate = (key) => key === "absenteeism_rate" || key === "overtime_rate" || key === "turnover_rate";
async function fetchJson(url) {
    const res = await fetch(url);
    if (!res.ok)
        throw new Error(`${res.status} ${res.statusText}`);
    return (await res.json());
}
function Dashboard() {
    const [chatMetric, setChatMetric] = (0, react_1.useState)(null);
    const [chatContext, setChatContext] = (0, react_1.useState)(null);
    const [cards, setCards] = (0, react_1.useState)(null);
    const [loading, setLoading] = (0, react_1.useState)(true);
    const [error, setError] = (0, react_1.useState)(null);
    const openChat = (metricTitle, context) => {
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
    (0, react_1.useEffect)(() => {
        const load = async () => {
            try {
                setLoading(true);
                const current = await fetchJson("/api/metrics/current");
                const keys = ["headcount", "absenteeism_rate", "turnover_rate", "overtime_rate"];
                const trendResults = await Promise.all(keys.map((k) => fetchJson(`/api/metrics/trend?metric_key=${k}&weeks=12`)));
                const headcountBreakdown = await fetchJson(`/api/metrics/headcount/breakdown`);
                // Map to cards in a fixed order
                const mapped = keys.map((k, idx) => {
                    const cur = current.find((m) => m.metric_key === k);
                    const trend = trendResults[idx] || [];
                    const latest = cur?.value ?? null;
                    const prev = trend.length >= 2 ? (trend[trend.length - 2].value ?? null) : null;
                    // Compute change: for headcount use percent change; for rates use pct-point change
                    let change = 0;
                    if (latest !== null && prev !== null && prev !== 0) {
                        if (isRate(k)) {
                            change = ((latest - prev) * 100);
                        }
                        else {
                            change = ((latest - prev) / prev) * 100;
                        }
                    }
                    const trendDir = change > 0.0001 ? "up" : change < -0.0001 ? "down" : "flat";
                    const valueDisplay = latest === null
                        ? "N/A"
                        : isRate(k)
                            ? `${(latest * 100).toFixed(1)}%`
                            : Math.round(latest);
                    const sparkline = (trend || []).map((p, i) => ({
                        label: i + 1,
                        value: typeof p.value === "number" ? (isRate(k) ? p.value * 100 : p.value) : 0,
                    }));
                    const target = isRate(k) && typeof cur?.target_value === "number" ? cur.target_value * 100 : undefined;
                    const status = toUiStatus(cur?.status ?? null);
                    const card = {
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
            }
            catch (e) {
                setError(e?.message || "Failed to load metrics");
            }
            finally {
                setLoading(false);
            }
        };
        load();
    }, []);
    return ((0, jsx_runtime_1.jsxs)("div", { className: "relative", children: [(0, jsx_runtime_1.jsxs)("div", { className: "grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 p-6", children: [loading && ((0, jsx_runtime_1.jsx)("div", { className: "col-span-1 md:col-span-2 xl:col-span-4 text-center text-muted-foreground", children: "Loading metrics\u2026" })), error && !loading && ((0, jsx_runtime_1.jsx)("div", { className: "col-span-1 md:col-span-2 xl:col-span-4 text-center text-destructive", children: error })), !loading && !error && cards && cards.map((c) => ((0, jsx_runtime_1.jsx)("div", { children: (0, jsx_runtime_1.jsx)(MetricCard_1.MetricCard, { title: c.title, value: c.value, change: c.change, target: c.target, trend: c.trend, status: c.status, sparkline: c.sparkline, onAskAI: (ctx) => openChat(c.title, ctx) }) }, c.key)))] }), (0, jsx_runtime_1.jsx)(dialog_1.Dialog, { open: !!chatMetric, onOpenChange: (open) => { if (!open) {
                    setChatMetric(null);
                    setChatContext(null);
                } }, children: (0, jsx_runtime_1.jsx)(dialog_1.DialogContent, { className: "max-w-3xl p-0 border-0 bg-transparent shadow-none", children: chatMetric && (0, jsx_runtime_1.jsx)(ChatInterface_1.ChatInterface, { metric: chatMetric, context: chatContext || undefined, onClose: () => { setChatMetric(null); setChatContext(null); } }) }) })] }));
}
