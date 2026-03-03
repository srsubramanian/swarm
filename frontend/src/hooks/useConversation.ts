import { useQuery } from '@tanstack/react-query';
import type { Conversation } from '../types';

export function useConversation(id: string | null) {
  return useQuery<Conversation>({
    queryKey: ['conversation', id],
    queryFn: () => fetch(`/api/conversations/${id}`).then((r) => r.json()),
    enabled: !!id,
  });
}
