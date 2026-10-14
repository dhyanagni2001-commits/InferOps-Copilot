import { useState } from "react";
import { diagnose } from "../services/api.js";
import DiagnosticSteps from "./DiagnosticSteps.jsx";
import EvidencePanel from "./EvidencePanel.jsx";
import Message from "./Message.jsx";

export default function Chat() {
  const [question, setQuestion] = useState("Why does this deployment keep restarting?");
  const [namespace, setNamespace] = useState("inferops-demo");
  const [workload, setWorkload] = useState("inference-demo");
  const [token, setToken] = useState("dev-token");
  const [status, setStatus] = useState("");
  const [result, setResult] = useState(null);

  async function submit(event) {
    event.preventDefault(); setResult(null); setStatus("Starting diagnosis…");
    try {
      await diagnose({ question, namespace, workload: { kind: "Deployment", name: workload } }, token, (name, data) => {
        if (name === "status") setStatus(data.message);
        if (name === "completed") { setResult(data); setStatus(""); }
        if (name === "error") throw new Error(data.message);
      });
    } catch (error) { console.error("diagnosis failed", error); setStatus(error.message); }
  }

  return <>
    <form onSubmit={submit}>
      <label>Question<textarea value={question} onChange={e => setQuestion(e.target.value)} required /></label>
      <div className="row">
        <label>Namespace<input value={namespace} onChange={e => setNamespace(e.target.value)} required /></label>
        <label>Deployment<input value={workload} onChange={e => setWorkload(e.target.value)} required /></label>
        <label>API token<input type="password" value={token} onChange={e => setToken(e.target.value)} required /></label>
      </div>
      <button disabled={Boolean(status)}>{status ? "Working…" : "Diagnose"}</button>
    </form>
    <DiagnosticSteps status={status} />
    <Message diagnosis={result?.diagnosis} />
    <EvidencePanel evidence={result?.evidence} />
  </>;
}
