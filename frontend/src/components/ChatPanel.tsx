import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import type { ChatMessage } from "../types/game";

interface Props {
  messages: ChatMessage[];
  placeholder: string;
  onSend: (text: string) => void;
}

export default function ChatPanel({ messages, placeholder, onSend }: Props) {
  const [text, setText] = useState("");
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages.length]);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const t = text.trim();
    if (!t) return;
    onSend(t);
    setText("");
  };

  return (
    <div className="chat">
      <div className="chat-list" ref={listRef}>
        {messages.map((m) => (
          <p key={m.id} className={`msg ${m.kind}`}>
            {m.kind === "guess" || m.kind === "chat" ? <b>{m.player_name}: </b> : null}
            {m.text}
          </p>
        ))}
      </div>
      <form onSubmit={submit} className="chat-form">
        <input value={text} onChange={(e) => setText(e.target.value)} placeholder={placeholder}
               maxLength={200} autoComplete="off" />
      </form>
    </div>
  );
}
