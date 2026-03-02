import type { Conversation } from '../../types';
import QueueItem from './QueueItem';

interface QueueListProps {
  conversations: Conversation[];
  selectedId: string | null;
  actionedMap: Record<string, string>;
  onSelect: (id: string) => void;
}

export default function QueueList({
  conversations,
  selectedId,
  actionedMap,
  onSelect,
}: QueueListProps) {
  const pendingCount = conversations.filter((c) => !actionedMap[c.id]).length;

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="px-5 py-3">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
            Action Queue
          </h2>
          <span className="inline-flex items-center rounded-full bg-indigo-400/10 px-2 py-0.5 text-xs font-medium text-indigo-400 ring-1 ring-inset ring-indigo-400/20">
            {pendingCount}
          </span>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto">
        {conversations.map((conv) => (
          <QueueItem
            key={conv.id}
            conversation={conv}
            selected={conv.id === selectedId}
            actioned={!!actionedMap[conv.id]}
            onClick={() => onSelect(conv.id)}
          />
        ))}
      </div>
    </div>
  );
}
