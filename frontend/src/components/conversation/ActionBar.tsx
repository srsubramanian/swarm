import { useState } from 'react';
import type { ActionOption } from '../../types';
import { BookOpenIcon, CheckCircleIcon } from '@heroicons/react/20/solid';

interface ActionBarProps {
  options: ActionOption[];
  isActioned: boolean;
  actionedOptionId?: string;
  onAction: (optionId: string) => void;
  memoryOpen: boolean;
  onToggleMemory: () => void;
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
}: ActionBarProps) {
  const [confirmingId, setConfirmingId] = useState<string | null>(null);

  const handleClick = (option: ActionOption) => {
    if (confirmingId === option.id) {
      onAction(option.id);
      setConfirmingId(null);
    } else {
      setConfirmingId(option.id);
    }
  };

  const actionedLabel = actionedOptionId
    ? options.find((o) => o.id === actionedOptionId)?.label
    : null;

  return (
    <div className="bg-white border-t border-gray-200 px-6 py-3">
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
          {isActioned ? (
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
                  className={`rounded-md px-4 py-2 text-sm font-semibold transition-all ${
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
