import Chat from "./components/Chat.jsx";

export default function App() {
  return <>
    <header className="topbar">
      <div className="brand"><span className="brand-mark">IO</span> InferOps</div>
      <div className="environment"><span /> local demo</div>
    </header>
    <main>
      <div className="intro">
        <h1>Deployment diagnostics</h1>
        <p>Inspect a Kubernetes workload using read-only evidence.</p>
      </div>
      <Chat />
      <footer>InferOps only reads workload status and events. It does not change cluster resources.</footer>
    </main>
  </>;
}
