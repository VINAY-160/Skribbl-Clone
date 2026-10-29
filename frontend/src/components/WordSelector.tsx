export default function WordSelector({
  options, timeLeft, onPick,
}: { options: string[]; timeLeft: number; onPick: (word: string) => void }) {
  return (
    <div className="overlay">
      <div className="panel center">
        <h2>Pick a word to draw</h2>
        <div className="row wrap center">
          {options.map((w) => (
            <button key={w} className="btn" onClick={() => onPick(w)}>{w}</button>
          ))}
        </div>
        <p className="muted">A random word is picked in {timeLeft}s</p>
      </div>
    </div>
  );
}
