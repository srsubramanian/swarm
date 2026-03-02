import type { Conversation } from '../../types';
import Badge from '../shared/Badge';
import AgentIcon from '../shared/AgentIcon';
import { ChatBubbleLeftRightIcon } from '@heroicons/react/20/solid';

interface QueueItemProps {
  conversation: Conversation;
  selected: boolean;
  actioned: boolean;
  onClick: () => void;
}

export default function QueueItem({
  conversation,
  selected,
  actioned,
  onClick,
}: QueueItemProps) {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-4 py-3 border-l-2 transition-colors ${
        selected
          ? 'bg-gray-800 border-indigo-400'
          : 'border-transparent hover:bg-gray-800/50'
      }`}
    >
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm font-medium text-white truncate pr-2">
          {conversation.clientName}
        </span>
        <Badge level={conversation.riskLevel} dark />
      </div>
      <p className="text-xs text-gray-400 truncate mb-2">{conversation.title}</p>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1">
          {conversation.agents.map((a) => (
            <AgentIcon key={a.role} role={a.role} size="sm" />
          ))}
        </div>
        <div className="flex items-center gap-2">
          {actioned && (
            <span className="text-xs text-green-400 font-medium">Actioned</span>
          )}
          <span className="flex items-center gap-1 text-xs text-gray-500">
            <ChatBubbleLeftRightIcon className="h-3.5 w-3.5" />
            {conversation.messageCount}
          </span>
        </div>
      </div>
    </button>
  );
}
