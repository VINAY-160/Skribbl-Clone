export default function Timer({ timeLeft, total }: { timeLeft: number; total: number }) {
  const pct = total > 0 ? Math.max(0, Math.min(100, (timeLeft / total) * 100)) : 0;
  return (
    <div className="timer" aria-label={`${timeLeft} seconds left`}>
      <strong>{timeLeft}</strong>
      <div className="bar"><i style={{ width: `${pct}%` }} className={pct < 25 ? "low" : ""} /></div>
    </div>
  );
}
