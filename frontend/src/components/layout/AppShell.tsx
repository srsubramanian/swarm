import { useState, useEffect } from 'react';
import type { ViewMode, AgentRole } from '../../types';
import { useConversations } from '../../hooks/useConversations';
import { useDecision } from '../../hooks/useDecision';
import QueueList from '../sidebar/QueueList';
import ScenarioPanel from '../ScenarioPanel';
import ConversationHeader from '../conversation/ConversationHeader';
import MessageList from '../conversation/MessageList';
import ModeratorSummary from '../conversation/ModeratorSummary';
import ActionBar from '../conversation/ActionBar';
import MemoryDrawer from '../memory/MemoryDrawer';
import AgentIcon from '../shared/AgentIcon';

export default function AppShell() {
  const { data: conversations = [] } = useConversations();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('full');
  const [memoryOpen, setMemoryOpen] = useState(false);
  const decisionMutation = useDecision();

  // Auto-select first conversation if none selected
  useEffect(() => {
    if (conversations.length > 0 && (!selectedId || !conversations.find((c) => c.id === selectedId))) {
      setSelectedId(conversations[0].id);
    }
    if (conversations.length === 0) {
      setSelectedId(null);
    }
  }, [conversations, selectedId]);

  const conversation = selectedId ? conversations.find((c) => c.id === selectedId) : null;

  const handleSelectConversation = (id: string) => {
    setSelectedId(id);
    setMemoryOpen(false);
  };

  const handleAction = (optionId: string, justification?: string) => {
    if (!selectedId || !conversation) return;

    const option = conversation.actionRequired.options.find((o) => o.id === optionId);
    const action = option?.variant === 'danger' ? 'escalate' : option?.variant === 'primary' ? 'approve' : 'reject';

    decisionMutation.mutate({
      conversationId: selectedId,
      optionId,
      action,
      justification: justification || '',
    });
  };

  const isActioned = conversation?.status === 'concluded';
  const actionedOptionId = conversation?.actionRequired?.actionedOption || undefined;

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="w-80 bg-gray-900 flex flex-col shrink-0">
        <div className="px-5 py-4 border-b border-gray-800">
          <h1 className="text-lg font-bold text-white tracking-tight">SwarmOps</h1>
          <p className="text-xs text-gray-400 mt-0.5">RM Console</p>
        </div>

        <QueueList
          conversations={conversations}
          selectedId={selectedId}
          onSelect={handleSelectConversation}
        />

        <ScenarioPanel />

        <div className="px-5 py-3 border-t border-gray-800">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
            System Status
          </p>
          <div className="flex items-center gap-4">
            {(['compliance', 'security', 'engineering'] as AgentRole[]).map((role) => (
              <div key={role} className="flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-green-400" />
                <span className="text-xs text-gray-400 capitalize">{role}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {conversation ? (
          <>
            <ConversationHeader
              conversation={conversation}
              viewMode={viewMode}
              onViewModeChange={setViewMode}
            />

            <div className="flex-1 overflow-y-auto">
              {viewMode === 'full' ? (
                <MessageList messages={conversation.messages} />
              ) : (
                <div className="max-w-3xl mx-auto px-6 py-6 space-y-3">
                  {conversation.agents.map((agent) => (
                    <div
                      key={agent.role}
                      className="flex items-start gap-3 rounded-lg bg-white p-4 shadow-sm ring-1 ring-gray-900/5"
                    >
                      <AgentIcon role={agent.role} />
                      <div>
                        <p className="text-sm font-medium text-gray-900">{agent.name}</p>
                        <p className="text-sm text-gray-600 mt-0.5">{agent.position}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <div className="max-w-3xl mx-auto px-6 pb-6">
                <ModeratorSummary summary={conversation.moderatorSummary} />
              </div>
            </div>

            {memoryOpen && (
              <MemoryDrawer
                memory={conversation.clientMemory}
                onClose={() => setMemoryOpen(false)}
              />
            )}

            <ActionBar
              options={conversation.actionRequired.options}
              isActioned={isActioned}
              actionedOptionId={actionedOptionId}
              onAction={handleAction}
              memoryOpen={memoryOpen}
              onToggleMemory={() => setMemoryOpen((prev) => !prev)}
              isPending={decisionMutation.isPending}
            />
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <p className="text-lg font-medium text-gray-400">No events in queue</p>
              <p className="text-sm text-gray-300 mt-1">
                Use the sidebar to submit a scenario
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
