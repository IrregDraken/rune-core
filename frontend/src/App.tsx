import { useEffect, useState } from "react";
import {
  activateWorkspace,
  controlWindow,
  getActivity,
  getState,
  getTools,
  getVoice,
  sendMessage,
  setGoal,
  rememberMemory,
  createPlan,
  verifyPlanStep,
  type ActivityEvent,
  type RuneState,
  type ToolSpec,
  type VoiceStatus,
  type WindowInfo,
} from "./api";

type View = "home" | "chat" | "memory" | "goals" | "actions" | "activity" | "system";

const nav: { id: View; label: string; icon: string }[] = [
  { id: "home", label: "Overview", icon: "⌂" },
  { id: "chat", label: "Conversation", icon: "◌" },
  { id: "memory", label: "Memory", icon: "◈" },
  { id: "goals", label: "Goals", icon: "◎" },
  { id: "actions", label: "Actions", icon: "↗" },
  { id: "activity", label: "Activity", icon: "≋" },
  { id: "system", label: "System", icon: "⌘" },
];

const fallbackActivity: ActivityEvent[] = [];

function App() {
  const [view, setView] = useState<View>("home");
  const [state, setState] = useState<RuneState | null>(null);
  const [activity, setActivity] = useState<ActivityEvent[]>(fallbackActivity);
  const [tools, setTools] = useState<ToolSpec[]>([]);
  const [voice, setVoice] = useState<VoiceStatus>({
    wake_word: false,
    speech_to_text: false,
    text_to_speech: false,
    speaker_verifier: false,
  });
  const [online, setOnline] = useState(false);
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [activityFilter, setActivityFilter] = useState("ALL");
  const [telemetryHistory, setTelemetryHistory] = useState<number[]>([]);

  const refresh = async () => {
    try {
      setRefreshing(true);
      const [next, trail, toolData, voiceData] = await Promise.all([
        getState(),
        getActivity(),
        getTools(),
        getVoice(),
      ]);
      setState(next);
      const load = next.node?.observation?.system?.memory_load_percent;
      if (typeof load === "number") setTelemetryHistory((items) => [...items.slice(-23), load]);
      setActivity(trail.events);
      setTools(toolData.tools);
      setVoice(voiceData);
      setOnline(true);
      setError("");
    } catch (err) {
      setOnline(false);
      setError(err instanceof Error ? err.message : "RUNE API unavailable");
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 4000);
    return () => window.clearInterval(timer);
  }, []);

  const windows = state?.node?.observation?.windows ?? [];
  const activeWorkspace = state?.shell?.workspaces?.find((item) => item.active)?.name ?? "Home";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><img src="/rune-glyph.svg" alt="RUNE" /></div>
          <div className="brand-copy">
            <strong>RUNE</strong>
            <span>persistent intelligence</span>
          </div>
        </div>

        <div className="nav-label">COMMAND CENTER</div>
        <nav>
          {nav.map((item) => (
            <button key={item.id} className={view === item.id ? "nav-item active" : "nav-item"} onClick={() => setView(item.id)}>
              <span className="nav-icon">{item.icon}</span>
              <span>{item.label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-node">
          <span className={online ? "status-dot" : "status-dot offline"} />
          <div>
            <strong>{online ? "Core online" : "Core offline"}</strong>
            <span>{state?.node?.hostname ?? "Local runtime"}</span>
          </div>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <RuneIsland state={state} online={online} />
          <div className="heading">
            <span className="eyebrow">RUNE / {activeWorkspace.toUpperCase()}</span>
            <h1>{titleFor(view)}</h1>
          </div>
          <div className="top-actions">
            <button className="refresh-button" onClick={() => void refresh()} aria-label="Refresh" disabled={refreshing}>
              {refreshing ? "SYNCING" : "SYNC"}
            </button>
            <span className={online ? "pulse" : "pulse offline"} />
            <span className="runtime-label">{online ? "CONNECTED" : "DISCONNECTED"}</span>
          </div>
        </header>

        {error && <div className="connection-banner"><span>●</span> {error}<button onClick={() => void refresh()}>Retry</button></div>}

        <WorkspaceBar state={state} onActivated={() => void refresh()} />

        {view === "home" && <Home state={state} windows={windows} activity={activity} telemetry={telemetryHistory} onNavigate={setView} />}
        {view === "chat" && <Chat onSent={() => void refresh()} />}
        {view === "memory" && <Memory state={state} />}
        {view === "goals" && <Goals state={state} onChanged={() => void refresh()} />}
        {view === "actions" && <Actions state={state} tools={tools} windows={windows} />}
        {view === "activity" && <Activity events={activity} filter={activityFilter} onFilter={setActivityFilter} />}
        {view === "system" && <System state={state} tools={tools} voice={voice} />}
      </main>
    </div>
  );
}

function WorkspaceBar({ state, onActivated }: { state: RuneState | null; onActivated: () => void }) {
  const [switching, setSwitching] = useState("");
  const workspaces = state?.shell?.workspaces ?? [];

  const select = async (id: string) => {
    if (switching || workspaces.find((item) => item.id === id)?.active) return;
    setSwitching(id);
    try {
      await activateWorkspace(id);
      onActivated();
    } catch (err) {
      console.error(err);
    } finally {
      setSwitching("");
    }
  };

  if (!workspaces.length) return null;

  return (
    <div className="workspace-bar" aria-label="RUNE workspaces">
      <span className="workspace-label">WORKSPACE</span>
      <div className="workspace-tabs">
        {workspaces.map((workspace) => (
          <button
            key={workspace.id}
            className={workspace.active ? "workspace-tab active" : "workspace-tab"}
            onClick={() => void select(workspace.id)}
            disabled={Boolean(switching)}
          >
            <span className="workspace-status" />
            {workspace.name}
          </button>
        ))}
      </div>
      {switching && <span className="workspace-sync">SWITCHING</span>}
    </div>
  );
}

function RuneIsland({ state, online }: { state: RuneState | null; online: boolean }) {
  const mode = state?.shell?.mode?.replaceAll("_", " ") ?? "ambient";
  const message = state?.shell?.island_message;
  return (
    <div className={online ? "rune-island online" : "rune-island"}>
      <span className="island-core"><img src="/rune-glyph.svg" alt="" /></span>
      <div className="island-copy"><strong>RUNE</strong><span>{message || mode}</span></div>
      <span className="island-signal" />
    </div>
  );
}

function titleFor(view: View) {
  return {
    home: "Good evening, Draken.",
    chat: "Conversation",
    memory: "Memory",
    goals: "Goals",
    actions: "Agency & tools",
    activity: "Activity",
    system: "System",
  }[view];
}

function Home({ state, windows, activity, telemetry, onNavigate }: { state: RuneState | null; windows: WindowInfo[]; activity: ActivityEvent[]; telemetry: number[]; onNavigate: (view: View) => void }) {
  const memoryLoad = state?.node?.observation?.system?.memory_load_percent;
  const activeGoal = state?.current_goal ?? "Build RUNE";
  return (
    <section className="content">
      <div className="hero-grid">
        <div className="hero-card panel">
          <div className="hero-topline"><span className="section-kicker">CURRENT STATE</span><span className="live-chip">PERSISTENT CORE</span></div>
          <div className="orb"><div className="orb-ring ring-one" /><div className="orb-ring ring-two" /><div className="orb-core"><img src="/rune-glyph.svg" alt="" /></div></div>
          <h2>{state?.shell?.island_message || "I'm here."}</h2>
          <p>RUNE is the persistent intelligence layer above the machine. This interface is its visible command surface.</p>
          <button className="primary" onClick={() => onNavigate("chat")}>Open conversation <span>↗</span></button>
        </div>

        <div className="state-stack">
          <StateCard label="ACTIVE GOAL" value={activeGoal} detail="Current runtime direction" />
          <StateCard label="NODE" value={state?.node?.platform ?? "Offline"} detail={state?.node?.hostname ?? "Connect a RUNE node"} />
          <StateCard label="MEMORY LOAD" value={memoryLoad != null ? `${memoryLoad}%` : "—"} detail="Observed system telemetry" />
        </div>
      </div>

      <SectionHeader eyebrow="LIVE CONTEXT" title="RUNE's current awareness" action="Memory ↗" onClick={() => onNavigate("memory")} />
      <div className="cards-3"><TelemetryCard values={telemetry} current={memoryLoad} />
        <InfoCard title="WINDOWS" value={String(windows.length)} meta="Visible top-level windows" />
        <InfoCard title="PROCESSES" value={String(state?.node?.observation?.process_count ?? "—")} meta="Observed by local node" />
        <InfoCard title="AVAILABLE RAM" value={state?.node?.observation?.system?.memory_available_mb ? `${Math.round(state.node.observation.system.memory_available_mb / 1024 * 10) / 10} GB` : "—"} meta="Windows telemetry" />
      </div>

      <SectionHeader eyebrow="WINDOW AWARENESS" title="What's open" action={windows.length ? `${windows.length} WINDOWS` : "NO WINDOWS"} />
      <WindowList windows={windows} compact />

      <SectionHeader eyebrow="RECENT ACTIVITY" title="Runtime trail" action="Full activity ↗" onClick={() => onNavigate("activity")} />
      <ActivityList events={activity.slice(-5).reverse()} />
    </section>
  );
}

function Chat({ onSent }: { onSent: () => void }) {
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [messages, setMessages] = useState<{ from: "rune" | "you"; text: string; time: number }[]>([
    { from: "rune", text: "I'm online. Talk to me.", time: Date.now() },
  ]);

  const send = async () => {
    const text = message.trim();
    if (!text || sending) return;
    setMessages((items) => [...items, { from: "you", text, time: Date.now() }]);
    setMessage("");
    setSending(true);
    try {
      const response = await sendMessage(text);
      onSent();
      setMessages((items) => [...items, { from: "rune", text: response, time: Date.now() }]);
    } catch (err) {
      setMessages((items) => [...items, { from: "rune", text: err instanceof Error ? err.message : "RUNE could not respond." }]);
    } finally {
      setSending(false);
    }
  };

  return (
    <section className="content chat-view">
      <div className="panel conversation">
        <div className="panel-head"><div><span className="section-kicker">LIVE CHANNEL</span><h2>Conversation</h2></div><span className="live-chip">LOCAL</span></div>
        <div className="messages">
          <div className="conversation-status"><span className="status-dot" /> SESSION ACTIVE · LOCAL RUNTIME</div>
          {messages.map((item, index) => (
            <div className={item.from === "you" ? "message user" : "message"} key={index}>
              <span className="message-label">{item.from === "you" ? "YOU" : "RUNE"} <time>{new Date(item.time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</time></span>
              <p>{item.text}</p>
            </div>
          ))}
          {sending && <div className="message"><span className="message-label">RUNE</span><p className="typing">processing <i /> <i /> <i /></p></div>}
        </div>
        <div className="composer">
          <input value={message} onChange={(event) => setMessage(event.target.value)} onKeyDown={(event) => event.key === "Enter" && void send()} placeholder="Say something to RUNE..." />
          <button onClick={() => void send()} disabled={sending}>{sending ? "..." : "Send ↗"}</button>
        </div>
      </div>
    </section>
  );
}

function Memory({ state }: { state: RuneState | null }) {
  const entries = Object.entries(state?.working_memory ?? {});
  const contextEntries = Object.entries(state?.active_context ?? {});
  const decisionEntries = Object.entries(state?.last_decision ?? {});
  const assessment = state?.cognition?.assessment;
  return <section className="content">
    <SectionHeader eyebrow="PERSISTENT CONTEXT" title="Memory" action="LOCAL SQLITE" />
    <div className="memory-grid">
      <div className="panel large-panel">
        <div className="panel-title"><h3>Working memory</h3><span>{entries.length} ITEMS</span></div>
        <p className="muted">The bounded context RUNE can actively carry while reasoning.</p>
        {entries.length ? entries.map(([key, value]) => <div className="memory-item" key={key}><span>{key}</span><strong>{displayValue(value)}</strong></div>) : <div className="empty-state">No working-memory entries yet.</div>}
      </div>
      <div className="panel large-panel">
        <div className="panel-title"><h3>Active context</h3><span>{contextEntries.length} SIGNALS</span></div>
        <p className="muted">Context currently available to the runtime before it decides what to do next.</p>
        {contextEntries.length ? contextEntries.map(([key, value]) => <div className="memory-item" key={key}><span>{key}</span><strong>{displayValue(value)}</strong></div>) : <div className="empty-state">No active context signals.</div>}
        <div className="decision-strip"><span className="section-kicker">LAST DECISION</span><strong>{decisionEntries.length ? displayValue(state?.last_decision?.status) : "No decision yet"}</strong></div>
      </div>
    </div>
    <SectionHeader eyebrow="LONG-TERM MEMORY" title="Recalled context" action={`${state?.long_term_memory?.length ?? 0} RECORDS`} />
    <div className="panel memory-recall">
      {(state?.long_term_memory ?? []).slice(-6).reverse().map((record) => (
        <div className="memory-item" key={record.key}><span>{record.key}</span><strong>{displayValue(record.value)}</strong></div>
      ))}
      {!state?.long_term_memory?.length && <div className="empty-state">No long-term memories recalled yet.</div>}
    </div>
    <MemoryWriter />
    <SectionHeader eyebrow="PLANNING" title="Active plan" action={state?.active_plan?.status?.toUpperCase() ?? "NONE"} />
    <div className="panel plan-panel">
      {state?.active_plan ? state.active_plan.steps.map((step) => (
        <div className="plan-step" key={step.id}><span className={`plan-dot ${step.status}`} /><div><strong>{step.description}</strong><span>{step.status}</span></div></div>
      )) : <div className="empty-state">No active plan.</div>}
    </div>
    <SectionHeader eyebrow="COGNITION" title="Current appraisal" action={state?.cognition?.mode?.toUpperCase() ?? "OBSERVE"} />
    <CognitionPulse assessment={assessment} />
    <div className="cognition-grid">
      <CognitionMetric label="ATTENTION" value={assessment?.attention_score} />
      <CognitionMetric label="URGENCY" value={assessment?.urgency} />
      <CognitionMetric label="UNCERTAINTY" value={assessment?.uncertainty} />
      <CognitionMetric label="SIGNIFICANCE" value={assessment?.significance} />
      <CognitionMetric label="CONTROL" value={assessment?.control} />
      <CognitionMetric label="CONSEQUENCE" value={assessment?.consequence} />
      <CognitionMetric label="GOAL PRESSURE" value={assessment?.goal_pressure} />
      <CognitionMetric label="PREDICTION ERROR" value={assessment?.prediction_error} />
    </div>
  </section>;
}

function MemoryWriter() {
  const [text, setText] = useState("");
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState("");

  const save = async () => {
    const value = text.trim();
    if (!value || saving) return;
    setSaving(true);
    setNotice("");
    try {
      await rememberMemory(`note:${Date.now()}`, value, "episodic", 0.85, ["explicit", "user"]);
      setText("");
      setNotice("Memory stored.");
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Memory could not be stored.");
    } finally {
      setSaving(false);
    }
  };

  return <div className="panel memory-writer">
    <div className="panel-title"><h3>Remember something</h3><span>EXPLICIT MEMORY</span></div>
    <div className="inline-form">
      <input value={text} onChange={(event) => setText(event.target.value)} onKeyDown={(event) => event.key === "Enter" && void save()} placeholder="Tell RUNE something worth remembering..." />
      <button className="primary" onClick={() => void save()} disabled={saving}>{saving ? "SAVING" : "REMEMBER"}</button>
    </div>
    {notice && <p className="form-notice">{notice}</p>}
  </div>;
}

function CognitionPulse({ assessment }: { assessment?: RuneState["cognition"]["assessment"] }) {
  const score = assessment?.attention_score ?? 0;
  const urgency = assessment?.urgency ?? 0;
  const uncertainty = assessment?.uncertainty ?? 0;
  const pressure = Math.round(((score + urgency + uncertainty) / 3) * 100);
  const stateLabel = urgency > 0.72 ? "HIGH PRIORITY" : score > 0.58 ? "FOCUSED" : uncertainty > 0.62 ? "SEEKING CLARITY" : "AMBIENT";
  return <div className="panel cognition-pulse">
    <div className="pulse-orb"><span /><span /><img src="/rune-glyph.svg" alt="" /></div>
    <div className="pulse-copy"><span className="section-kicker">COGNITIVE STATE</span><strong>{stateLabel}</strong><p>Attention pressure {pressure}% · attention, urgency and uncertainty combined</p></div>
    <div className="pulse-score"><span>{pressure}</span><small>%</small></div>
  </div>;
}

function CognitionMetric({ label, value }: { label: string; value?: number }) {
  const percentage = value == null ? 0 : Math.round(value * 100);
  return <div className="panel cognition-metric"><div className="metric-top"><span>{label}</span><strong>{value == null ? "—" : `${percentage}%`}</strong></div><div className="metric-track"><span style={{ width: `${percentage}%` }} /></div></div>;
}
function displayValue(value: unknown) {
  if (value == null) return "—";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return String(value);
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function Goals({ state, onChanged }: { state: RuneState | null; onChanged: () => void }) {
  const goal = state?.current_goal ?? "Build RUNE";
  const [draft, setDraft] = useState(goal);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState("");
  const [steps, setSteps] = useState("");
  const plan = state?.active_plan;

  useEffect(() => setDraft(goal), [goal]);

  const save = async () => {
    const value = draft.trim();
    if (!value || saving) return;
    setSaving(true);
    setNotice("");
    try {
      await setGoal(value);
      setNotice("Goal persisted to RUNE memory.");
      onChanged();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Goal could not be saved.");
    } finally {
      setSaving(false);
    }
  };

  const buildPlan = async () => {
    const cleanSteps = steps.split("\n").map((item) => item.trim()).filter(Boolean);
    if (!draft.trim() || !cleanSteps.length || saving) return;
    setSaving(true);
    setNotice("");
    try {
      await createPlan(draft.trim(), cleanSteps);
      setSteps("");
      setNotice("Plan created and persisted.");
      onChanged();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Plan could not be created.");
    } finally {
      setSaving(false);
    }
  };

  const verify = async (stepId: string) => {
    try {
      await verifyPlanStep(stepId, true, { source: "command-center" });
      setNotice("Step verified. RUNE advanced the plan.");
      onChanged();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Step could not be verified.");
    }
  };

  return <section className="content">
    <SectionHeader eyebrow="DIRECTION" title="Goals" action="PERSISTENT" />
    <div className="goal panel">
      <div>
        <span className="goal-number">01</span>
        <h3>{goal}</h3>
        <p>Active direction used by cognition when assessing significance and attention.</p>
      </div>
      <span className="goal-status">ACTIVE</span>
    </div>
    <div className="panel goal-editor">
      <div className="panel-title"><h3>Set active goal</h3><span>AUTHENTICATED WRITE</span></div>
      <div className="inline-form">
        <input value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => event.key === "Enter" && void save()} placeholder="What should RUNE optimize for?" />
        <button className="primary" onClick={() => void save()} disabled={saving}>{saving ? "SAVING" : "SAVE GOAL"}</button>
      </div>
    </div>
    <div className="panel goal-editor">
      <div className="panel-title"><h3>Build a verified plan</h3><span>{plan ? plan.status.toUpperCase() : "NONE"}</span></div>
      <textarea className="plan-input" value={steps} onChange={(event) => setSteps(event.target.value)} placeholder={"One step per line\nBuild the feature\nRun tests\nVerify the result"} rows={5} />
      <button className="primary" onClick={() => void buildPlan()} disabled={saving}>CREATE PLAN</button>
      {plan && <div className="plan-editor-list">
        {plan.steps.map((step) => <div className="plan-step" key={step.id}>
          <span className={`plan-dot ${step.status}`} />
          <div><strong>{step.description}</strong><span>{step.status}</span></div>
          {(step.status === "ready" || step.status === "executing") && <button className="text-button" onClick={() => void verify(step.id)}>VERIFY</button>}
        </div>)}
      </div>}
    </div>
    {notice && <p className="form-notice">{notice}</p>}
  </section>;
}

function Actions({ state, tools, windows }: { state: RuneState | null; tools: ToolSpec[]; windows: WindowInfo[] }) {
  const [busy, setBusy] = useState<number | null>(null);
  const [notice, setNotice] = useState("");
  const runWindow = async (operation: string, hwnd: number, index: number) => {
    setBusy(index);
    setNotice("");
    try {
      await controlWindow(operation, hwnd);
      setNotice(`${operation} requested for window ${hwnd}.`);
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Action blocked.");
    } finally {
      setBusy(null);
    }
  };
  const authorized = Boolean(import.meta.env.VITE_RUNE_SESSION_TOKEN);
  return <section className="content">
    <SectionHeader eyebrow="AGENCY" title="Actions" action={authorized ? "SESSION AUTHORIZED" : "READ-ONLY SESSION"} />
    {notice && <div className="notice">{notice}</div>}
    <div className="panel lifecycle-panel"><div className="lifecycle-step"><span>01</span><strong>DECISION</strong><em>{displayValue(state?.last_decision?.status ?? "—")}</em></div><div className="lifecycle-line" /><div className="lifecycle-step"><span>02</span><strong>ATTEMPT</strong><em>{displayValue(state?.last_action?.status ?? "—")}</em></div><div className="lifecycle-line" /><div className="lifecycle-step"><span>03</span><strong>VERIFICATION</strong><em>{displayValue(state?.last_action?.verified ?? "—")}</em></div></div>
    <div className="action-grid">
      <div className="panel action-panel">
        <div className="panel-title"><h3>Computer awareness</h3><span>{state?.node?.platform ?? "OFFLINE"}</span></div>
        <p className="muted">Window control is routed through RUNE's authorization and verification pipeline.</p>
        <WindowList windows={windows} onAction={runWindow} busyIndex={busy} />
      </div>
      <div className="panel action-panel">
        <div className="panel-title"><h3>Registered tools</h3><span>{tools.length} TOOLS</span></div>
        {tools.length ? tools.map((tool) => <div className="tool-row" key={tool.name}><span className={`risk-dot ${tool.risk}`} /><div><strong>{tool.name}</strong><span>{tool.description}</span></div>{tool.requires_authority && <em>AUTH</em>}</div>) : <div className="empty-state">No external tools registered.</div>}
      </div>
    </div>
  </section>;
}

function Activity({ events, filter, onFilter }: { events: ActivityEvent[]; filter: string; onFilter: (value: string) => void }) {
  const types = ["ALL", ...Array.from(new Set(events.map((event) => event.type)))];
  const filtered = filter === "ALL" ? events : events.filter((event) => event.type === filter);
  return <section className="content">
    <SectionHeader eyebrow="EVENT JOURNAL" title="Activity" action={filtered.length + " / " + events.length + " EVENTS"} />
    <div className="activity-filters">{types.map((type) => <button key={type} className={filter === type ? "filter-chip active" : "filter-chip"} onClick={() => onFilter(type)}>{type.replaceAll("_", " ")}</button>)}</div>
    <ActivityList events={[...filtered].reverse()} detailed />
  </section>;
}

function System({ state, tools, voice }: { state: RuneState | null; tools: ToolSpec[]; voice: VoiceStatus }) {
  const owner = state?.identity?.owner;
  const checks = [
    ["Runtime", Boolean(state), state?.node?.platform ?? "Offline"],
    ["Identity", Boolean(owner), owner?.assurance ?? "Unavailable"],
    ["Tools", true, `${tools.length} registered`],
    ["Wake word", voice.wake_word, voice.wake_word ? "Connected" : "Not connected"],
    ["Speech to text", voice.speech_to_text, voice.speech_to_text ? "Connected" : "Not connected"],
    ["Text to speech", voice.text_to_speech, voice.text_to_speech ? "Connected" : "Not connected"],
    ["Speaker verification", voice.speaker_verifier, voice.speaker_verifier ? "Connected" : "Not connected"],
  ];
  return <section className="content">
    <SectionHeader eyebrow="RUNTIME" title="System" action="LOCAL FIRST" />
    <div className="system-grid">
      <div className="panel system-card"><span className="section-kicker">OWNER CONTEXT</span><h3>{owner?.display_name ?? "Unknown"}</h3><p>{owner?.platform ?? "No node"} · {owner?.assurance ?? "unverified"}</p><code>{owner?.device_id ?? "No device identity"}</code></div>
      <div className="panel system-card"><span className="section-kicker">CAPABILITIES</span><div className="capability-list">{(state?.node?.capabilities ?? []).map((capability) => <span key={capability}>{capability}</span>)}</div></div>
    </div>
    <div className="system-checks">{checks.map(([name, ready, detail]) => <div className="panel check-row" key={String(name)}><span className={ready ? "check ok" : "check"}>{ready ? "✓" : "·"}</span><div><strong>{String(name)}</strong><span>{String(detail)}</span></div></div>)}</div>
  </section>;
}

function SectionHeader({ eyebrow, title, action, onClick }: { eyebrow: string; title: string; action?: string; onClick?: () => void }) {
  return <div className="section-row"><div><span className="section-kicker">{eyebrow}</span><h2>{title}</h2></div>{action && <button className="text-button" onClick={onClick}>{action}</button>}</div>;
}

function StateCard({ label, value, detail }: { label: string; value: string; detail: string }) {
  return <div className="panel state-card"><span className="section-kicker">{label}</span><strong>{value}</strong><span>{detail}</span></div>;
}

function TelemetryCard({ values, current }: { values: number[]; current?: number }) {
  const points = values.length ? values : [current ?? 0];
  const max = Math.max(100, ...points);
  const width = 240;
  const height = 54;
  const path = points.map((value, index) => {
    const x = points.length === 1 ? width : (index / (points.length - 1)) * width;
    const y = height - (value / max) * height;
    return (index ? "L" : "M") + x.toFixed(1) + " " + y.toFixed(1);
  }).join(" ");
  return <div className="panel telemetry-card"><div className="telemetry-head"><span>MEMORY TREND</span><strong>{current == null ? "—" : current + "%"}</strong></div><svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" aria-label="Memory telemetry trend"><path d={path} fill="none" /></svg><small>Last {points.length} observations</small></div>;
}

function InfoCard({ title, value, meta }: { title: string; value: string; meta: string }) {
  return <div className="panel info-card"><span>{title}</span><strong>{value}</strong><small>{meta}</small></div>;
}

function WindowList({ windows, compact = false, onAction, busyIndex }: { windows: WindowInfo[]; compact?: boolean; onAction?: (operation: string, hwnd: number, index: number) => void; busyIndex?: number | null }) {
  if (!windows.length) return <div className="empty-state">No window telemetry available from the current node.</div>;
  return <div className={compact ? "panel window-list" : "window-list inline-list"}>{windows.slice(0, compact ? 8 : 12).map((item, index) => <div className={item.foreground ? "window-row foreground" : "window-row"} key={item.hwnd}>
    <span className="window-dot" />
    <div><strong>{item.title || "Untitled window"}</strong><span>PID {item.pid} · HWND {item.hwnd}</span></div>
    {onAction ? <div className="window-actions"><button disabled={busyIndex === index} onClick={() => onAction("focus", item.hwnd, index)}>{busyIndex === index ? "..." : "Focus"}</button><button disabled={busyIndex === index} onClick={() => onAction("minimize", item.hwnd, index)}>Min</button></div> : item.foreground ? <em>FOREGROUND</em> : null}
  </div>)}</div>;
}

function ActivityList({ events, detailed = false }: { events: ActivityEvent[]; detailed?: boolean }) {
  if (!events.length) return <div className="panel empty-state">No runtime events yet.</div>;
  return <div className="panel activity-list">{events.map((event, index) => <div className="activity-row" key={event.id || index}>
    <span className={`activity-icon ${event.type}`}>◆</span>
    <div><strong>{event.type.replaceAll("_", " ")}</strong><span>{detailed ? JSON.stringify(event.payload) : summarizePayload(event.payload)}</span></div>
    <time>{formatTime(event.timestamp)}</time>
  </div>)}</div>;
}

function summarizePayload(payload: Record<string, unknown>) {
  const values = Object.values(payload).filter((value) => typeof value === "string" || typeof value === "number");
  return values.slice(0, 2).map(String).join(" · ") || "Runtime event";
}

function formatTime(timestamp: string) {
  const date = new Date(timestamp);
  return Number.isNaN(date.getTime()) ? "--:--" : date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export default App;
