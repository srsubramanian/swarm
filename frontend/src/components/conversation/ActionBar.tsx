import { useState } from 'react';
import type { ActionOption } from '../../types';
import { BookOpenIcon, CheckCircleIcon } from '@heroicons/react/20/solid';

interface ActionBarProps {
  options: ActionOption[];
  isActioned: boolean;
  actionedOptionId?: string;
  onAction: (optionId: string, justification?: string) => void;
  memoryOpen: boolean;
  onToggleMemory: () => void;
  isPending?: boolean;
}

const variantClasses: Record<string, { base: string; confirming: string }> = {
  primary: {
    base: 'bg-indigo-600 text-white hover:bg-indigo-500',
    confirming: 'bg-indigo-700 text-white ring-2 ring-indigo-300',
  },
  secondary: {
    base: 'bg-white text-gray-700 ring-1 ring-inset ring-gray-300 hover:bg-gray-50',
    confirming: 'bg-gray-100 text-gray-900 ring-2 ring-gray-400',
  },
  danger: {
    base: 'bg-red-600 text-white hover:bg-red-500',
    confirming: 'bg-red-700 text-white ring-2 ring-red-300',
  },
};

export default function ActionBar({
  options,
  isActioned,
  actionedOptionId,
  onAction,
  memoryOpen,
  onToggleMemory,
  isPending = false,
}: ActionBarProps) {
  const [confirmingId, setConfirmingId] = useState<string | null>(null);
  const [justification, setJustification] = useState('');
  const [showJustification, setShowJustification] = useState(false);

  const handleClick = (option: ActionOption) => {
    if (isPending) return;

    if (option.variant === 'danger' && confirmingId !== option.id) {
      // First click on danger action — show justification field
      setConfirmingId(option.id);
      setShowJustification(true);
      setJustification('');
      return;
    }

    if (confirmingId === option.id) {
      onAction(option.id, justification || undefined);
      setConfirmingId(null);
      setShowJustification(false);
      setJustification('');
    } else {
      setConfirmingId(option.id);
      setShowJustification(false);
    }
  };

  const actionedLabel = actionedOptionId
    ? options.find((o) => o.id === actionedOptionId)?.label
    : null;

  return (
    <div className="bg-white border-t border-gray-200 px-6 py-3">
      {showJustification && confirmingId && (
        <div className="mb-3 flex items-center gap-2">
          <input
            type="text"
            value={justification}
            onChange={(e) => setJustification(e.target.value)}
            placeholder="Justification required for this action..."
            className="flex-1 rounded-md border-gray-300 px-3 py-1.5 text-sm ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-inset focus:ring-red-500"
          />
        </div>
      )}
      <div className="flex items-center justify-between">
        <button
          onClick={onToggleMemory}
          className={`inline-flex items-center gap-1.5 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
            memoryOpen
              ? 'bg-amber-50 text-amber-700 ring-1 ring-amber-200'
              : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
          }`}
        >
          <BookOpenIcon className="h-4 w-4" />
          Client Memory
        </button>

        <div className="flex items-center gap-3">
          {isPending ? (
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <span className="inline-block h-3 w-3 rounded-full border-2 border-gray-400 border-t-transparent animate-spin" />
              Processing...
            </div>
          ) : isActioned ? (
            <div className="flex items-center gap-2 text-sm text-green-700 font-medium">
              <CheckCircleIcon className="h-5 w-5 text-green-500" />
              Actioned: {actionedLabel}
            </div>
          ) : (
            options.map((option) => {
              const isConfirming = confirmingId === option.id;
              const classes = variantClasses[option.variant];

              return (
                <button
                  key={option.id}
                  onClick={() => handleClick(option)}
                  disabled={isPending}
                  className={`rounded-md px-4 py-2 text-sm font-semibold transition-all disabled:opacity-50 ${
                    isConfirming ? classes.confirming : classes.base
                  }`}
                >
                  {isConfirming ? 'Click again to confirm' : option.label}
                </button>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
