import type { LeaderboardEntry } from "../types/game";

export default function Leaderboard({ entries, meId }: { entries: LeaderboardEntry[]; meId: string | null }) {
  return (
    <ol className="leaderboard">
      {entries.map((e) => (
        <li key={e.player_id} className={e.player_id === meId ? "me" : ""}>
          <span className="rank">{e.rank}</span>
          <span className="grow">{e.name}</span>
          <strong>{e.score}</strong>
        </li>
      ))}
    </ol>
  );
}
