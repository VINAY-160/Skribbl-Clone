import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { useRoomSocket } from "../hooks/useWebSocket";
import Game from "./Game";
import Lobby from "./Lobby";
import Results from "./Results";

export default function Room() {
  const { roomId = "" } = useParams();
  const [name, setName] = useState(() => localStorage.getItem("skribbl:name") ?? "");
  if (!name) return <NamePrompt onSubmit={(n) => { localStorage.setItem("skribbl:name", n); setName(n); }} />;
  return <Session roomId={roomId.toUpperCase()} name={name} />;
}

function Session({ roomId, name }: { roomId: string; name: string }) {
  const { state, send, subscribe } = useRoomSocket(roomId, name);

  if (state.kicked) return <Notice title="You were removed from the room" />;
  if (state.status === "rejected") return <Notice title={state.error ?? "Couldn't join this room"} />;
  if (state.status === "closed") return <Notice title="Connection lost" body="Check your network and reopen the room link." />;
  if (!state.playerId) return <Notice title="Connecting..." plain />;

  return (
    <>
      {state.status === "reconnecting" && <div className="banner">Reconnecting...</div>}
      {state.phase === "lobby" && <Lobby state={state} send={send} roomId={roomId} />}
      {state.phase === "game_over" && <Results state={state} send={send} />}
      {state.phase !== "lobby" && state.phase !== "game_over" && <Game state={state} send={send} subscribe={subscribe} />}
      {state.error && <div className="toast" role="alert">{state.error}</div>}
    </>
  );
}

function Notice({ title, body, plain }: { title: string; body?: string; plain?: boolean }) {
  return (
    <main className="page narrow center stack">
      <h2>{title}</h2>
      {body && <p className="muted">{body}</p>}
      {!plain && <Link className="btn" to="/">Back to home</Link>}
    </main>
  );
}

function NamePrompt({ onSubmit }: { onSubmit: (name: string) => void }) {
  const [value, setValue] = useState("");
  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (value.trim()) onSubmit(value.trim());
  };
  return (
    <main className="page narrow stack">
      <h1 className="brand">skribbl</h1>
      <p className="muted">Pick a name to join this room.</p>
      <form className="row" onSubmit={submit}>
        <input className="grow" value={value} onChange={(e) => setValue(e.target.value)} placeholder="Your name"
               maxLength={20} autoFocus aria-label="Your name" />
        <button className="btn primary">Join</button>
      </form>
    </main>
  );
}
