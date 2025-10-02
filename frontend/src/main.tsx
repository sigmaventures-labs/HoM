import React from "react";
import ReactDOM from "react-dom/client";
import { Dashboard } from "./views/Dashboard";
import { EphemeralChart, buildDevFallbackSpec } from "./components/chat/EphemeralChart";

const showPreview = window.location.hash === "#preview";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <div style={{ position: "fixed", top: 8, left: 8, zIndex: 9999, padding: 6, background: "#fffa", color: "#111", borderRadius: 6 }}>App booted</div>
    {showPreview ? (
      <div style={{ padding: 24 }}>
        <h2 style={{ marginBottom: 12 }}>EphemeralChart Preview</h2>
        <EphemeralChart spec={buildDevFallbackSpec()} />
      </div>
    ) : (
      <Dashboard />
    )}
  </React.StrictMode>
);


