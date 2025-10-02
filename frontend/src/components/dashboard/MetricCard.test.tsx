import { render, screen, fireEvent } from "@testing-library/react";
import { MetricCard } from "./MetricCard";

// Mock Sparkline to avoid Recharts dependencies in this test suite
jest.mock("./Sparkline", () => ({
  Sparkline: ({ data }: { data: { label: string | number; value: number }[] }) => (
    <div data-testid="mock-sparkline">{data.length}pts</div>
  ),
}));

describe("MetricCard", () => {
  it("renders title, value and Ask AI button", () => {
    render(
      <MetricCard
        title="Headcount"
        value={245}
        change={2.3}
        trend="up"
        status="good"
        onAskAI={() => {}}
      />
    );
    expect(screen.getByText("Headcount")).toBeInTheDocument();
    expect(screen.getByText("245")).toBeInTheDocument();
    expect(screen.getByText("Ask AI")).toBeInTheDocument();
  });

  it("formats positive change with plus sign and percent", () => {
    render(
      <MetricCard
        title="Absenteeism"
        value={"3.1%"}
        change={2.3}
        trend="up"
        status="warning"
        onAskAI={() => {}}
      />
    );
    expect(screen.getByText("+2.3%"))
      .toHaveClass("text-success");
  });

  it("formats negative change without plus and applies destructive color", () => {
    render(
      <MetricCard
        title="Turnover"
        value={"10.2%"}
        change={-1.5}
        trend="down"
        status="critical"
        onAskAI={() => {}}
      />
    );
    expect(screen.getByText("-1.5%"))
      .toHaveClass("text-destructive");
  });

  it("shows status badge with capitalized text", () => {
    render(
      <MetricCard
        title="Headcount"
        value={245}
        change={0}
        trend="flat"
        status="good"
        onAskAI={() => {}}
      />
    );
    const badge = screen.getByText("Good");
    expect(badge).toBeInTheDocument();
  });

  it("renders target and breakdown sections when provided", () => {
    render(
      <MetricCard
        title="Overtime"
        value={"5.0%"}
        change={0.5}
        target={4}
        breakdown={{ Sales: 80, Ops: 165 }}
        trend="up"
        status="warning"
        onAskAI={() => {}}
      />
    );
    expect(screen.getByText("Target:"));
    expect(screen.getByText("4%"));
    expect(screen.getByText("Sales:"));
    expect(screen.getByText("80"));
    expect(screen.getByText("Ops:"));
    expect(screen.getByText("165"));
  });

  it("renders sparkline when data is provided", () => {
    render(
      <MetricCard
        title="Absenteeism"
        value={"3.1%"}
        change={2.3}
        trend="up"
        status="warning"
        sparkline={[{ label: "W1", value: 3 }, { label: "W2", value: 4 }]}
        onAskAI={() => {}}
      />
    );
    expect(screen.getByTestId("mock-sparkline")).toHaveTextContent("2pts");
  });

  it("invokes onAskAI with full metric context", () => {
    const onAskAI = jest.fn();
    const props = {
      title: "Headcount",
      value: 245,
      change: 2.3,
      target: 250,
      breakdown: { Sales: 80, Ops: 165 },
      trend: "up" as const,
      status: "good" as const,
      sparkline: [
        { label: "W1", value: 1 },
        { label: "W2", value: 2 },
      ],
    };
    render(<MetricCard {...props} onAskAI={onAskAI} />);
    fireEvent.click(screen.getByText("Ask AI"));
    expect(onAskAI).toHaveBeenCalledTimes(1);
    expect(onAskAI).toHaveBeenCalledWith(props);
  });
});


