// Read POSTed server-sent events without an extra browser dependency.
export async function diagnose(payload, token, onEvent) {
  console.info("diagnosis request started", { namespace: payload.namespace, workload: payload.workload.name });
  const response = await fetch("/api/diagnose", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error((await response.json()).detail || "Request failed");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() || "";
    for (const block of blocks) {
      const event = block.match(/^event: (.+)$/m)?.[1];
      const data = block.match(/^data: (.+)$/m)?.[1];
      if (event && data) onEvent(event, JSON.parse(data));
    }
    if (done) break;
  }
  console.info("diagnosis request completed");
}
