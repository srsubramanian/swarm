import { useEffect, useRef } from 'react';
import type { Message } from '../../types';
import MessageBubble from './MessageBubble';

interface MessageListProps {
  messages: Message[];
}

export default function MessageList({ messages }: MessageListProps) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="max-w-3xl mx-auto px-6 py-6 space-y-6">
      {messages.map((msg) => (
        <MessageBubble
          key={msg.id}
          agentRole={msg.agentRole}
          agentName={msg.agentName}
          content={msg.content}
          timestamp={msg.timestamp}
        />
      ))}
      <div ref={endRef} />
    </div>
  );
}
