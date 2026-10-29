import { Check, Crown, Pencil } from "lucide-react";
import type { Player } from "../types/game";
import Avatar from "./Avatar";

interface Props {
  players: Player[];
  meId: string | null;
  mode: "lobby" | "game";
  canModerate?: boolean;
  onKick?: (id: string) => void;
  onBan?: (id: string) => void;
  onVotekick?: (id: string) => void;
}

export default function PlayerList({ players, meId, mode, canModerate, onKick, onBan, onVotekick }: Props) {
  const list = mode === "game" ? [...players].sort((a, b) => b.score - a.score) : players;
  return (
    <ul className="players">
      {list.map((p) => (
        <li key={p.id} className={`${p.connected ? "" : "away"} ${p.id === meId ? "me" : ""}`}>
          <Avatar name={p.name} index={p.avatar} />
          <span className="grow name">
            {p.name}
            {p.id === meId && <span className="muted"> (you)</span>}
          </span>
          {p.is_host && <Crown size={14} aria-label="host" />}
          {mode === "lobby" && p.ready && <span className="tag">ready</span>}
          {mode === "game" && p.is_drawer && <Pencil size={14} aria-label="drawing" />}
          {mode === "game" && p.has_guessed && <Check size={14} className="ok" aria-label="guessed" />}
          {mode === "game" && <strong>{p.score}</strong>}
          {p.id !== meId && (
            <span className="mod">
              {canModerate && onKick && <button className="link" onClick={() => onKick(p.id)}>kick</button>}
              {canModerate && onBan && <button className="link" onClick={() => onBan(p.id)}>ban</button>}
              {!canModerate && onVotekick && mode === "game" && (
                <button className="link" onClick={() => onVotekick(p.id)}>vote kick</button>
              )}
            </span>
          )}
        </li>
      ))}
    </ul>
  );
}
