import { useEffect, useRef, useState } from "react";

const WS_URL = "ws://localhost:8000/ws";

const FEATURES = [
  { key: "auto_chest", label: "Auto Coffre", desc: "Ouvre les coffres en attente (1 clic = 1 coffre)" },
  { key: "auto_synthesis", label: "Auto Synthèse", desc: "Fusionne gris/vert/bleu uniquement, jamais violet+" },
];

export default function App() {
  const [connected, setConnected] = useState(false);
  const [running, setRunning] = useState(false);
  const [features, setFeatures] = useState({});
  const [counters, setCounters] = useState({});
  const [settings, setSettings] = useState({});
  const [logs, setLogs] = useState([]);
  const wsRef = useRef(null);
  const logEndRef = useRef(null);

  useEffect(() => {
    let alive = true;
    function connect() {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;
      ws.onopen = () => alive && setConnected(true);
      ws.onclose = () => { if (alive) { setConnected(false); setTimeout(connect, 1500); } };
      ws.onmessage = (e) => {
        const d = JSON.parse(e.data);
        if (d.type === "state") {
          setRunning(d.running);
          setFeatures(d.features || {});
          setCounters(d.counters || {});
          setSettings(d.settings || {});
        } else if (d.type === "log") {
          setLogs((p) => [...p.slice(-400), d.msg]);
        }
      };
    }
    connect();
    return () => { alive = false; wsRef.current?.close(); };
  }, []);

  useEffect(() => { logEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [logs]);

  const send = (o) => wsRef.current?.send(JSON.stringify(o));
  const toggle = (k) => send({ cmd: "toggle", feature: k, enabled: !features[k] });

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="logo">⚡</span>
          <div><h1>TBH AFK Bot</h1><p>Auto-farming nocturne</p></div>
        </div>
        <div className={`status ${connected ? "ok" : "off"}`}>
          <span className="dot" /> {connected ? "Connecté" : "Hors ligne"}
        </div>
      </header>

      {settings.calibrated === false && (
        <div className="banner">⚠ Géométrie non calibrée — lance <code>python calibrate.py grab</code> et renseigne les grilles dans <code>config.py</code> avant la synthèse.</div>
      )}

      <section className="cards">
        {FEATURES.map((f) => (
          <div className={`card ${features[f.key] ? "active" : ""}`} key={f.key}>
            <div className="card-text">
              <h3>{f.label} <span className="count">{counters[f.key] ?? 0}</span></h3>
              <p>{f.desc}</p>
            </div>
            <button className={`switch ${features[f.key] ? "on" : ""}`}
              onClick={() => toggle(f.key)} disabled={!connected}>
              <span className="knob" />
            </button>
          </div>
        ))}
      </section>

      <section className="settings">
        <label className="field">
          <span>Durée max (min)</span>
          <input type="number" min="0" defaultValue={settings.max_runtime_minutes ?? 600}
            disabled={!connected}
            onBlur={(e) => send({ cmd: "set_max_runtime", value: e.target.value })} />
        </label>
        <label className="field check">
          <input type="checkbox" checked={!!settings.debug} disabled={!connected}
            onChange={(e) => send({ cmd: "set_debug", value: e.target.checked })} />
          <span>Mode debug</span>
        </label>
        <div className="grades">
          Grades fusionnés : {(settings.allowed_grades || []).join(" · ") || "—"}
        </div>
      </section>

      <section className="controls">
        <button className={`run-btn ${running ? "stop" : "start"}`} disabled={!connected}
          onClick={() => send({ cmd: running ? "stop" : "start" })}>
          {running ? "■  Arrêter" : "▶  Démarrer"}
        </button>
        <span className={`run-state ${running ? "live" : ""}`}>{running ? "En cours" : "Arrêté"}</span>
      </section>

      <section className="console">
        <div className="console-head">Journal</div>
        <div className="console-body">
          {logs.length === 0 && <div className="empty">En attente…</div>}
          {logs.map((l, i) => <div className="line" key={i}>{l}</div>)}
          <div ref={logEndRef} />
        </div>
      </section>

      <footer className="warn">Failsafe : souris dans le coin haut-gauche, ou Ctrl+Alt+K, pour tout stopper.</footer>
    </div>
  );
}
