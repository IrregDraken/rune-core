import { useEffect, useState } from "react";
import { getState, sendMessage } from "./api";

type View = "home" | "chat" | "memory" | "goals" | "actions" | "activity" | "settings";

type RuneState = {
  identity?: { name: string; role: string };
  current_goal?: string | null;
  node?: { platform?: string; hostname?: string; capabilities?: string[]; observation?: { process_count?: number; status?: string } };
  shell?: { mode?: string; island_message?: string | null; workspaces?: { id: string; name: string; active: boolean }[] };
  windows?: { hwnd: number; pid: number; title: string; foreground?: boolean }[];
};

const nav: { id: View; label: string; icon: string }[] = [
  { id: "home", label: "Home", icon: "⌂" },
  { id: "chat", label: "Chat", icon: "◌" },
  { id: "memory", label: "Memory", icon: "◈" },
  { id: "goals", label: "Goals", icon: "◎" },
  { id: "actions", label: "Actions", icon: "↗" },
  { id: "activity", label: "Activity", icon: "≋" },
  { id: "settings", label: "Settings", icon: "⚙" },
];

const activity = [
  ["17:04:12", "Input received", "You asked RUNE to continue the build.", "input"],
  ["17:04:13", "Context assembled", "Active project context loaded.", "context"],
  ["17:04:13", "Decision", "Continue dashboard construction.", "decision"],
  ["17:04:14", "Action", "Repository write requested.", "action"],
];

