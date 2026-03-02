import type { Conversation, ViewMode } from '../../types';
import Badge from '../shared/Badge';
import { ClockIcon, ChatBubbleLeftRightIcon } from '@heroicons/react/20/solid';

interface ConversationHeaderProps {
  conversation: Conversation;
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
}

export default function ConversationHeader({
  conversation,
  viewMode,
  onViewModeChange,
}: ConversationHeaderProps) {
  const time = new Date(conversation.startedAt).toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  });

  return (
    <div className="bg-white border-b border-gray-200 px-6 py-4">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold text-gray-900">
              {conversation.title}
            </h2>
            <Badge level={conversation.riskLevel} />
            <span className="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700 ring-1 ring-inset ring-blue-600/20">
              Awaiting Decision
            </span>
          </div>
          <div className="flex items-center gap-4 mt-1.5">
            <span className="text-sm text-gray-500">{conversation.clientName}</span>
            <span className="text-gray-300">·</span>
            <span className="text-sm text-gray-500">{conversation.eventType}</span>
            <span className="text-gray-300">·</span>
            <span className="flex items-center gap-1 text-sm text-gray-500">
              <ClockIcon className="h-3.5 w-3.5" />
              {time}
            </span>
            <span className="text-gray-300">·</span>
            <span className="flex items-center gap-1 text-sm text-gray-500">
              <ChatBubbleLeftRightIcon className="h-3.5 w-3.5" />
              {conversation.messageCount} messages
            </span>
          </div>
        </div>

        <div className="flex items-center rounded-lg bg-gray-100 p-0.5">
          <button
            onClick={() => onViewModeChange('full')}
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              viewMode === 'full'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            Full Chat
          </button>
          <button
            onClick={() => onViewModeChange('summary')}
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              viewMode === 'summary'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            Summary
          </button>
        </div>
      </div>
    </div>
  );
}
