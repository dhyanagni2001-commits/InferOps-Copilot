export default function Message({ diagnosis }) {
  if (!diagnosis) return null;
  return <section className="answer">
    <h2>Diagnosis</h2><p>{diagnosis.summary}</p>
    <h3>Suggested actions</h3><ol>{diagnosis.suggested_actions.map(item => <li key={item}>{item}</li>)}</ol>
    {diagnosis.limitations?.map(item => <p className="warning" key={item}>{item}</p>)}
  </section>;
}