function App() {
  const [view, setView] = useState<View>("home");
  const [message, setMessage] = useState("");
  const [runtimeOnline, setRuntimeOnline] = useState(false);
  const [state, setState] = useState<RuneState | null>(null);
  const [error, setError] = useState("");
  const [windows, setWindows] = useState<RuneState["windows"]>([]);
  const [messages, setMessages] = useState([
    { from: "rune", text: "I'm online. The runtime is still under construction, but the control surface is taking shape." },
  ]);

  useEffect(() => {
    let mounted = true;
    const refresh = async () => {
      try {
        const next = await getState();
        if (mounted) {
          setState(next);
          setRuntimeOnline(true);
          setWindows(next.windows ?? []);
          setError("");
        }
      } catch (err) {
        if (mounted) {
          setRuntimeOnline(false);
          setError(err instanceof Error ? err.message : "RUNE API unavailable");
        }
      }
    };
    refresh();
    const timer = window.setInterval(refresh, 3000);
    return () => {
      mounted = false;
      window.clearInterval(timer);
    };
  }, []);

  const send = async () => {
    const trimmed = message.trim();
    if (!trimmed) return;
    setMessages((current) => [...current, { from: "you", text: trimmed }]);
    setMessage("");
    try {
      const response = await sendMessage(trimmed);
      setMessages((current) => [...current, { from: "rune", text: response }]);
    } catch (err) {
      setMessages((current) => [...current, { from: "rune", text: err instanceof Error ? err.message : "RUNE could not respond." }]);
    }
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><img src="/rune-glyph.svg" alt="" /></div>
          <div>
            <strong>RUNE</strong>
            <span>persistent intelligence</span>
          </div>
        </div>

        <div className="nav-label">WORKSPACE</div>
        <nav>
          {nav.map((item) => (
            <button
              key={item.id}
              className={view === item.id ? "nav-item active" : "nav-item"}
              onClick={() => setView(item.id)}
            >
              <span className="nav-icon">{item.icon}</span>
              <span>{item.label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="status-dot" />
          <div>
            <strong>Core online</strong>
            <span>{runtimeOnline ? "Local runtime" : "Start API to connect"}</span>
          </div>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <RuneIsland state={state} online={runtimeOnline} />
          <div>
            <span className="eyebrow">RUNE / CONTROL CENTER</span>
            <h1>{titleFor(view)}</h1>
          </div>
          <WorkspaceBar workspaces={state?.shell?.workspaces ?? []} />
          <div className="top-status">
            <span className={runtimeOnline ? "pulse" : "pulse offline"} /> {runtimeOnline ? "Runtime healthy" : "Runtime disconnected"}
            <span className="divider" />
            <span className="model-chip">MODEL · LOCAL</span>
          </div>
        </header>

        {view === "home" && <Home onNavigate={setView} state={state} windows={windows ?? []} />}
        {view === "chat" && (
          <section className="content chat-view">
            <div className="panel conversation">
              <div className="panel-head">
                <div><span className="section-kicker">CONVERSATION</span><h2>Talk to RUNE</h2></div>
                <span className="live-chip">LIVE SURFACE</span>
              </div>
              <div className="messages">
                {messages.map((item, index) => (
                  <div className={item.from === "you" ? "message user" : "message"} key={index}>
                    <span className="message-label">{item.from === "you" ? "YOU" : "RUNE"}</span>
                    <p>{item.text}</p>
                  </div>
                ))}
              </div>
              <div className="composer">
                <input
                  value={message}
                  onChange={(event) => setMessage(event.target.value)}
                  onKeyDown={(event) => event.key === "Enter" && send()}
                  placeholder="Talk to RUNE..."
                />
                <button onClick={send}>Send ↗</button>
              </div>
            </div>
          </section>
        )}
        {view === "memory" && <Memory />}
        {view === "goals" && <Goals />}
        {view === "actions" && <Actions />}
        {view === "activity" && <Activity />}
        {view === "settings" && <Settings />}
      </main>
    </div>
  );
}

function RuneIsland({ state, online }: { state: RuneState | null; online: boolean }) {
  const mode = state?.shell?.mode ?? "ambient";
  const message = state?.shell?.island_message;
  return (
    <div className={online ? "rune-island online" : "rune-island"}>
      <span className="island-core"><img src="/rune-glyph.svg" alt="" /></span>
      <div className="island-copy">
        <strong>RUNE</strong>
        <span>{message ? message.replace("_", " ") : mode}</span>
      </div>
      <span className="island-signal" />
    </div>
  );
}

function titleFor(view: View) {
  return { home: "Good evening, Draken.", chat: "Conversation", memory: "Memory", goals: "Goals", actions: "Actions", activity: "Activity", settings: "System" }[view];
}

function WorkspaceBar({ workspaces }: { workspaces: { id: string; name: string; active: boolean }[] }) {\n  const activate = async (id: string) => {\n    try {\n      await fetch(`${import.meta.env.VITE_RUNE_API_URL ?? "http://127.0.0.1:8765"}/api/workspace`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ workspace_id: id }) });\n      window.location.reload();\n    } catch { /* runtime polling will surface connectivity */ }\n  };\n  return <div className="workspace-bar">{workspaces.map((workspace) => <button key={workspace.id} className={workspace.active ? "workspace-chip active" : "workspace-chip"} onClick={() => activate(workspace.id)}>{workspace.name}</button>)}</div>;\n}\n\nfunction Home({ onNavigate, state, windows }: { onNavigate: (view: View) => void; state: RuneState | null; windows: { hwnd: number; pid: number; title: string; foreground?: boolean }[] }) {
  return (
    <section className="content">
      <div className="hero-grid">
        <div className="hero-card panel">
          <span className="section-kicker">CURRENT STATE</span>
          <div className="orb"><div className="orb-core"><img src="/rune-glyph.svg" alt="" /></div></div>
          <h2>I'm here.</h2>
          <p>{state?.shell?.island_message ? `Command: ${state.shell.island_message}` : "RUNE is being built as a persistent intelligence, not a chat box. This shell is becoming its control surface."}</p>
          <button className="primary" onClick={() => onNavigate("chat")}>Open conversation <span>↗</span></button>
        </div>
        <div className="state-stack">
          <StateCard label="ACTIVE GOAL" value="Build RUNE" detail="Foundation + interface" />
          <StateCard label="MODEL" value="Local / replaceable" detail="Ollama boundary ready" />
          <StateCard label="MEMORY" value="SQLite" detail="Persistent event journal" />
        </div>
      </div>

      <div className="section-row">
        <div>
          <span className="section-kicker">LIVE CONTEXT</span>
          <h2>What RUNE knows right now</h2>
        </div>
        <button className="text-button" onClick={() => onNavigate("memory")}>View memory ↗</button>
      </div>
      <div className="cards-3">
        <InfoCard title="Node" value={state?.node?.platform ?? "Offline"} meta={state?.node?.hostname ?? "Connect RUNE runtime"} />
        <InfoCard title="Processes" value={String(state?.node?.observation?.process_count ?? "—")} meta="Observed by local node" />
        <InfoCard title="Shell" value={state?.shell?.mode ?? "ambient"} meta={state?.shell?.island_message ?? "Ready"} />
      </div>\n\n      <div className="section-row">\n        <div><span className="section-kicker">WINDOW AWARENESS</span><h2>What is open</h2></div>\n        <span className="live-chip">{windows.length} WINDOWS</span>\n      </div>\n      <div className="panel window-list">\n        {windows.length ? windows.slice(0, 8).map((window) => <div className={window.foreground ? "window-row foreground" : "window-row"} key={window.hwnd}><span className="window-dot" /><div><strong>{window.title}</strong><span>PID {window.pid} · HWND {window.hwnd}</span></div>{window.foreground && <em>FOREGROUND</em>}</div>) : <div className="empty-state">No window telemetry available from the current node.</div>}\n      </div>

      <div className="section-row">
        <div>
          <span className="section-kicker">RECENT ACTIVITY</span>
          <h2>Runtime trail</h2>
        </div>
        <button className="text-button" onClick={() => onNavigate("activity")}>Full activity ↗</button>
      </div>
      <div className="panel activity-list">
        {activity.map(([time, name, detail, kind]) => (
          <div className="activity-row" key={time + name}>
            <span className={"activity-icon " + kind}>{kind === "input" ? "↓" : kind === "decision" ? "◆" : kind === "action" ? "↗" : "◇"}</span>
            <div><strong>{name}</strong><span>{detail}</span></div>
            <time>{time}</time>
          </div>
        ))}
      </div>
    </section>
  );
}

function StateCard({ label, value, detail }: { label: string; value: string; detail: string }) {
  return <div className="panel state-card"><span className="section-kicker">{label}</span><strong>{value}</strong><span>{detail}</span></div>;
}
function InfoCard({ title, value, meta }: { title: string; value: string; meta: string }) {
  return <div className="panel info-card"><span>{title}</span><strong>{value}</strong><small>{meta}</small></div>;
}
function Memory() {
  return <section className="content"><div className="section-row"><div><span className="section-kicker">PERSISTENT CONTEXT</span><h2>Memory</h2></div><span className="live-chip">LOCAL SQLITE</span></div><div className="memory-grid"><div className="panel large-panel"><h3>Working memory</h3><p className="muted">The active workspace RUNE can use while reasoning.</p><div className="memory-item"><span>project</span><strong>RUNE</strong></div><div className="memory-item"><span>current_goal</span><strong>Build the foundation</strong></div><div className="memory-item"><span>interface</span><strong>Dashboard</strong></div></div><div className="panel large-panel"><h3>Long-term memory</h3><p className="muted">Persistent storage and retrieval will expand this surface.</p><div className="empty-state">No semantic memory index connected yet.</div></div></div></section>;
}
function Goals() {
  return <section className="content"><div className="section-row"><div><span className="section-kicker">DIRECTION</span><h2>Goals</h2></div></div><div className="goal panel"><div><span className="goal-number">01</span><h3>Build RUNE</h3><p>Persistent intelligence runtime with memory, reasoning, tools, agency and verification.</p></div><span className="goal-status">ACTIVE</span></div></section>;
}
function Actions() {
  return <section className="content"><div className="section-row"><div><span className="section-kicker">AGENCY</span><h2>Actions</h2></div></div><div className="panel"><div className="action-row"><div><span className="section-kicker">READY</span><h3>No external action pending</h3><p className="muted">Approved actions will appear here before and after execution.</p></div><span className="verified-badge">VERIFICATION REQUIRED</span></div></div></section>;
}
function Activity() {
  return <section className="content"><div className="section-row"><div><span className="section-kicker">EVENT JOURNAL</span><h2>Activity</h2></div></div><div className="panel activity-list">{activity.concat(activity).map(([time, name, detail, kind], index) => <div className="activity-row" key={index}><span className={"activity-icon " + kind}>◆</span><div><strong>{name}</strong><span>{detail}</span></div><time>{time}</time></div>)}</div></section>;
}
function Settings() {
  return <section className="content"><div className="section-row"><div><span className="section-kicker">RUNTIME</span><h2>System</h2></div></div><div className="settings-grid"><div className="panel setting"><span>Runtime</span><strong>Local</strong><small>Persistent process on this machine</small></div><div className="panel setting"><span>Model provider</span><strong>Ollama</strong><small>Replaceable ModelProvider boundary</small></div><div className="panel setting"><span>Storage</span><strong>SQLite</strong><small>Event journal</small></div><div className="panel setting"><span>Network</span><strong>Optional retrieval</strong><small>Fresh information can be injected into context</small></div></div></section>;
}

export default App;
