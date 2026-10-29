import type { SocketStatus } from "../services/websocket";
import type {
  ChatMessage, GameOver, Phase, Player, RoundEnd, Settings, Stroke,
} from "../types/game";

export interface GameState {
  status: SocketStatus;
  playerId: string | null;
  phase: Phase;
  round: number;
  totalRounds: number;
  drawerId: string | null;
  hostId: string | null;
  players: Player[];
  settings: Settings | null;
  hint: string | null;
  word: string | null;
  wordOptions: string[] | null;
  timeLeft: number;
  chooseTime: number;
  messages: ChatMessage[];
  initialStrokes: Stroke[];
  roundEnd: RoundEnd | null;
  gameOver: GameOver | null;
  error: string | null;
  kicked: boolean;
  nextId: number;
}

export const initialState: GameState = {
  status: "idle", playerId: null, phase: "lobby", round: 0, totalRounds: 0,
  drawerId: null, hostId: null, players: [], settings: null, hint: null, word: null,
  wordOptions: null, timeLeft: 0, chooseTime: 15, messages: [], initialStrokes: [],
  roundEnd: null, gameOver: null, error: null, kicked: false, nextId: 1,
};

export type Action =
  | { type: "reset" }
  | { type: "status"; status: SocketStatus }
  | { type: "clear_error" }
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  | { type: "server"; event: string; data: any };

function addMessage(state: GameState, msg: Omit<ChatMessage, "id">): Partial<GameState> {
  const messages = [...state.messages, { ...msg, id: state.nextId }].slice(-200);
  return { messages, nextId: state.nextId + 1 };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function snapshot(s: any): Partial<GameState> {
  return {
    phase: s.phase, round: s.round, totalRounds: s.total_rounds, drawerId: s.drawer_id,
    timeLeft: s.time_left, hint: s.hint, word: s.word, wordOptions: s.word_options,
    players: s.players, hostId: s.host_id, settings: s.settings, initialStrokes: s.strokes ?? [],
  };
}

export function gameReducer(state: GameState, action: Action): GameState {
  switch (action.type) {
    case "reset":
      return { ...initialState };
    case "status":
      return { ...state, status: action.status };
    case "clear_error":
      return { ...state, error: null };
    case "server":
      return applyEvent(state, action.event, action.data);
  }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function applyEvent(state: GameState, event: string, d: any): GameState {
  switch (event) {
    case "joined":
      return { ...state, playerId: d.player_id, ...snapshot(d.state) };
    case "game_state":
      return { ...state, ...snapshot(d) };
    case "player_joined":
    case "player_left":
    case "players_update":
      return { ...state, players: d.players, hostId: d.host_id ?? state.hostId };
    case "settings_updated":
      return { ...state, settings: d.settings };
    case "game_started":
      return { ...state, players: d.players, gameOver: null, roundEnd: null };
    case "round_start":
      return {
        ...state, phase: "choosing_word", round: d.round, totalRounds: d.total_rounds,
        drawerId: d.drawer_id, players: d.players, word: null, hint: null, wordOptions: null,
        timeLeft: d.choose_time, chooseTime: d.choose_time, roundEnd: null, initialStrokes: [],
      };
    case "word_options":
      return { ...state, wordOptions: d.options };
    case "drawing_start":
      return {
        ...state, phase: "drawing", hint: d.hint, word: d.word ?? null, wordOptions: null,
        timeLeft: d.draw_time,
      };
    case "timer":
      return { ...state, timeLeft: d.time_left };
    case "hint":
      return { ...state, hint: d.hint };
    case "guess_result":
      return {
        ...state, players: d.players,
        ...addMessage(state, { kind: "correct", text: `${d.player_name} guessed the word! +${d.points}` }),
      };
    case "close_guess":
      return { ...state, ...addMessage(state, { kind: "system", text: `"${d.text}" is close!` }) };
    case "chat_message":
      return {
        ...state,
        ...addMessage(state, { kind: d.kind, player_name: d.player_name, text: d.text }),
      };
    case "round_end":
      return {
        ...state, phase: "turn_end", word: d.word, players: d.players,
        roundEnd: { word: d.word, reason: d.reason, drawer_points: d.drawer_points, players: d.players },
      };
    case "game_over":
      return { ...state, phase: "game_over", gameOver: d, word: null };
    case "kicked":
      return { ...state, kicked: true };
    case "error":
      return { ...state, error: d.message };
    default:
      return state;
  }
}
