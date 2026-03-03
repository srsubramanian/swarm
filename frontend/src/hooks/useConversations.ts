import { useQuery } from '@tanstack/react-query';
import type { Conversation } from '../types';

export function useConversations() {
  return useQuery<Conversation[]>({
    queryKey: ['conversations'],
    queryFn: () => fetch('/api/conversations').then((r) => r.json()),
    refetchInterval: 5000,
  });
}
