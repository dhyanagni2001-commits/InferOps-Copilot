import { useEffect, useState } from "react";
import Chat from "./components/Chat.jsx";
import { loadConfig } from "./services/api.js";

export default function App() {
  const [config, setConfig] = useState(null);
  const [configError, setConfigError] = useState("");

  useEffect(() => {
    loadConfig().then(setConfig).catch(error => setConfigError(error.message));
  }, []);

  const mode = config?.mode;
  return <>
    <header className="topbar">
      <div className="brand"><span className="brand-mark">IO</span> InferOps Copilot</div>
      <div className="environment" data-testid="mode">
        <span className={`dot ${mode === "cluster" ? "live" : configError ? "down" : ""}`} />
        {configError ? "backend unreachable" : mode === "cluster" ? "live cluster" : mode === "demo" ? "demo replay" : "connecting…"}
        {config?.llm_enabled && <em>· {config.llm_model}</em>}
      </div>
    </header>
    <main>
      <div className="intro">
        <h1>Deployment diagnostics</h1>
        <p>Find the root cause of a failing Kubernetes workload from read-only cluster evidence and runbooks.</p>
      </div>
      <Chat config={config} />
      <footer>
        InferOps only reads workload status, events, and logs. It never changes cluster resources or runs suggested commands.
        {config && <> · v{config.version} · retrieval: {config.embedding_backend}/{config.vector_store}</>}
      </footer>
    </main>
  </>;
}
