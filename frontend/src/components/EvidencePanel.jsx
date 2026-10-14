export default function EvidencePanel({ evidence = [] }) {
  if (!evidence.length) return null;
  return <section className="evidence"><div className="section-title"><h2>Evidence</h2><span>{evidence.length} records</span></div>{evidence.map(item => (
    <details key={item.id}><summary><span>{item.title}</span><code>{item.id}</code></summary><pre>{item.detail}</pre>
      {item.data?.url && <a href={item.data.url} target="_blank" rel="noreferrer">Open source</a>}
    </details>
  ))}</section>;
}
