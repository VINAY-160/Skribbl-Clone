import { useState } from "react";
import Canvas from "../components/Canvas";
import ChatPanel from "../components/ChatPanel";
import DrawingToolbar, { COLORS, SIZES } from "../components/DrawingToolbar";
import PlayerList from "../components/PlayerList";
import Timer from "../components/Timer";
import WordSelector from "../components/WordSelector";
import type { GameState } from "../state/gameReducer";
import type { SendFn, SubscribeFn, Tool } from "../types/game";

interface Props { state: GameState; send: SendFn; subscribe: SubscribeFn }

const REASONS: Record<string, string> = {
  time_up: "Time's up", all_guessed: "Everyone guessed it", drawer_left: "The drawer left",
};

export default function Game({ state, send, subscribe }: Props) {
  const [tool, setTool] = useState<Tool>("pen");
  const [color, setColor] = useState(COLORS[0]);
  const [size, setSize] = useState(SIZES[1]);

  const me = state.players.find((p) => p.id === state.playerId);
  const drawer = state.players.find((p) => p.id === state.drawerId);
  const isDrawer = state.drawerId === state.playerId;
  const isHost = state.playerId === state.hostId;
  const drawing = state.phase === "drawing";
  const total = drawing ? state.settings?.draw_time ?? 0 : state.chooseTime;

  let headline: string;
  if (state.phase === "choosing_word") headline = isDrawer ? "Choose a word" : `${drawer?.name ?? "Someone"} is choosing a word`;
  else if (state.phase === "turn_end") headline = `The word was ${state.word ?? "..."}`;
  else if (isDrawer) headline = state.word ?? "";
  else headline = state.hint ?? "???";

  const canGuess = drawing && !isDrawer && !me?.has_guessed;
  const placeholder = canGuess ? "Type your guess" : isDrawer && drawing ? "Chat with players who guessed" : "Say something";

  return (
    <main className="game">
      <header className="topbar">
        <span className="muted">Round {state.round}/{state.totalRounds}</span>
        <span className={`headline ${isDrawer || state.phase !== "drawing" ? "plain" : "hint"}`}>{headline}</span>
        <Timer timeLeft={state.timeLeft} total={total} />
      </header>

      <aside className="side-players">
        <PlayerList players={state.players} meId={state.playerId} mode="game" canModerate={isHost}
                    onKick={(id) => send("kick", { player_id: id })} onBan={(id) => send("ban", { player_id: id })}
                    onVotekick={(id) => send("votekick", { player_id: id })} />
      </aside>

      <section className="stage">
        <Canvas interactive={isDrawer && drawing} tool={tool} color={color} size={size}
                initialStrokes={state.initialStrokes} send={send} subscribe={subscribe}>
          {state.phase === "choosing_word" && isDrawer && state.wordOptions && (
            <WordSelector options={state.wordOptions} timeLeft={state.timeLeft}
                          onPick={(word) => send("word_chosen", { word })} />
          )}
          {state.phase === "turn_end" && state.roundEnd && (
            <div className="overlay">
              <div className="panel">
                <h2>{REASONS[state.roundEnd.reason] ?? "Round over"}</h2>
                <p className="muted">The word was <b>{state.roundEnd.word ?? "not chosen"}</b></p>
                <ul className="list">
                  {[...state.roundEnd.players].sort((a, b) => b.turn_points - a.turn_points).map((p) => (
                    <li key={p.id}>
                      <span className="grow">{p.name}</span>
                      <strong>{p.turn_points > 0 ? `+${p.turn_points}` : "0"}</strong>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </Canvas>
        {isDrawer && drawing && (
          <DrawingToolbar tool={tool} color={color} size={size} onTool={setTool} onColor={setColor}
                          onSize={setSize} onUndo={() => send("draw_undo")} onClear={() => send("canvas_clear")} />
        )}
      </section>

      <aside className="side-chat">
        <ChatPanel messages={state.messages} placeholder={placeholder}
                   onSend={(text) => send(canGuess ? "guess" : "chat", { text })} />
      </aside>
    </main>
  );
}
