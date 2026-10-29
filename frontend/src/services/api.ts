import { API_URL } from "../config";
import type { RoomInfo, Settings, TopPlayer } from "../types/game";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let message = "Something went wrong";
    try {
      const body = await res.json();
      if (typeof body.detail === "string") message = body.detail;
      else if (res.status === 422) message = "Some settings are out of range";
    } catch {
      /* keep default */
    }
    throw new Error(message);
  }
  return res.json() as Promise<T>;
}

export const api = {
  createRoom: (settings: Partial<Settings>) =>
    request<{ room_id: string }>("/api/rooms", { method: "POST", body: JSON.stringify({ settings }) }),
  getRoom: (id: string) => request<RoomInfo>(`/api/rooms/${encodeURIComponent(id)}`),
  listRooms: () => request<RoomInfo[]>("/api/rooms"),
  topPlayers: () => request<TopPlayer[]>("/api/leaderboard?limit=5"),
};
