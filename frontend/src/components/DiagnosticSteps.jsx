export default function DiagnosticSteps({ status }) {
  return status ? <p className="status"><span className="pulse" /> {status}</p> : null;
}
