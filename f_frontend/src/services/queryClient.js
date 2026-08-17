import { QueryClient } from '@tanstack/react-query';

/**
 * Centralized TanStack Query Client for PrepFly Browser Caching Architecture:
 * - staleTime: 5 minutes (prevents duplicate network requests when switching tabs)
 * - gcTime: 30 minutes (retains cache in memory for fast page transitions)
 * - refetchOnWindowFocus: false (avoids disruptive background re-fetching)
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      gcTime: 30 * 60 * 1000,
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
});
