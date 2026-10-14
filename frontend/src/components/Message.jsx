export default function Message({ diagnosis }) {
  if (!diagnosis) return null;
  return <section className="result">
    <p className="section-label">Finding</p><h2>{diagnosis.summary}</h2>
    <h3>What to do next</h3><ol>{diagnosis.suggested_actions.map(item => <li key={item}>{item}</li>)}</ol>
    {diagnosis.limitations?.map(item => <p className="warning" key={item}>{item}</p>)}
  </section>;
}
