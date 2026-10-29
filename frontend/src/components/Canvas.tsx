import type { ReactNode } from "react";
import { useCanvas } from "../hooks/useCanvas";
import type { SendFn, Stroke, SubscribeFn, Tool } from "../types/game";

interface Props {
  interactive: boolean;
  tool: Tool;
  color: string;
  size: number;
  initialStrokes: Stroke[];
  send: SendFn;
  subscribe: SubscribeFn;
  children?: ReactNode;
}

export default function Canvas({ children, ...opts }: Props) {
  const { canvasRef, ...handlers } = useCanvas(opts);
  return (
    <div className="canvas-wrap">
      <canvas ref={canvasRef} className={opts.interactive ? "drawable" : ""} {...handlers} />
      {children}
    </div>
  );
}
