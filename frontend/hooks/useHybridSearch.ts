"use client";

import useSWR from "swr";

import { searchProducts } from "@/services/products";

export function useHybridSearch(query: string, limit = 20) {
  const cleanQuery = query.trim();

  return useSWR(
    cleanQuery ? ["hybrid-search", cleanQuery, limit] : null,
    () => searchProducts(cleanQuery, limit),
    {
      keepPreviousData: true,
    },
  );
}
