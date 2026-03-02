import { useState, useEffect, useCallback } from 'react';
import type { Conversation, ViewMode, AgentRole } from '../../types';
import QueueList from '../sidebar/QueueList';
import ConversationHeader from '../conversation/ConversationHeader';
import MessageList from '../conversation/MessageList';
import ModeratorSummary from '../conversation/ModeratorSummary';
import ActionBar from '../conversation/ActionBar';
import MemoryDrawer from '../memory/MemoryDrawer';
import AgentIcon from '../shared/AgentIcon';

const API_POLL_INTERVAL = 3000;

export default function AppShell() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('full');
  const [memoryOpen, setMemoryOpen] = useState(false);
  const [actionedMap, setActionedMap] = useState<Record<string, string>>({});

  const fetchConversations = useCallback(async () => {
    try {
      const resp = await fetch('/api/conversations');
      if (!resp.ok) return;
      const data: Conversation[] = await resp.json();
      setConversations(data);
      setSelectedId((prev) => {
        if (data.length === 0) return null;
        if (!prev || !data.find((c) => c.id === prev)) return data[0].id;
        return prev;
      });
    } catch {
      // API not available
    }
  }, []);

  useEffect(() => {
    fetchConversations();
    const interval = setInterval(fetchConversations, API_POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchConversations]);

  const conversation = selectedId ? conversations.find((c) => c.id === selectedId) : null;

  const handleSelectConversation = (id: string) => {
    setSelectedId(id);
    setMemoryOpen(false);
  };

  const handleAction = (optionId: string) => {
    if (selectedId) {
      setActionedMap((prev) => ({ ...prev, [selectedId]: optionId }));
    }
  };

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
          actionedMap={actionedMap}
          onSelect={handleSelectConversation}
        />

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
              isActioned={!!actionedMap[selectedId!]}
              actionedOptionId={actionedMap[selectedId!]}
              onAction={handleAction}
              memoryOpen={memoryOpen}
              onToggleMemory={() => setMemoryOpen((prev) => !prev)}
            />
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <p className="text-lg font-medium text-gray-400">No events in queue</p>
              <p className="text-sm text-gray-300 mt-1">
                Submit a scenario via the API to get started
              </p>
              <code className="block mt-4 text-xs text-gray-400 bg-gray-100 rounded-lg px-4 py-3">
                curl -X POST /api/queue -H &quot;Content-Type: application/json&quot; -d
                &#123;&quot;scenario&quot;:&quot;wire_transfer&quot;&#125;
              </code>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
