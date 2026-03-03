import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { Scenario } from '../types';

export function useScenarios() {
  return useQuery<Scenario[]>({
    queryKey: ['scenarios'],
    queryFn: () => fetch('/api/queue/scenarios').then((r) => r.json()),
  });
}

export function useSubmitScenario() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (scenario: string) =>
      fetch('/api/queue', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario }),
      }).then((r) => r.json()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
    },
  });
}
