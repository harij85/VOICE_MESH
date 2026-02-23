export function createWsClient({ url, onScene, onStatus }) {
  let ws = null;
  let retryMs = 500;

  function connect() {
    onStatus?.(`ws connecting: ${url}`);
    ws = new WebSocket(url);

    ws.onopen = () => {
      retryMs = 500;
      onStatus?.("ws connected");
      ws.send(JSON.stringify({ type: "hello", role: "renderer", version: "0.1.0" }));
    };

    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === "scene") onScene?.(msg.scene);
      } catch (e) {
        onStatus?.(`ws parse error: ${String(e)}`);
      }
    };

    ws.onclose = () => {
      onStatus?.(`ws closed; retrying in ${retryMs}ms`);
      setTimeout(connect, retryMs);
      retryMs = Math.min(5000, retryMs * 1.5);
    };

    ws.onerror = () => {
      // let onclose handle retry
    };
  }

  connect();

  return {
    sendCommand(text) {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "command", text, source: "renderer" }));
      }
    }
  };
}