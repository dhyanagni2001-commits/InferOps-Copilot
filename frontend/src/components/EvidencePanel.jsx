export default function EvidencePanel({ evidence = [], cited = [] }) {
  if (!evidence.length) return null;
  const cluster = evidence.filter(item => item.source !== "search_docs");
  const docs = evidence.filter(item => item.source === "search_docs");
  return <section className="evidence" aria-label="Evidence">
    <div className="section-title"><h2>Evidence</h2><span>{evidence.length} records</span></div>
    <Group title="Cluster" items={cluster} cited={cited} />
    <Group title="Runbooks" items={docs} cited={cited} />
  </section>;
}

function Group({ title, items, cited }) {
  if (!items.length) return null;
  return <>
    <h3 className="group-title">{title}</h3>
    {items.map(item => (
      <details key={item.id} id={`evidence-${item.id}`} open={cited.includes(item.id) && item.source !== "search_docs"}>
        <summary>
          <span>{item.error && <span className="badge error">error</span>} {item.title}</span>
          <code className={cited.includes(item.id) ? "cited" : ""}>{item.id}</code>
        </summary>
        <pre>{item.detail}</pre>
        {item.data?.url && <a href={item.data.url} target="_blank" rel="noreferrer">Upstream reference ↗</a>}
      </details>
    ))}
  </>;
}
