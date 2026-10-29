import { useCallback, useEffect, useReducer, useRef } from "react";
import { GameSocket } from "../services/websocket";
import { gameReducer, initialState } from "../state/gameReducer";
import type { SendFn, SubscribeFn } from "../types/game";

type Listener = (data: unknown) => void;

/** Owns the socket for one room, feeds the reducer, and lets components subscribe to raw events. */
export function useRoomSocket(roomId: string, name: string) {
  const [state, dispatch] = useReducer(gameReducer, initialState);
  const socketRef = useRef<GameSocket | null>(null);
  const listeners = useRef(new Map<string, Set<Listener>>());

  useEffect(() => {
    dispatch({ type: "reset" });
    const socket = new GameSocket(roomId, name, {
      onMessage: (msg) => {
        dispatch({ type: "server", event: msg.event, data: msg.data });
        listeners.current.get(msg.event)?.forEach((fn) => fn(msg.data));
      },
      onStatus: (status) => dispatch({ type: "status", status }),
    });
    socketRef.current = socket;
    const t = window.setTimeout(() => socket.connect(), 0); // survives StrictMode double-mount
    return () => {
      window.clearTimeout(t);
      socket.close();
      socketRef.current = null;
    };
  }, [roomId, name]);

  useEffect(() => {
    if (!state.error) return;
    const t = window.setTimeout(() => dispatch({ type: "clear_error" }), 3500);
    return () => window.clearTimeout(t);
  }, [state.error]);

  const send: SendFn = useCallback((event, data = {}) => socketRef.current?.send(event, data), []);

  const subscribe: SubscribeFn = useCallback((event, fn) => {
    const set = listeners.current.get(event) ?? new Set<Listener>();
    set.add(fn);
    listeners.current.set(event, set);
    return () => {
      set.delete(fn);
    };
  }, []);

  return { state, send, subscribe };
}
