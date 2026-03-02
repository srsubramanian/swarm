import {
  ShieldCheckIcon,
  LockClosedIcon,
  WrenchScrewdriverIcon,
  SparklesIcon,
} from '@heroicons/react/20/solid';
import type { AgentRole } from '../../types';

const config: Record<
  AgentRole | 'moderator',
  {
    Icon: React.ComponentType<React.SVGProps<SVGSVGElement>>;
    bg: string;
    text: string;
  }
> = {
  compliance: { Icon: ShieldCheckIcon, bg: 'bg-indigo-100', text: 'text-indigo-600' },
  security: { Icon: LockClosedIcon, bg: 'bg-rose-100', text: 'text-rose-600' },
  engineering: {
    Icon: WrenchScrewdriverIcon,
    bg: 'bg-emerald-100',
    text: 'text-emerald-600',
  },
  moderator: { Icon: SparklesIcon, bg: 'bg-violet-100', text: 'text-violet-600' },
};

interface AgentIconProps {
  role: AgentRole | 'moderator';
  size?: 'sm' | 'md';
}

export default function AgentIcon({ role, size = 'md' }: AgentIconProps) {
  const { Icon, bg, text } = config[role];
  const sizeClasses = size === 'sm' ? 'h-6 w-6' : 'h-8 w-8';
  const iconSize = size === 'sm' ? 'h-3.5 w-3.5' : 'h-4 w-4';

  return (
    <span
      className={`inline-flex items-center justify-center rounded-full ${bg} ${sizeClasses} shrink-0`}
    >
      <Icon className={`${iconSize} ${text}`} />
    </span>
  );
}
