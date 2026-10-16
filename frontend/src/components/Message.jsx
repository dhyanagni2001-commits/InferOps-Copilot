import { useState } from "react";

const CAUSES = {
  oom_killed: "Out of memory", image_pull_error: "Image pull", config_error: "Configuration", unschedulable: "Scheduling",
  liveness_probe_failure: "Liveness probe", crash_loop: "Crash loop", readiness_probe_failure: "Readiness probe",
  service_port_mismatch: "Service port", service_no_endpoints: "Service selector", no_pods: "No pods",
  healthy: "Healthy", evidence_unavailable: "Not inspectable", unknown: "Undetermined",
};

export default function Message({ result }) {
  if (!result) return null;
  const { diagnosis } = result;
  return <section className={`result ${diagnosis.cause === "healthy" ? "ok" : ""}`} aria-label="Diagnosis">
    <div className="result-meta">
      <span className="badge">{CAUSES[diagnosis.cause] || diagnosis.cause}</span>
      <span className={`badge confidence-${diagnosis.confidence}`}>{diagnosis.confidence} confidence</span>
      <span className="badge subtle">{diagnosis.generated_by === "llm" ? "model-written" : "rule-based"}</span>
      <span className="timing">{result.duration_ms} ms · {result.mode}</span>
    </div>
    <h2>{diagnosis.summary}</h2>
    {diagnosis.evidence_ids.length > 0 && <p className="citations">Based on {diagnosis.evidence_ids.map(id => <a key={id} href={`#evidence-${id}`} className="cite">{id}</a>)}</p>}
    <h3>What to do next</h3>
    <ol>{diagnosis.suggested_actions.map(item => <li key={item}>{item}</li>)}</ol>
    {diagnosis.commands.length > 0 && <>
      <h3>Inspect further</h3>
      <ul className="commands">{diagnosis.commands.map(command => <Command key={command} command={command} />)}</ul>
    </>}
    {diagnosis.alternatives.length > 0 && <>
      <h3>Also observed</h3>
      <ul className="alternatives">{diagnosis.alternatives.map(item => <li key={item.cause}><strong>{CAUSES[item.cause] || item.cause}:</strong> {item.summary}</li>)}</ul>
    </>}
    {diagnosis.limitations.map(item => <p className="warning" key={item}>{item}</p>)}
  </section>;
}

function Command({ command }) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    try { await navigator.clipboard.writeText(command); setCopied(true); setTimeout(() => setCopied(false), 1500); } catch { /* clipboard is optional */ }
  }
  return <li><code>{command}</code><button type="button" className="copy" onClick={copy}>{copied ? "Copied" : "Copy"}</button></li>;
}
