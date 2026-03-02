import type { AgentRole } from '../../types';
import AgentIcon from '../shared/AgentIcon';
import FormattedContent from '../shared/FormattedContent';

const borderColors: Record<AgentRole | 'moderator', string> = {
  compliance: 'border-indigo-400',
  security: 'border-rose-400',
  engineering: 'border-emerald-400',
  moderator: 'border-violet-400',
};

interface MessageBubbleProps {
  agentRole: AgentRole | 'moderator';
  agentName: string;
  content: string;
  timestamp: string;
}

export default function MessageBubble({
  agentRole,
  agentName,
  content,
  timestamp,
}: MessageBubbleProps) {
  const time = new Date(timestamp).toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  });

  return (
    <div className="flex gap-3">
      <AgentIcon role={agentRole} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-medium text-gray-900">{agentName}</span>
          <span className="text-xs text-gray-400">{time}</span>
        </div>
        <div
          className={`bg-white rounded-lg p-4 border-l-4 ${borderColors[agentRole]} shadow-sm ring-1 ring-gray-900/5`}
        >
          <FormattedContent content={content} />
        </div>
      </div>
    </div>
  );
}
