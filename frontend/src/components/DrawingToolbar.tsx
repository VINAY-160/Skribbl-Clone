import { Eraser, Pencil, Trash2, Undo2 } from "lucide-react";
import type { Tool } from "../types/game";

export const COLORS = [
  "#16181d", "#8a8f98", "#e5484d", "#f76b15", "#f5c518",
  "#30a46c", "#12a594", "#2f5bea", "#8e4ec6", "#a2623a",
];
export const SIZES = [3, 8, 18];

interface Props {
  tool: Tool; color: string; size: number;
  onTool: (t: Tool) => void; onColor: (c: string) => void; onSize: (s: number) => void;
  onUndo: () => void; onClear: () => void;
}

export default function DrawingToolbar(p: Props) {
  return (
    <div className="toolbar">
      <div className="row">
        {COLORS.map((c) => (
          <button key={c} aria-label={`Color ${c}`} className={`swatch ${p.color === c && p.tool === "pen" ? "on" : ""}`}
                  style={{ background: c }} onClick={() => { p.onColor(c); p.onTool("pen"); }} />
        ))}
      </div>
      <div className="row">
        {SIZES.map((s) => (
          <button key={s} aria-label={`Brush size ${s}`} className={`size ${p.size === s ? "on" : ""}`}
                  onClick={() => p.onSize(s)}>
            <i style={{ width: Math.max(4, s * 0.8), height: Math.max(4, s * 0.8) }} />
          </button>
        ))}
        <button className={`icon ${p.tool === "pen" ? "on" : ""}`} aria-label="Pen" onClick={() => p.onTool("pen")}>
          <Pencil size={16} />
        </button>
        <button className={`icon ${p.tool === "eraser" ? "on" : ""}`} aria-label="Eraser" onClick={() => p.onTool("eraser")}>
          <Eraser size={16} />
        </button>
        <button className="icon" aria-label="Undo" onClick={p.onUndo}><Undo2 size={16} /></button>
        <button className="icon" aria-label="Clear canvas" onClick={p.onClear}><Trash2 size={16} /></button>
      </div>
    </div>
  );
}
