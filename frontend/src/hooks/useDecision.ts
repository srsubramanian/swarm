import { useMutation, useQueryClient } from '@tanstack/react-query';

interface DecisionInput {
  conversationId: string;
  optionId: string;
  action: string;
  justification: string;
}

export function useDecision() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ conversationId, optionId, action, justification }: DecisionInput) =>
      fetch(`/api/decisions/${conversationId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          option_id: optionId,
          action,
          justification,
        }),
      }).then((r) => r.json()),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
      queryClient.invalidateQueries({ queryKey: ['conversation', variables.conversationId] });
    },
  });
}
