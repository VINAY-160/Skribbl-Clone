import { useCallback, useEffect, useRef } from "react";
import type { PointerEvent as ReactPointerEvent } from "react";
import type { SendFn, Stroke, SubscribeFn, Tool } from "../types/game";

interface Options {
  interactive: boolean;
  tool: Tool;
  color: string;
  size: number;
  initialStrokes: Stroke[];
  send: SendFn;
  subscribe: SubscribeFn;
}

const BASE_WIDTH = 800; // brush sizes are defined against an 800px wide canvas
const clamp01 = (n: number) => Math.min(1, Math.max(0, n));

function style(ctx: CanvasRenderingContext2D, s: Stroke, w: number) {
  const color = s.tool === "eraser" ? "#ffffff" : s.color;
  ctx.strokeStyle = color;
  ctx.fillStyle = color;
  ctx.lineWidth = Math.max(1, s.size * (w / BASE_WIDTH));
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
}

function paintStroke(ctx: CanvasRenderingContext2D, s: Stroke, w: number, h: number) {
  const pts = s.points;
  if (!pts.length) return;
  style(ctx, s, w);
  if (pts.length === 1) {
    ctx.beginPath();
    ctx.arc(pts[0][0] * w, pts[0][1] * h, ctx.lineWidth / 2, 0, Math.PI * 2);
    ctx.fill();
    return;
  }
  ctx.beginPath();
  ctx.moveTo(pts[0][0] * w, pts[0][1] * h);
  for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0] * w, pts[i][1] * h);
  ctx.stroke();
}

function paintSegment(
  ctx: CanvasRenderingContext2D, s: Stroke, a: number[], b: number[], w: number, h: number,
) {
  style(ctx, s, w);
  ctx.beginPath();
  ctx.moveTo(a[0] * w, a[1] * h);
  ctx.lineTo(b[0] * w, b[1] * h);
  ctx.stroke();
}

/**
 * Capture -> send -> render pipeline.
 * - Drawer: pointer events -> normalised points -> painted locally at once, batched to the server every 40ms.
 * - Everyone else: draw_data / draw_undo / canvas_clear events repaint the same stroke list.
 */
export function useCanvas(opts: Options) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const strokes = useRef<Stroke[]>([]);
  const remote = useRef<Stroke | null>(null);
  const local = useRef<{ stroke: Stroke; buffer: number[][]; timer: number } | null>(null);
  const optsRef = useRef(opts);
  optsRef.current = opts;

  const redraw = useCallback(() => {
    const c = canvasRef.current;
    const ctx = c?.getContext("2d");
    if (!c || !ctx) return;
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, c.width, c.height);
    for (const s of strokes.current) paintStroke(ctx, s, c.width, c.height);
  }, []);

  // size to the element, keep it crisp on resize
  useEffect(() => {
    const c = canvasRef.current;
    if (!c) return;
    strokes.current = optsRef.current.initialStrokes.map((s) => ({ ...s, points: [...s.points] }));
    const resize = () => {
      const r = c.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      c.width = Math.max(1, Math.round(r.width * dpr));
      c.height = Math.max(1, Math.round(r.height * dpr));
      redraw();
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(c);
    return () => ro.disconnect();
  }, [redraw]);

  // remote events
  useEffect(() => {
    const { subscribe } = optsRef.current;
    const offs = [
      subscribe("draw_data", (d) => {
        const c = canvasRef.current;
        const ctx = c?.getContext("2d");
        if (!c || !ctx) return;
        if (d.type === "start") {
          const s: Stroke = { color: d.color, size: d.size, tool: d.tool, points: [[d.x, d.y]] };
          strokes.current.push(s);
          remote.current = s;
          paintStroke(ctx, s, c.width, c.height);
        } else if (d.type === "move" && remote.current) {
          const s = remote.current;
          for (const p of d.points as number[][]) {
            paintSegment(ctx, s, s.points[s.points.length - 1], p, c.width, c.height);
            s.points.push(p);
          }
        } else if (d.type === "end") {
          remote.current = null;
        }
      }),
      subscribe("canvas_clear", () => {
        strokes.current = [];
        redraw();
      }),
      subscribe("draw_undo", (d) => {
        strokes.current = d.strokes;
        redraw();
      }),
      subscribe("round_start", () => {
        strokes.current = [];
        remote.current = null;
        redraw();
      }),
    ];
    return () => offs.forEach((off) => off());
  }, [redraw]);

  const flush = useCallback(() => {
    const l = local.current;
    if (!l || !l.buffer.length) return;
    while (l.buffer.length) optsRef.current.send("draw_move", { points: l.buffer.splice(0, 50) });
  }, []);

  const endStroke = useCallback(() => {
    const l = local.current;
    if (!l) return;
    flush();
    window.clearInterval(l.timer);
    local.current = null;
    optsRef.current.send("draw_end");
  }, [flush]);

  useEffect(() => {
    if (!opts.interactive) endStroke();
  }, [opts.interactive, endStroke]);

  const toPoint = (e: { clientX: number; clientY: number }, el: HTMLElement) => {
    const r = el.getBoundingClientRect();
    return [clamp01((e.clientX - r.left) / r.width), clamp01((e.clientY - r.top) / r.height)];
  };

  const onPointerDown = (e: ReactPointerEvent<HTMLCanvasElement>) => {
    const c = canvasRef.current;
    const ctx = c?.getContext("2d");
    if (!c || !ctx || !optsRef.current.interactive || e.button > 0) return;
    c.setPointerCapture(e.pointerId);
    const [x, y] = toPoint(e, c);
    const { tool, color, size, send } = optsRef.current;
    const stroke: Stroke = { color, size, tool, points: [[x, y]] };
    strokes.current.push(stroke);
    paintStroke(ctx, stroke, c.width, c.height);
    send("draw_start", { x, y, color, size, tool });
    local.current = { stroke, buffer: [], timer: window.setInterval(flush, 40) };
  };

  const onPointerMove = (e: ReactPointerEvent<HTMLCanvasElement>) => {
    const c = canvasRef.current;
    const ctx = c?.getContext("2d");
    const l = local.current;
    if (!c || !ctx || !l) return;
    const native = e.nativeEvent;
    const events = native.getCoalescedEvents?.() ?? [native];
    for (const ev of events.length ? events : [native]) {
      const p = toPoint(ev, c);
      paintSegment(ctx, l.stroke, l.stroke.points[l.stroke.points.length - 1], p, c.width, c.height);
      l.stroke.points.push(p);
      l.buffer.push(p);
    }
  };

  return { canvasRef, onPointerDown, onPointerMove, onPointerUp: endStroke, onPointerCancel: endStroke };
}
