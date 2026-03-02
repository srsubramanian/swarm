import type { RiskLevel } from '../../types';

const lightConfig: Record<RiskLevel, { classes: string; dotClass: string }> = {
  critical: {
    classes: 'bg-red-50 text-red-700 ring-red-600/20',
    dotClass: 'bg-red-500',
  },
  high: {
    classes: 'bg-orange-50 text-orange-700 ring-orange-600/20',
    dotClass: 'bg-orange-500',
  },
  medium: {
    classes: 'bg-yellow-50 text-yellow-700 ring-yellow-600/20',
    dotClass: 'bg-yellow-500',
  },
  low: {
    classes: 'bg-green-50 text-green-700 ring-green-600/20',
    dotClass: 'bg-green-500',
  },
};

const darkConfig: Record<RiskLevel, { classes: string; dotClass: string }> = {
  critical: {
    classes: 'bg-red-400/10 text-red-400 ring-red-400/20',
    dotClass: 'bg-red-400',
  },
  high: {
    classes: 'bg-orange-400/10 text-orange-400 ring-orange-400/20',
    dotClass: 'bg-orange-400',
  },
  medium: {
    classes: 'bg-yellow-400/10 text-yellow-400 ring-yellow-400/20',
    dotClass: 'bg-yellow-400',
  },
  low: {
    classes: 'bg-green-400/10 text-green-400 ring-green-400/20',
    dotClass: 'bg-green-400',
  },
};

const labels: Record<RiskLevel, string> = {
  critical: 'Critical',
  high: 'High',
  medium: 'Medium',
  low: 'Low',
};

interface BadgeProps {
  level: RiskLevel;
  dark?: boolean;
}

export default function Badge({ level, dark = false }: BadgeProps) {
  const { classes, dotClass } = dark ? darkConfig[level] : lightConfig[level];

  return (
    <span
      className={`inline-flex items-center gap-x-1.5 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${classes}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${dotClass}`} />
      {labels[level]}
    </span>
  );
}
