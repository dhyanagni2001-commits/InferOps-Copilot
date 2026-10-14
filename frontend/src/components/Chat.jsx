import { useState } from "react";
import { diagnose } from "../services/api.js";
import DiagnosticSteps from "./DiagnosticSteps.jsx";
import EvidencePanel from "./EvidencePanel.jsx";
import Message from "./Message.jsx";

export default function Chat() {
  const [question, setQuestion] = useState("Why does this deployment keep restarting?");
  const [namespace, setNamespace] = useState("inferops-demo");
  const [kind, setKind] = useState("Deployment");
  const [workload, setWorkload] = useState("inference-demo");
  const [token, setToken] = useState("dev-token");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  async function submit(event) {
    event.preventDefault(); setResult(null); setError(""); setLoading(true); setStatus("Starting diagnosis…");
    try {
      await diagnose({ question, namespace, workload: { kind, name: workload } }, token, (name, data) => {
        if (name === "status") setStatus(data.message);
        if (name === "completed") setResult(data);
        if (name === "error") throw new Error(data.message);
      });
    } catch (requestError) {
      console.error("diagnosis failed", requestError); setError(requestError.message);
    } finally {
      setLoading(false); setStatus("");
    }
  }

  return <>
    <form className="diagnostic-form" onSubmit={submit}>
      <div className="form-heading">
        <div><h2>New check</h2><p>Describe what is failing and where.</p></div>
        <span className="mode">read only</span>
      </div>
      <label>What is happening?<textarea value={question} onChange={e => setQuestion(e.target.value)} required /></label>
      <div className="fields">
        <label>Namespace<input value={namespace} onChange={e => setNamespace(e.target.value)} required /></label>
        <label>Resource<select value={kind} onChange={e => setKind(e.target.value)}>
          <option>Deployment</option><option>StatefulSet</option><option>DaemonSet</option><option>Pod</option><option>Service</option>
        </select></label>
        <label>Name<input value={workload} onChange={e => setWorkload(e.target.value)} required /></label>
        <label>API token<input type="password" value={token} onChange={e => setToken(e.target.value)} required /></label>
      </div>
      <div className="form-actions">
        <button disabled={loading}>{loading ? "Checking…" : "Run diagnostic"}</button>
        <span>Usually takes a few seconds</span>
      </div>
    </form>
    <DiagnosticSteps status={status} />
    {error && <p className="warning">{error}</p>}
    <Message diagnosis={result?.diagnosis} />
    <EvidencePanel evidence={result?.evidence} />
  </>;
}
