import { Copy } from "lucide-react";
import { useState } from "react";
import PlayerList from "../components/PlayerList";
import SettingsForm from "../components/SettingsForm";
import type { GameState } from "../state/gameReducer";
import type { SendFn, Settings } from "../types/game";

export default function Lobby({ state, send, roomId }: { state: GameState; send: SendFn; roomId: string }) {
  const [copied, setCopied] = useState(false);
  const me = state.players.find((p) => p.id === state.playerId);
  const isHost = state.playerId === state.hostId;
  const link = `${window.location.origin}/room/${roomId}`;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(link);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch { /* clipboard blocked */ }
  };

  return (
    <main className="page narrow">
      <div className="row between">
        <div>
          <p className="muted">Room code</p>
          <h1 className="code">{roomId}</h1>
        </div>
        <button className="btn" onClick={copy}><Copy size={14} /> {copied ? "Copied" : "Copy invite link"}</button>
      </div>

      <section className="stack">
        <h2>Players ({state.players.length}/{state.settings?.max_players})</h2>
        <PlayerList players={state.players} meId={state.playerId} mode="lobby" canModerate={isHost}
                    onKick={(id) => send("kick", { player_id: id })} onBan={(id) => send("ban", { player_id: id })} />
      </section>

      {state.settings && (
        <section className="stack">
          <h2>Settings</h2>
          {!isHost && <p className="muted">Only the host can change settings.</p>}
          <SettingsForm settings={state.settings} disabled={!isHost}
                        onChange={(patch: Partial<Settings>) => send("update_settings", patch)} />
        </section>
      )}

      <div className="row">
        {!isHost && (
          <button className="btn grow" onClick={() => send("ready", { ready: !me?.ready })}>
            {me?.ready ? "Not ready" : "Ready"}
          </button>
        )}
        {isHost && (
          <button className="btn primary grow" onClick={() => send("start_game")} disabled={state.players.length < 2}>
            {state.players.length < 2 ? "Waiting for players" : "Start game"}
          </button>
        )}
      </div>
    </main>
  );
}
