'use client';

import { useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api';
import {
  DemoSummaryResponseSchema,
  HealthResponseSchema,
  type DemoSummaryResponse,
  type HealthResponse,
} from '@/lib/contracts';

/** Server state for the demo feature — all data flows through the interceptor. */

export function useHealth() {
  return useQuery<HealthResponse>({
    queryKey: ['health'],
    queryFn: () => api('/health', HealthResponseSchema),
  });
}

export function useDemoSummary() {
  return useQuery<DemoSummaryResponse>({
    queryKey: ['demo', 'summary'],
    queryFn: () => api('/demo/summary', DemoSummaryResponseSchema),
  });
}
