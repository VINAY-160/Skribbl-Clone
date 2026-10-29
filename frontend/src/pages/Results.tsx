import { Trophy } from "lucide-react";
import { useNavigate } from "react-router-dom";
import Leaderboard from "../components/Leaderboard";
import type { GameState } from "../state/gameReducer";
import type { LeaderboardEntry, SendFn } from "../types/game";

export default function Results({ state, send }: { state: GameState; send: SendFn }) {
  const nav = useNavigate();
  const isHost = state.playerId === state.hostId;
  const board: LeaderboardEntry[] =
    state.gameOver?.leaderboard ??
    [...state.players].sort((a, b) => b.score - a.score)
      .map((p, i) => ({ rank: i + 1, player_id: p.id, name: p.name, score: p.score, connected: p.connected }));
  const winners = state.gameOver?.winners ?? board.slice(0, 1);

  return (
    <main className="page narrow">
      <div className="center stack">
        <Trophy size={28} />
        <h1>{winners.length > 1 ? `${winners.map((w) => w.name).join(" and ")} tie` : `${winners[0]?.name ?? "Nobody"} wins`}</h1>
        {state.gameOver?.reason === "not_enough_players" && <p className="muted">The game ended early because too many players left.</p>}
      </div>
      <Leaderboard entries={board} meId={state.playerId} />
      <div className="row">
        {isHost
          ? <button className="btn primary grow" onClick={() => send("start_game")}>Play again</button>
          : <p className="muted grow">Waiting for the host to start another game.</p>}
        <button className="btn" onClick={() => nav("/")}>Leave</button>
      </div>
    </main>
  );
}
