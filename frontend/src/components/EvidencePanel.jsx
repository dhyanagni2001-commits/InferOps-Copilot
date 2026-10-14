export default function EvidencePanel({ evidence = [] }) {
  if (!evidence.length) return null;
  return <section><h2>Evidence</h2>{evidence.map(item => (
    <details key={item.id}><summary>{item.title} <code>{item.id}</code></summary><pre>{item.detail}</pre></details>
  ))}</section>;
}
