import { useScenarios, useSubmitScenario } from '../hooks/useScenarios';
import { useStreamingAnalysis } from '../hooks/useSSE';
import { PlusIcon } from '@heroicons/react/20/solid';

export default function ScenarioPanel() {
  const { data: scenarios } = useScenarios();
  const submitMutation = useSubmitScenario();
  const { isStreaming, startStream } = useStreamingAnalysis();

  const handleSubmit = (scenarioName: string) => {
    if (isStreaming || submitMutation.isPending) return;
    startStream(scenarioName);
  };

  if (!scenarios?.length) return null;

  return (
    <div className="px-5 py-3 border-t border-gray-800">
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
        Submit Event
      </p>
      <div className="space-y-1.5">
        {scenarios.map((s) => (
          <button
            key={s.name}
            onClick={() => handleSubmit(s.name)}
            disabled={isStreaming || submitMutation.isPending}
            className="w-full flex items-center gap-2 rounded-md px-3 py-2 text-left text-xs text-gray-300 hover:bg-gray-800 hover:text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <PlusIcon className="h-3.5 w-3.5 shrink-0 text-gray-500" />
            <div className="min-w-0">
              <p className="truncate font-medium">{s.title}</p>
              <p className="truncate text-gray-500">{s.clientName}</p>
            </div>
          </button>
        ))}
      </div>
      {(isStreaming || submitMutation.isPending) && (
        <div className="mt-2 flex items-center gap-2 text-xs text-indigo-400">
          <span className="inline-block h-2 w-2 rounded-full bg-indigo-400 animate-pulse" />
          Processing...
        </div>
      )}
    </div>
  );
}
