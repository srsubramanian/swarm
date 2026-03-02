import type { ClientMemory } from '../../types';
import FormattedContent from '../shared/FormattedContent';
import { XMarkIcon, BookOpenIcon } from '@heroicons/react/20/solid';

interface MemoryDrawerProps {
  memory: ClientMemory;
  onClose: () => void;
}

export default function MemoryDrawer({ memory, onClose }: MemoryDrawerProps) {
  const lastUpdated = new Date(memory.lastUpdated).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });

  return (
    <div className="border-t border-gray-200 bg-amber-50/50 max-h-72 overflow-y-auto">
      <div className="px-6 py-3 flex items-center justify-between bg-amber-100/50 border-b border-amber-200/50 sticky top-0">
        <div className="flex items-center gap-2">
          <BookOpenIcon className="h-4 w-4 text-amber-600" />
          <h3 className="text-sm font-semibold text-amber-900">
            Client Memory — {memory.clientName}
          </h3>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-amber-600">Updated {lastUpdated}</span>
          <button
            onClick={onClose}
            className="text-amber-400 hover:text-amber-600 transition-colors"
          >
            <XMarkIcon className="h-5 w-5" />
          </button>
        </div>
      </div>
      <div className="px-6 py-4">
        <FormattedContent content={memory.content} />
      </div>
    </div>
  );
}
