"use client";

import useSWR from "swr";

import { getRecommendations } from "@/services/products";

export function useRecommendations(
  sessionId: string | null,
  limit = 20,
  enabled = true,
) {
  return useSWR(
    sessionId && enabled ? ["recommendations", sessionId, limit] : null,
    () => getRecommendations(sessionId as string, limit),
    {
      keepPreviousData: true,
    },
  );
}
