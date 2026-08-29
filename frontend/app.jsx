const { useState, useEffect, useRef, useCallback } = React;
const API = window.API_BASE;

const LEARNER_ID_KEY = "pathfinder_learner_id";
const SAVED_ROADMAPS_KEY = "pathfinder_saved_roadmaps"; // array of {learner_id, label} for the switcher

function getOrCreateLearnerId() {
  let id = localStorageSafe.get(LEARNER_ID_KEY);
  if (!id) {
    id = "learner_" + Math.random().toString(36).slice(2, 10);
    localStorageSafe.set(LEARNER_ID_KEY, id);
  }
  return id;
}

function newLearnerId() {
  return "learner_" + Math.random().toString(36).slice(2, 10);
}

function getSavedRoadmaps() {
  try {
    const raw = localStorageSafe.get(SAVED_ROADMAPS_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch (e) {
    return [];
  }
}

function saveSavedRoadmaps(list) {
  localStorageSafe.set(SAVED_ROADMAPS_KEY, JSON.stringify(list));
}

function upsertSavedRoadmap(learnerId, label) {
  const list = getSavedRoadmaps();
  const idx = list.findIndex((r) => r.learner_id === learnerId);
  const entry = { learner_id: learnerId, label: label || "Untitled goal", updated_at: Date.now() };
  if (idx >= 0) list[idx] = entry; else list.push(entry);
  saveSavedRoadmaps(list);
  return list;
}

function removeSavedRoadmap(learnerId) {
  const list = getSavedRoadmaps().filter((r) => r.learner_id !== learnerId);
  saveSavedRoadmaps(list);
  return list;
}

// NOTE: artifact-style environments disallow localStorage, but this is a
// standalone static file served outside claude.ai, so browser storage is
// fine here. We still guard it in case it's opened in a sandboxed context.
const localStorageSafe = {
  get(key) {
    try { return window.localStorage.getItem(key); } catch (e) { return null; }
  },
  set(key, val) {
    try { window.localStorage.setItem(key, val); } catch (e) { /* no-op */ }
  },
};

async function api(path, options) {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${path} failed (${res.status}): ${text}`);
  }
  return res.json();
}

const SUGGESTED_GOALS = [
  "I'm a complete beginner and want to become a machine learning engineer",
  "I know some Python and want to move into data science",
  "I want to become a full-stack web developer from scratch",
  "I'm intermediate in ML and want to specialize in NLP and generative AI",
];

function TypingDots() {
  return <span className="spinner" aria-label="thinking" />;
}

function ChatTab({ learnerId, profile, path, onNewPath, learnerName, setLearnerName }) {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      text: "Hi! I'm your learning path assistant. Tell me what you're trying to learn or become — for example your career goal, current experience level, and anything you already know — and I'll build you a personalized roadmap.",
    },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, busy]);

  const send = useCallback(async (text) => {
    const trimmed = (text ?? input).trim();
    if (!trimmed || busy) return;
    setMessages((m) => [...m, { role: "user", text: trimmed }]);
    setInput("");
    setBusy(true);
    try {
      const isFirstGoal = !profile || !profile.goal_text;
      let data;
      if (isFirstGoal) {
        data = await api("/api/chat", {
          method: "POST",
          body: JSON.stringify({ learner_id: learnerId, message: trimmed, name: learnerName || undefined }),
        });
        setMessages((m) => [...m, { role: "assistant", text: data.reply }]);
        onNewPath(data.profile, data.path);
        upsertSavedRoadmap(learnerId, truncate(trimmed, 48));
      } else {
        data = await api(`/api/ask/${learnerId}`, {
          method: "POST",
          body: JSON.stringify({ query: trimmed }),
        });
        setMessages((m) => [...m, { role: "assistant", text: data.reply }]);
      }
    } catch (err) {
      setMessages((m) => [...m, { role: "assistant", text: `Something went wrong reaching the backend: ${err.message}. Is the FastAPI server running on ${API}?` }]);
    } finally {
      setBusy(false);
    }
  }, [input, busy, profile, learnerId, learnerName, onNewPath]);

  return (
    <div className="chat-layout">
      <div className="panel chat-window">
        <div className="panel-title">Talk to your learning assistant</div>
        <div className="panel-subtitle">Describe your goal in your own words. The assistant infers your target domain, experience level and known skills straight from what you type.</div>

        <div className="chat-messages" ref={scrollRef}>
          {messages.map((m, i) => (
            <div key={i} className={`msg ${m.role}`} dangerouslySetInnerHTML={{ __html: mdBold(m.text) }} />
          ))}
          {busy && <div className="msg assistant thinking"><TypingDots /> &nbsp;thinking…</div>}
        </div>

        {(!profile || !profile.goal_text) && (
          <div className="suggestion-row">
            {SUGGESTED_GOALS.map((g) => (
              <span key={g} className="suggestion-chip" onClick={() => send(g)}>{g}</span>
            ))}
          </div>
        )}

        <div className="chat-input-row">
          <textarea
            placeholder="e.g. I want to become a machine learning engineer, I'm a beginner but know some Python…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
          />
          <button className="btn btn-primary" onClick={() => send()} disabled={busy || !input.trim()}>Send</button>
        </div>
      </div>

      <div className="panel">
        <div className="panel-title">Your profile so far</div>
        <div className="panel-subtitle">Built automatically from the conversation — nothing to fill in by hand.</div>

        {!profile ? (
          <div className="empty-state">
            <div className="glyph">＊</div>
            <div>Say hello to get started.</div>
          </div>
        ) : (
          <>
            <div style={{ marginBottom: 10 }}>
              <input
                className="chat-name-input"
                placeholder="Your name (optional)"
                value={learnerName}
                onChange={(e) => setLearnerName(e.target.value)}
                style={{
                  width: "100%", background: "var(--ink)", border: "1px solid var(--line)",
                  borderRadius: 8, color: "var(--text)", padding: "8px 10px", fontSize: 13,
                  fontFamily: "var(--font-body)",
                }}
              />
            </div>
            <div className="profile-row"><span className="label">Goal</span><span className="value">{truncate(profile.goal_text, 40) || "—"}</span></div>
            <div className="profile-row"><span className="label">Track</span><span className="value">{path ? path.domain : "—"}</span></div>
            <div className="profile-row"><span className="label">Experience</span><span className="value">{profile.experience_level}</span></div>
            <div className="profile-row"><span className="label">Path length</span><span className="value">{path ? `${path.total_steps} steps · ${path.total_estimated_hours}h` : "—"}</span></div>
            <div style={{ marginTop: 12 }}>
              <div className="stat-label" style={{ marginBottom: 6 }}>Known skills</div>
              {profile.known_skills.length === 0 && <div style={{ color: "var(--text-faint)", fontSize: 12 }}>None captured yet.</div>}
              {profile.known_skills.map((s) => <span key={s} className="skill-pill">{s}</span>)}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function truncate(s, n) {
  if (!s) return "";
  return s.length > n ? s.slice(0, n) + "…" : s;
}

function mdBold(text) {
  // Minimal, safe **bold** -> <strong> renderer for assistant replies (no other HTML passthrough).
  const escaped = text
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  return escaped.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
}

function RoadmapTab({ learnerId, path, refreshAll }) {
  const [busyId, setBusyId] = useState(null);
  const [toast, setToast] = useState(null);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 3200);
    return () => clearTimeout(t);
  }, [toast]);

  if (!path) {
    return (
      <div className="panel">
        <div className="empty-state">
          <div className="glyph">🗺</div>
          <div>No roadmap yet — describe your goal in the Chat tab first.</div>
        </div>
      </div>
    );
  }

  const act = async (courseId, action) => {
    setBusyId(courseId);
    try {
      if (action === "complete") {
        await api(`/api/progress/${learnerId}`, {
          method: "POST",
          body: JSON.stringify({ course_id: courseId, status: "completed" }),
        });
        setToast("Marked complete — roadmap updated.");
      } else if (action === "too_easy") {
        await api(`/api/feedback/${learnerId}`, {
          method: "POST",
          body: JSON.stringify({ course_id: courseId, feedback: "too_easy" }),
        });
        setToast("Got it — marked as known and skipped.");
      } else if (action === "too_hard") {
        await api(`/api/feedback/${learnerId}`, {
          method: "POST",
          body: JSON.stringify({ course_id: courseId, feedback: "too_hard" }),
        });
        setToast("Thanks — your level was adjusted so upcoming recommendations go gentler.");
      }
      await refreshAll();
    } catch (err) {
      setToast(`Couldn't save that: ${err.message}`);
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="panel">
      {toast && <div className="toast">{toast}</div>}
      <div className="panel-title">Your personalized roadmap</div>
      <div className="panel-subtitle">{path.overview}</div>

      <div className="trail">
        {path.steps.map((s) => (
          <div className="trail-step" key={s.course_id}>
            <div className={`trail-node ${s.completed ? "done" : ""} ${s.is_milestone ? "milestone" : ""}`}>
              {s.completed ? "✓" : s.step}
            </div>
            <div className={`trail-card ${s.completed ? "done" : ""}`}>
              <div className="trail-card-head">
                <p className="trail-card-title">{s.title}</p>
                <span className={`badge ${s.type}`}>{s.type}</span>
              </div>
              <div className="trail-meta">
                {s.domain} · {s.level} · {s.duration_hours}h
                {s.prerequisites.length > 0 && <> · requires {s.prerequisites.length} prereq{s.prerequisites.length > 1 ? "s" : ""}</>}
              </div>
              {s.feedback_flag && (
                <div className={`feedback-ack ${s.feedback_flag}`}>
                  {s.feedback_flag === "too_hard" && "⚠ You flagged this as too hard — your overall level was adjusted so future recommendations go gentler."}
                  {s.feedback_flag === "too_easy" && "✓ You flagged this as too easy — marked done and its skills were added to your known skills."}
                  {s.feedback_flag === "not_relevant" && "✕ You flagged this as not relevant — it's been skipped."}
                </div>
              )}
              <p className="trail-explain">{s.explanation}</p>
              {!s.completed && (
                <div className="trail-actions">
                  <button className="btn-mini positive" disabled={busyId === s.course_id} onClick={() => act(s.course_id, "complete")}>
                    Mark complete
                  </button>
                  <button className="btn-mini" disabled={busyId === s.course_id} onClick={() => act(s.course_id, "too_easy")}>
                    Too easy — I know this
                  </button>
                  <button className="btn-mini negative" disabled={busyId === s.course_id} onClick={() => act(s.course_id, "too_hard")}>
                    Feels too hard
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function StatCard({ label, value, unit, children }) {
  return (
    <div className="stat-card">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}{unit && <span className="unit">{unit}</span>}</div>
      {children}
    </div>
  );
}

function SkillChart({ acquired, remaining }) {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (!canvasRef.current) return;
    if (chartRef.current) chartRef.current.destroy();
    const total = acquired.length + remaining.length;
    chartRef.current = new Chart(canvasRef.current, {
      type: "doughnut",
      data: {
        labels: ["Skills acquired", "Skills remaining"],
        datasets: [{
          data: [acquired.length, remaining.length || (total === 0 ? 1 : 0)],
          backgroundColor: ["#4FD1B0", "#2A3B5E"],
          borderWidth: 0,
        }],
      },
      options: {
        cutout: "72%",
        plugins: { legend: { display: false } },
        maintainAspectRatio: false,
      },
    });
    return () => chartRef.current && chartRef.current.destroy();
  }, [acquired, remaining]);

  return <div className="chart-wrap"><canvas ref={canvasRef}></canvas></div>;
}

function DashboardTab({ learnerId, path, hasProfile }) {
  const [dash, setDash] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    if (!hasProfile) return;
    setLoading(true);
    try {
      const data = await api(`/api/dashboard/${learnerId}`);
      setDash(data);
    } catch (e) {
      // swallow — shown as empty state below
    } finally {
      setLoading(false);
    }
  }, [learnerId, hasProfile]);

  useEffect(() => { load(); }, [load, path]);

  if (!hasProfile) {
    return (
      <div className="panel">
        <div className="empty-state">
          <div className="glyph">📊</div>
          <div>Your dashboard will appear once you've described a learning goal in the Chat tab.</div>
        </div>
      </div>
    );
  }

  if (loading && !dash) {
    return <div className="panel"><div className="empty-state"><TypingDots /> &nbsp;Loading dashboard…</div></div>;
  }

  if (!dash) return null;

  return (
    <div>
      <div className="dash-grid">
        <StatCard label="Overall progress" value={`${dash.progress_percent}`} unit="%">
          <div className="progress-bar-track"><div className="progress-bar-fill" style={{ width: `${dash.progress_percent}%` }} /></div>
        </StatCard>
        <StatCard label="Steps completed" value={`${dash.completed_steps}/${dash.total_steps}`} />
        <StatCard label="Est. remaining time" value={dash.total_estimated_hours} unit="hrs total" />
        <StatCard label="Milestones" value={dash.milestones.length} unit="projects & assessments" />
      </div>

      <div className="dash-cols">
        <div className="panel">
          <div className="panel-title">Skill development by domain</div>
          <div className="panel-subtitle">Share of each domain's roadmap you've completed so far.</div>
          {Object.entries(dash.domain_progress).map(([domain, d]) => (
            <div className="domain-row" key={domain}>
              <div className="domain-row-label">
                <span>{domain}</span>
                <span className="frac">{d.completed}/{d.total}</span>
              </div>
              <div className="progress-bar-track">
                <div className="progress-bar-fill" style={{ width: `${d.total ? (100 * d.completed / d.total) : 0}%` }} />
              </div>
            </div>
          ))}

          <div className="panel-title" style={{ marginTop: 22 }}>Up next</div>
          {dash.upcoming_next.length === 0 && <div style={{ color: "var(--text-faint)", fontSize: 13 }}>Nothing left — path complete! 🎉</div>}
          {dash.upcoming_next.map((s) => (
            <div className="next-item" key={s.course_id}>
              <span>{s.title}</span>
              <span className={`badge ${s.type}`}>{s.type}</span>
            </div>
          ))}
        </div>

        <div className="panel">
          <div className="panel-title">Skills acquired vs. remaining</div>
          <SkillChart acquired={dash.skills_acquired} remaining={dash.skills_remaining} />
          <div style={{ marginTop: 10 }}>
            {dash.skills_acquired.map((s) => <span key={s} className="skill-pill">{s}</span>)}
          </div>

          <div className="panel-title" style={{ marginTop: 22 }}>Milestones</div>
          {dash.milestones.map((m) => (
            <div className="milestone-item" key={m.course_id}>
              <span>{m.title}</span>
              <span style={{ color: m.completed ? "var(--teal)" : "var(--text-faint)", fontFamily: "var(--font-mono)", fontSize: 11 }}>
                {m.completed ? "done" : "pending"}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function RoadmapSwitcher({ activeId, onSwitch, onNew, onDeleted }) {
  const [open, setOpen] = useState(false);
  const [roadmaps, setRoadmaps] = useState(getSavedRoadmaps());

  useEffect(() => {
    if (open) setRoadmaps(getSavedRoadmaps());
  }, [open]);

  const del = async (e, learnerId) => {
    e.stopPropagation();
    try { await api(`/api/learner/${learnerId}`, { method: "DELETE" }); } catch (err) { /* ignore */ }
    const updated = removeSavedRoadmap(learnerId);
    setRoadmaps(updated);
    if (learnerId === activeId) onDeleted();
  };

  return (
    <div className="switcher">
      <button className="btn btn-ghost" onClick={() => setOpen((o) => !o)}>
        My roadmaps {roadmaps.length > 0 && <span className="count">{roadmaps.length}</span>} ▾
      </button>
      <button className="btn btn-primary" onClick={onNew}>+ New roadmap</button>
      {open && (
        <div className="switcher-menu">
          {roadmaps.length === 0 && <div className="switcher-empty">No saved roadmaps yet — describe a goal in Chat to create one.</div>}
          {roadmaps.map((r) => (
            <div
              key={r.learner_id}
              className={`switcher-item ${r.learner_id === activeId ? "active" : ""}`}
              onClick={() => { onSwitch(r.learner_id); setOpen(false); }}
            >
              <span className="switcher-item-label">{r.label}</span>
              <button className="switcher-item-delete" onClick={(e) => del(e, r.learner_id)} title="Delete this roadmap">✕</button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function App() {
  const [learnerId, setLearnerIdState] = useState(getOrCreateLearnerId());
  const [tab, setTab] = useState("chat");
  const [profile, setProfile] = useState(null);
  const [path, setPath] = useState(null);
  const [learnerName, setLearnerName] = useState("");

  const refreshAll = useCallback(async (idOverride) => {
    const id = idOverride || learnerId;
    try {
      const p = await api(`/api/profile/${id}`);
      setProfile(p);
      const pathData = await api(`/api/path/${id}`);
      setPath(pathData);
    } catch (e) {
      // no profile yet for this learner — that's fine on first load / brand new roadmap
      setProfile(null);
      setPath(null);
    }
  }, [learnerId]);

  useEffect(() => { refreshAll(); }, [refreshAll]);

  const onNewPath = (newProfile, newPath) => {
    setProfile(newProfile);
    setPath(newPath);
  };

  const switchTo = (id) => {
    localStorageSafe.set(LEARNER_ID_KEY, id);
    setLearnerIdState(id);
    setTab("chat");
    refreshAll(id);
  };

  const startNewRoadmap = () => {
    const id = newLearnerId();
    localStorageSafe.set(LEARNER_ID_KEY, id);
    setLearnerIdState(id);
    setProfile(null);
    setPath(null);
    setLearnerName("");
    setTab("chat");
  };

  return (
    <div className="app-shell">
      <div className="app-header">
        <div className="brand">
          <div className="brand-mark">Path<em>finder</em></div>
          <div className="brand-tag">AI Personalized Learning Path Recommender</div>
        </div>
        <RoadmapSwitcher
          activeId={learnerId}
          onSwitch={switchTo}
          onNew={startNewRoadmap}
          onDeleted={startNewRoadmap}
        />
      </div>

      <div className="tab-row">
        <button className={`tab-btn ${tab === "chat" ? "active" : ""}`} onClick={() => setTab("chat")}>Chat</button>
        <button className={`tab-btn ${tab === "roadmap" ? "active" : ""}`} onClick={() => setTab("roadmap")}>
          Roadmap{path && <span className="count">{path.total_steps}</span>}
        </button>
        <button className={`tab-btn ${tab === "dashboard" ? "active" : ""}`} onClick={() => setTab("dashboard")}>Dashboard</button>
      </div>

      {tab === "chat" && (
        <ChatTab
          learnerId={learnerId}
          profile={profile}
          path={path}
          onNewPath={onNewPath}
          learnerName={learnerName}
          setLearnerName={setLearnerName}
        />
      )}
      {tab === "roadmap" && <RoadmapTab learnerId={learnerId} path={path} refreshAll={refreshAll} />}
      {tab === "dashboard" && <DashboardTab learnerId={learnerId} path={path} hasProfile={!!profile} />}

      <div className="footer-note">Pathfinder prototype · Recommendation logic runs entirely against your local FastAPI backend at {API}</div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
