export type Phase = "lobby" | "choosing_word" | "drawing" | "turn_end" | "game_over";
export type WordMode = "normal" | "hidden" | "combination";
export type Tool = "pen" | "eraser";

export interface Settings {
  max_players: number;
  rounds: number;
  draw_time: number;
  word_count: number;
  hints: number;
  word_mode: WordMode;
  is_private: boolean;
  category: string | null;
  custom_words?: string[];
}

export interface Player {
  id: string;
  name: string;
  avatar: number;
  score: number;
  turn_points: number;
  connected: boolean;
  ready: boolean;
  has_guessed: boolean;
  is_host: boolean;
  is_drawer: boolean;
}

export interface Stroke {
  color: string;
  size: number;
  tool: Tool;
  points: number[][]; // normalised 0..1
}

export interface ChatMessage {
  id: number;
  kind: "guess" | "chat" | "system" | "correct";
  player_name?: string;
  text: string;
}

export interface RoundEnd {
  word: string | null;
  reason: string;
  drawer_points: number;
  players: Player[];
}

export interface LeaderboardEntry {
  rank: number;
  player_id: string;
  name: string;
  score: number;
  connected: boolean;
}

export interface GameOver {
  winner: LeaderboardEntry | null;
  winners: LeaderboardEntry[];
  leaderboard: LeaderboardEntry[];
  reason: string;
}

export interface RoomInfo {
  room_id: string;
  is_private: boolean;
  phase: string;
  player_count: number;
  max_players: number;
  rounds: number;
  draw_time: number;
}

export interface TopPlayer {
  name: string;
  games: number;
  wins: number;
  total_score: number;
  best_score: number;
}

export interface ServerMessage {
  event: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: any;
}

export type SendFn = (event: string, data?: object) => void;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type SubscribeFn = (event: string, fn: (data: any) => void) => () => void;
