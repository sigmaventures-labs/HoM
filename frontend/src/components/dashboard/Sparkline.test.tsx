import { render, screen } from "@testing-library/react";
import { Sparkline } from "./Sparkline";

// Mock ChartContainer and Recharts primitives to avoid complex SVG/measures in JSDOM
jest.mock("../ui/chart", () => ({
  ChartContainer: ({ children }: any) => <div data-testid="chart-container">{children}</div>,
  ChartTooltip: ({ children }: any) => <div data-testid="chart-tooltip">{children}</div>,
  ChartTooltipContent: () => <div data-testid="chart-tooltip-content" />,
}));

jest.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: any) => <div data-testid="responsive-container">{children}</div>,
  LineChart: ({ children }: any) => <div data-testid="line-chart">{children}</div>,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  Line: () => <div data-testid="line" />,
}));

describe("Sparkline", () => {
  it("renders chart structure with provided data", () => {
    render(
      <Sparkline
        data={[
          { label: "W1", value: 3 },
          { label: "W2", value: 5 },
        ]}
        height={60}
        color="#4f46e5"
      />
    );
    expect(screen.getByTestId("chart-container")).toBeInTheDocument();
    expect(screen.getByTestId("responsive-container")).toBeInTheDocument();
    expect(screen.getByTestId("line-chart")).toBeInTheDocument();
    expect(screen.getByTestId("x-axis")).toBeInTheDocument();
    expect(screen.getByTestId("y-axis")).toBeInTheDocument();
    expect(screen.getByTestId("line")).toBeInTheDocument();
  });
});


