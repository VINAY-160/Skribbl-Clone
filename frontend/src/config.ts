export const API_URL: string = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");

export const WS_URL: string = API_URL
  ? API_URL.replace(/^http/, "ws")
  : `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}`;
