import { render, screen } from "@testing-library/react";
import { EphemeralChart, type EphemeralUiSpec } from "./EphemeralChart";

// Mock UI chart and recharts for JSDOM
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
  ReferenceLine: () => <div data-testid="reference-line" />,
}));

describe("EphemeralChart", () => {
  it("renders chart and table from spec", () => {
    const spec: EphemeralUiSpec = {
      version: 1,
      mode: "explanation",
      components: [
        {
          type: "chart",
          kind: "line",
          title: "Absenteeism Rate Trend",
          data: [
            { x: "2025-09-01", y: 0.01 },
            { x: "2025-09-08", y: 0.02 },
          ],
          yFormat: "%",
          annotations: [{ type: "horizontal_line", y: 0.03, label: "Target" }],
        },
        {
          type: "table",
          title: "Summary",
          rows: [
            { label: "Current", value: "2.0%" },
            { label: "Change", value: "+1.0%" },
            { label: "Status", value: "OK" },
          ],
        },
      ],
    };

    render(<EphemeralChart spec={spec} />);

    expect(screen.getByText("Absenteeism Rate Trend")).toBeInTheDocument();
    expect(screen.getByTestId("chart-container")).toBeInTheDocument();
    expect(screen.getByTestId("line-chart")).toBeInTheDocument();
    expect(screen.getByTestId("x-axis")).toBeInTheDocument();
    expect(screen.getByTestId("y-axis")).toBeInTheDocument();
    expect(screen.getByTestId("line")).toBeInTheDocument();

    expect(screen.getByText("Summary")).toBeInTheDocument();
    expect(screen.getByText("Current")).toBeInTheDocument();
    expect(screen.getByText("2.0%"));
  });
});


