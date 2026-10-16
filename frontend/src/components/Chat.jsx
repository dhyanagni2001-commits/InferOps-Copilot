import { useRef, useState } from "react";
import { diagnose } from "../services/api.js";
import DiagnosticSteps from "./DiagnosticSteps.jsx";
import EvidencePanel from "./EvidencePanel.jsx";
import Message from "./Message.jsx";

const SCENARIOS = [
  { label: "OOM restart", kind: "Deployment", name: "oom-demo", question: "Why does this deployment keep restarting?" },
  { label: "Image pull", kind: "Deployment", name: "broken-image", question: "The new rollout never starts. What is wrong?" },
  { label: "Readiness", kind: "Deployment", name: "broken-readiness", question: "Pods are running but receive no traffic. Why?" },
  { label: "Service port", kind: "Service", name: "broken-service", question: "Calls to this service are refused. What is the cause?" },
  { label: "Crash loop", kind: "Deployment", name: "crashloop-demo", question: "Why is the model API crash looping?" },
  { label: "Pending", kind: "Deployment", name: "unschedulable-demo", question: "The pod has been pending for a while." },
  { label: "Missing config", kind: "Deployment", name: "missing-config", question: "Container never starts after the config change." },
  { label: "Healthy", kind: "Deployment", name: "healthy-demo", question: "Users report errors. Is this deployment broken?" },
];

function storedToken() {
  try { return sessionStorage.getItem("inferops-token") || ""; } catch { return ""; }
}

export default function Chat({ config }) {
  const [question, setQuestion] = useState(SCENARIOS[0].question);
  const [namespace, setNamespace] = useState("inferops-demo");
  const [kind, setKind] = useState(SCENARIOS[0].kind);
  const [workload, setWorkload] = useState(SCENARIOS[0].name);
  const [token, setToken] = useState(storedToken() || "dev-token");
  const [steps, setSteps] = useState([]);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const controller = useRef(null);

  function pick(scenario) {
    setKind(scenario.kind); setWorkload(scenario.name); setQuestion(scenario.question);
  }

  async function submit(event) {
    event.preventDefault();
    controller.current?.abort();
    const abort = new AbortController();
    controller.current = abort;
    setResult(null); setError(""); setSteps([]); setStatus("Starting diagnosis…"); setLoading(true);
    try { sessionStorage.setItem("inferops-token", token); } catch { /* storage is optional */ }
    try {
      await diagnose({ question, namespace, workload: { kind, name: workload } }, token, (name, data) => {
        if (name === "status") setStatus(data.message);
        if (name === "tool_started") setSteps(items => [...items, { tool: data.tool, args: data.args, state: "running" }]);
        if (name === "tool_result") setSteps(items => finishStep(items, data));
        if (name === "completed") { setResult(data); setSteps(items => items.map(item => ({ ...item, state: item.state === "running" ? "done" : item.state }))); }
        if (name === "error") throw new Error(data.message);
      }, abort.signal);
    } catch (requestError) {
      setError(requestError.name === "AbortError" ? "Diagnosis cancelled." : requestError.message);
    } finally {
      if (controller.current === abort) { controller.current = null; setLoading(false); }
      setStatus("");
    }
  }

  function cancel() {
    controller.current?.abort();
  }

  const namespaces = config?.allowed_namespaces || [];
  return <>
    <form className="diagnostic-form" onSubmit={submit}>
      <div className="form-heading">
        <div><h2>New check</h2><p>Describe what is failing and where.</p></div>
        <span className="mode">read only</span>
      </div>
      <div className="scenarios" aria-label="Example scenarios">
        {SCENARIOS.map(item => (
          <button type="button" key={item.name} className={`chip ${workload === item.name ? "active" : ""}`} onClick={() => pick(item)}>{item.label}</button>
        ))}
      </div>
      <label>What is happening?<textarea value={question} onChange={e => setQuestion(e.target.value)} required minLength={3} maxLength={2000} /></label>
      <div className="fields">
        <label>Namespace{namespaces.length > 1
          ? <select value={namespace} onChange={e => setNamespace(e.target.value)}>{namespaces.map(item => <option key={item}>{item}</option>)}</select>
          : <input value={namespace} onChange={e => setNamespace(e.target.value)} required />}
        </label>
        <label>Resource<select value={kind} onChange={e => setKind(e.target.value)}>
          <option>Deployment</option><option>StatefulSet</option><option>DaemonSet</option><option>Pod</option><option>Service</option>
        </select></label>
        <label>Name<input value={workload} onChange={e => setWorkload(e.target.value)} required /></label>
        <label>API token<input type="password" value={token} onChange={e => setToken(e.target.value)} required autoComplete="off" /></label>
      </div>
      <div className="form-actions">
        <button disabled={loading}>{loading ? "Checking…" : "Run diagnostic"}</button>
        {loading && <button type="button" className="secondary" onClick={cancel}>Cancel</button>}
        <span>{status || "Usually takes a few seconds"}</span>
      </div>
    </form>
    <DiagnosticSteps steps={steps} />
    {error && <p className="warning" role="alert">{error}</p>}
    <Message result={result} />
    <EvidencePanel evidence={result?.evidence} cited={result?.diagnosis?.evidence_ids} />
  </>;
}

// Evidence sources are named after the tool that produced them.
function finishStep(items, evidence) {
  const index = items.findLastIndex(item => item.tool === evidence.source && item.state === "running");
  if (index === -1) return items;
  const next = [...items];
  next[index] = { ...next[index], state: evidence.error ? "failed" : "done", detail: evidence.error || evidence.title };
  return next;
}
