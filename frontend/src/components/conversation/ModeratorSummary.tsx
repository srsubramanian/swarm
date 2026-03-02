import type { ModeratorSummaryData } from '../../types';
import AgentIcon from '../shared/AgentIcon';
import { CheckCircleIcon } from '@heroicons/react/20/solid';

interface ModeratorSummaryProps {
  summary: ModeratorSummaryData;
}

export default function ModeratorSummary({ summary }: ModeratorSummaryProps) {
  return (
    <div className="bg-violet-50 rounded-lg border border-violet-200 overflow-hidden">
      <div className="flex items-center gap-2 px-5 py-3 bg-violet-100/50 border-b border-violet-200">
        <AgentIcon role="moderator" size="sm" />
        <h3 className="text-sm font-semibold text-violet-900">Moderator Synthesis</h3>
      </div>

      <div className="px-5 py-4 space-y-4">
        <div>
          <dt className="text-xs font-medium text-violet-600 uppercase tracking-wider">
            Status
          </dt>
          <dd className="mt-1 text-sm font-medium text-gray-900">{summary.status}</dd>
        </div>

        <div>
          <dt className="text-xs font-medium text-violet-600 uppercase tracking-wider">
            Consensus
          </dt>
          <dd className="mt-1 text-sm text-gray-700">{summary.consensus}</dd>
        </div>

        <div>
          <dt className="text-xs font-medium text-violet-600 uppercase tracking-wider">
            Key Decisions
          </dt>
          <dd className="mt-1">
            <ul className="space-y-1.5">
              {summary.keyDecisions.map((decision, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                  <CheckCircleIcon className="h-4 w-4 text-violet-400 mt-0.5 shrink-0" />
                  {decision}
                </li>
              ))}
            </ul>
          </dd>
        </div>

        <div>
          <dt className="text-xs font-medium text-violet-600 uppercase tracking-wider">
            Risk Assessment
          </dt>
          <dd className="mt-1 text-sm font-medium text-gray-900">
            {summary.riskAssessment}
          </dd>
        </div>

        <div>
          <dt className="text-xs font-medium text-violet-600 uppercase tracking-wider">
            Recommended Next Steps
          </dt>
          <dd className="mt-1">
            <ol className="space-y-1.5 list-decimal list-inside">
              {summary.nextSteps.map((step, i) => (
                <li key={i} className="text-sm text-gray-700">
                  {step}
                </li>
              ))}
            </ol>
          </dd>
        </div>
      </div>
    </div>
  );
}
