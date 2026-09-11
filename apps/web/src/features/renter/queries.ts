'use client';

import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api';
import {
  MeResponseSchema,
  RenterActivationResponseSchema,
  RenterOverviewResponseSchema,
  RenterPublicationListResponseSchema,
} from '@/lib/contracts';

export function useRenterMe() {
  return useQuery({
    queryKey: ['me'],
    queryFn: () => api('/me', MeResponseSchema),
  });
}

export function useRenterOverview(tenancyId: string) {
  return useQuery({
    queryKey: ['renter', tenancyId, 'overview'],
    queryFn: async () => {
      const overview = await api(`/renter/${tenancyId}`, RenterOverviewResponseSchema);
      if (overview.tenancyId !== tenancyId) throw new Error('Renter overview tenancy mismatch');
      return overview;
    },
    retry: false,
  });
}

export function useRenterContextOverviews(tenancyIds: string[]) {
  return useQueries({
    queries: tenancyIds.map((tenancyId) => ({
      queryKey: ['renter', tenancyId, 'overview'],
      queryFn: async () => {
        const overview = await api(`/renter/${tenancyId}`, RenterOverviewResponseSchema);
        if (overview.tenancyId !== tenancyId) throw new Error('Renter overview tenancy mismatch');
        return overview;
      },
      retry: false,
    })),
  });
}

export function useRenterPublications(tenancyId: string) {
  return useQuery({
    queryKey: ['renter', tenancyId, 'documents'],
    queryFn: async () => {
      const publications = await api(
        `/renter/${tenancyId}/documents`,
        RenterPublicationListResponseSchema,
      );
      if (publications.documents.some((document) => document.tenancyId !== tenancyId)) {
        throw new Error('Renter publication tenancy mismatch');
      }
      return publications;
    },
    retry: false,
  });
}

export function useActivateRenterAccess(tenancyId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (activationCode: string) => {
      const response = await api(
        `/renter/${tenancyId}/activation`,
        RenterActivationResponseSchema,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ activationCode }),
        },
      );
      if (response.tenancyId !== tenancyId) {
        throw new Error('Activation response tenancy mismatch');
      }
      return response;
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['me'] }),
        queryClient.invalidateQueries({ queryKey: ['renter', tenancyId] }),
      ]);
    },
  });
}
