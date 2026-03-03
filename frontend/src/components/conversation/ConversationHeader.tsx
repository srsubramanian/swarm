import type { Conversation, ViewMode } from '../../types';
import Badge from '../shared/Badge';
import { ClockIcon, ChatBubbleLeftRightIcon } from '@heroicons/react/20/solid';

interface ConversationHeaderProps {
  conversation: Conversation;
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
}

const statusConfig: Record<string, { label: string; classes: string }> = {
  live: {
    label: 'Live',
    classes: 'bg-green-50 text-green-700 ring-green-600/20',
  },
  awaiting_decision: {
    label: 'Awaiting Decision',
    classes: 'bg-blue-50 text-blue-700 ring-blue-600/20',
  },
  concluded: {
    label: 'Concluded',
    classes: 'bg-gray-50 text-gray-600 ring-gray-500/20',
  },
};

export default function ConversationHeader({
  conversation,
  viewMode,
  onViewModeChange,
}: ConversationHeaderProps) {
  const time = new Date(conversation.startedAt).toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  });

  const status = statusConfig[conversation.status] || statusConfig.awaiting_decision;

  return (
    <div className="bg-white border-b border-gray-200 px-6 py-4">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold text-gray-900">
              {conversation.title}
            </h2>
            <Badge level={conversation.riskLevel} />
            <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${status.classes}`}>
              {status.label}
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
