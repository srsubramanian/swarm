import { useCallback, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';

interface SSEState {
  isStreaming: boolean;
  events: Array<{ event: string; data: unknown }>;
}

export function useStreamingAnalysis() {
  const queryClient = useQueryClient();
  const [state, setState] = useState<SSEState>({ isStreaming: false, events: [] });
  const abortRef = useRef<AbortController | null>(null);

  const startStream = useCallback(async (scenario: string) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setState({ isStreaming: true, events: [] });

    try {
      const resp = await fetch('/api/queue/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario }),
        signal: controller.signal,
      });

      if (!resp.ok || !resp.body) {
        setState((s) => ({ ...s, isStreaming: false }));
        return;
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        let eventType = '';
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith('data: ') && eventType) {
            try {
              const data = JSON.parse(line.slice(6));
              setState((s) => ({
                ...s,
                events: [...s.events, { event: eventType, data }],
              }));
              if (eventType === 'done') {
                queryClient.invalidateQueries({ queryKey: ['conversations'] });
              }
            } catch {
              // skip invalid JSON
            }
            eventType = '';
          }
        }
      }
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') return;
    } finally {
      setState((s) => ({ ...s, isStreaming: false }));
    }
  }, [queryClient]);

  const stopStream = useCallback(() => {
    abortRef.current?.abort();
    setState((s) => ({ ...s, isStreaming: false }));
  }, []);

  return { ...state, startStream, stopStream };
}
