export type RiskLevel = 'critical' | 'high' | 'medium' | 'low';

export type AgentRole = 'compliance' | 'security' | 'engineering';

export type ConversationStatus = 'live' | 'awaiting_decision' | 'concluded';

export type ViewMode = 'full' | 'summary';

export interface AgentInfo {
  role: AgentRole;
  name: string;
  status: 'analyzing' | 'complete';
  position: string;
}

export interface Message {
  id: string;
  agentRole: AgentRole | 'moderator';
  agentName: string;
  content: string;
  timestamp: string;
}

export interface ActionOption {
  id: string;
  label: string;
  variant: 'primary' | 'secondary' | 'danger';
}

export interface ActionRequired {
  status: 'pending' | 'actioned';
  options: ActionOption[];
  actionedOption?: string;
}

export interface ClientMemory {
  clientName: string;
  content: string;
  lastUpdated: string;
}

export interface ModeratorSummaryData {
  status: string;
  consensus: string;
  keyDecisions: string[];
  riskAssessment: string;
  nextSteps: string[];
}

export interface DecisionPayload {
  optionId: string;
  action: 'approve' | 'reject' | 'escalate' | 'override';
  justification: string;
}

export interface DecisionRecord {
  optionId: string;
  action: string;
  justification: string;
  decidedBy: string;
  decidedAt: string | null;
}

export interface Conversation {
  id: string;
  title: string;
  clientName: string;
  riskLevel: RiskLevel;
  status: ConversationStatus;
  eventType: string;
  startedAt: string;
  messageCount: number;
  agents: AgentInfo[];
  messages: Message[];
  moderatorSummary: ModeratorSummaryData;
  actionRequired: ActionRequired;
  clientMemory: ClientMemory;
  decision?: DecisionRecord | null;
}

export interface Scenario {
  name: string;
  title: string;
  clientName: string;
  eventType: string;
}

export interface SSEEvent {
  event: string;
  data: string;
}
