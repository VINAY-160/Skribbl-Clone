import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../services/api";
import SettingsForm from "../components/SettingsForm";
import type { RoomInfo, Settings, TopPlayer } from "../types/game";

const DEFAULTS: Settings = {
  max_players: 8, rounds: 3, draw_time: 80, word_count: 3, hints: 2,
  word_mode: "normal", is_private: true, category: null, custom_words: [],
};

export default function Home() {
  const nav = useNavigate();
  const [name, setName] = useState(() => localStorage.getItem("skribbl:name") ?? "");
  const [code, setCode] = useState("");
  const [settings, setSettings] = useState<Settings>(DEFAULTS);
  const [showSettings, setShowSettings] = useState(false);
  const [rooms, setRooms] = useState<RoomInfo[]>([]);
  const [top, setTop] = useState<TopPlayer[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const loadRooms = () => api.listRooms().then(setRooms).catch(() => setRooms([]));
  useEffect(() => {
    loadRooms();
    api.topPlayers().then(setTop).catch(() => setTop([]));
  }, []);

  const saveName = () => {
    const n = name.trim();
    if (!n) { setError("Enter a name first"); return null; }
    localStorage.setItem("skribbl:name", n);
    setError("");
    return n;
  };

  const create = async () => {
    if (!saveName()) return;
    setBusy(true);
    try {
      const { room_id } = await api.createRoom(settings);
      nav(`/room/${room_id}`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const join = async (id: string) => {
    if (!saveName()) return;
    const clean = id.trim().toUpperCase();
    if (!clean) { setError("Enter a room code"); return; }
    try {
      await api.getRoom(clean);
      nav(`/room/${clean}`);
    } catch {
      setError("Room not found. Check the code and try again.");
    }
  };

  return (
    <main className="page narrow">
      <h1 className="brand">skribbl</h1>
      <p className="muted">Draw. Guess. Win.</p>

      <section className="stack">
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name"
               maxLength={20} aria-label="Your name" />
        {error && <p className="error">{error}</p>}

        <div className="row">
          <button className="btn primary grow" onClick={create} disabled={busy}>Create room</button>
          <button className="btn" onClick={() => setShowSettings((v) => !v)}>
            {showSettings ? "Hide settings" : "Settings"}
          </button>
        </div>
        {showSettings && <SettingsForm settings={settings} onChange={(p) => setSettings((s) => ({ ...s, ...p }))} />}

        <form className="row" onSubmit={(e) => { e.preventDefault(); join(code); }}>
          <input className="grow" value={code} onChange={(e) => setCode(e.target.value)}
                 placeholder="Room code" maxLength={6} aria-label="Room code" />
          <button className="btn">Join</button>
        </form>
      </section>

      <section className="stack">
        <div className="row between">
          <h2>Open rooms</h2>
          <button className="link" onClick={loadRooms}>Refresh</button>
        </div>
        {rooms.length === 0 && <p className="muted">No public rooms right now. Create one and set it to public.</p>}
        <ul className="list">
          {rooms.map((r) => (
            <li key={r.room_id}>
              <span className="grow">{r.room_id}
                <span className="muted"> {r.player_count}/{r.max_players} players, {r.rounds} rounds</span>
              </span>
              <button className="btn small" onClick={() => join(r.room_id)}>Join</button>
            </li>
          ))}
        </ul>
      </section>

      {top.length > 0 && (
        <section className="stack">
          <h2>Top players</h2>
          <ul className="list">
            {top.map((t) => (
              <li key={t.name}>
                <span className="grow">{t.name}</span>
                <span className="muted">{t.wins} {t.wins === 1 ? "win" : "wins"}, best {t.best_score}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </main>
  );
}
