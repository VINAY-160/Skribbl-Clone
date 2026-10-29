import { WS_URL } from "../config";
import type { ServerMessage } from "../types/game";

export type SocketStatus = "idle" | "connecting" | "open" | "reconnecting" | "rejected" | "closed";

interface Handlers {
  onMessage: (msg: ServerMessage) => void;
  onStatus: (status: SocketStatus) => void;
}

const REJECTED_CODES = new Set([4001, 4403, 4404]); // kicked, join refused, room missing
const MAX_RETRIES = 6;

/** Thin wrapper over the browser WebSocket: JSON envelope, auto-reconnect, player_id reuse. */
export class GameSocket {
  private ws: WebSocket | null = null;
  private attempts = 0;
  private closedByUs = false;
  private retryTimer: number | undefined;

  constructor(
    private readonly roomId: string,
    private readonly name: string,
    private readonly handlers: Handlers,
  ) {}

  private get storageKey() {
    return `skribbl:player:${this.roomId}`;
  }

  connect(): void {
    this.handlers.onStatus(this.attempts === 0 ? "connecting" : "reconnecting");
    const pid = sessionStorage.getItem(this.storageKey);
    const url =
      `${WS_URL}/ws/${encodeURIComponent(this.roomId)}?name=${encodeURIComponent(this.name)}` +
      (pid ? `&player_id=${encodeURIComponent(pid)}` : "");
    const ws = new WebSocket(url);
    this.ws = ws;

    ws.onopen = () => {
      this.attempts = 0;
      this.handlers.onStatus("open");
    };
    ws.onmessage = (e) => {
      let msg: ServerMessage;
      try {
        msg = JSON.parse(e.data);
      } catch {
        return;
      }
      if (msg.event === "joined") sessionStorage.setItem(this.storageKey, msg.data.player_id);
      this.handlers.onMessage(msg);
    };
    ws.onclose = (e) => {
      if (this.closedByUs || this.ws !== ws) return;
      if (REJECTED_CODES.has(e.code)) {
        sessionStorage.removeItem(this.storageKey);
        this.handlers.onStatus("rejected");
      } else if (e.code === 4000 || this.attempts >= MAX_RETRIES) {
        this.handlers.onStatus("closed");
      } else {
        this.attempts += 1;
        this.handlers.onStatus("reconnecting");
        this.retryTimer = window.setTimeout(() => this.connect(), Math.min(1000 * this.attempts, 5000));
      }
    };
  }

  send(event: string, data: object = {}): void {
    if (this.ws?.readyState === WebSocket.OPEN) this.ws.send(JSON.stringify({ event, data }));
  }

  close(): void {
    this.closedByUs = true;
    window.clearTimeout(this.retryTimer);
    this.ws?.close();
    this.ws = null;
  }
}
