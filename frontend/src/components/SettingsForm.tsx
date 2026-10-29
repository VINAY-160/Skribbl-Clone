import type { Settings } from "../types/game";

interface Props {
  settings: Settings;
  disabled?: boolean;
  onChange: (patch: Partial<Settings>) => void;
}

const range = (a: number, b: number) => Array.from({ length: b - a + 1 }, (_, i) => a + i);
const DRAW_TIMES = [15, 30, 45, 60, 80, 90, 120, 150, 180, 240];

export default function SettingsForm({ settings: s, disabled, onChange }: Props) {
  const num = (key: keyof Settings) => (e: React.ChangeEvent<HTMLSelectElement>) =>
    onChange({ [key]: Number(e.target.value) } as Partial<Settings>);

  return (
    <div className="settings">
      <label>Rounds
        <select disabled={disabled} value={s.rounds} onChange={num("rounds")}>
          {range(2, 10).map((n) => <option key={n}>{n}</option>)}
        </select>
      </label>
      <label>Draw time
        <select disabled={disabled} value={s.draw_time} onChange={num("draw_time")}>
          {(DRAW_TIMES.includes(s.draw_time) ? DRAW_TIMES : [...DRAW_TIMES, s.draw_time].sort((a, b) => a - b))
            .map((n) => <option key={n} value={n}>{n}s</option>)}
        </select>
      </label>
      <label>Max players
        <select disabled={disabled} value={s.max_players} onChange={num("max_players")}>
          {range(2, 20).map((n) => <option key={n}>{n}</option>)}
        </select>
      </label>
      <label>Words to choose from
        <select disabled={disabled} value={s.word_count} onChange={num("word_count")}>
          {range(1, 5).map((n) => <option key={n}>{n}</option>)}
        </select>
      </label>
      <label>Hints
        <select disabled={disabled} value={s.hints} onChange={num("hints")}>
          {range(0, 5).map((n) => <option key={n} value={n}>{n === 0 ? "Off" : n}</option>)}
        </select>
      </label>
      <label>Word mode
        <select disabled={disabled} value={s.word_mode}
                onChange={(e) => onChange({ word_mode: e.target.value as Settings["word_mode"] })}>
          <option value="normal">Normal</option>
          <option value="hidden">Hidden</option>
          <option value="combination">Combination</option>
        </select>
      </label>
      <label>Visibility
        <select disabled={disabled} value={s.is_private ? "private" : "public"}
                onChange={(e) => onChange({ is_private: e.target.value === "private" })}>
          <option value="private">Private (invite link)</option>
          <option value="public">Public (listed)</option>
        </select>
      </label>
      <label className="wide">Custom words
        <input disabled={disabled} placeholder="comma separated, optional"
               defaultValue={s.custom_words?.join(", ") ?? ""}
               onBlur={(e) => onChange({
                 custom_words: e.target.value.split(",").map((w) => w.trim()).filter(Boolean),
               })} />
      </label>
    </div>
  );
}
