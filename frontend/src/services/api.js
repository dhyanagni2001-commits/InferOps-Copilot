// Read POSTed Server-Sent Events with streaming fetch; EventSource cannot send a body or headers.
export async function diagnose(payload, token, onEvent, signal) {
  const response = await fetch("/api/diagnose", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
    signal,
  });
  if (!response.ok) throw new Error(await errorMessage(response));

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
    const blocks = buffer.split("\n\n");
    buffer = done ? "" : blocks.pop() || "";
    for (const block of blocks) {
      const event = block.match(/^event: (.+)$/m)?.[1];
      const data = block.match(/^data: (.+)$/m)?.[1];
      if (event && data) onEvent(event, JSON.parse(data));
    }
    if (done) break;
  }
}

export async function loadConfig() {
  const response = await fetch("/api/config");
  if (!response.ok) throw new Error(`config request failed (${response.status})`);
  return response.json();
}

async function errorMessage(response) {
  try {
    const body = await response.json();
    if (Array.isArray(body.detail)) return body.detail.map(item => `${item.loc?.slice(-1)[0]}: ${item.msg}`).join("; ");
    return body.detail || `Request failed (${response.status})`;
  } catch {
    return `Request failed (${response.status})`;
  }
}
