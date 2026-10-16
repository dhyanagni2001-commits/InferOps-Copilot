const LABELS = {
  get_workload: "Read workload",
  service_inspect: "Inspect Service and endpoints",
  pod_status: "Read pod status",
  pod_events: "Read pod events",
  pod_logs: "Read container logs",
  search_docs: "Search runbooks",
};

export default function DiagnosticSteps({ steps }) {
  if (!steps.length) return null;
  return <ol className="steps" aria-label="Diagnostic steps">
    {steps.map((step, index) => (
      <li key={index} className={step.state}>
        <span className="step-icon" aria-hidden="true">{step.state === "done" ? "✓" : step.state === "failed" ? "!" : "•"}</span>
        <span className="step-name">{LABELS[step.tool] || step.tool}</span>
        <span className="step-detail">{step.detail || describe(step.args)}</span>
      </li>
    ))}
  </ol>;
}

function describe(args = {}) {
  return Object.entries(args).map(([key, value]) => `${key}=${value}`).join(" ");
}
