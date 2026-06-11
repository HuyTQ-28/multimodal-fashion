"use client";

import useSWR from "swr";

import { getHomeFeed } from "@/services/products";

export function useHomeFeed(limit = 20) {
  return useSWR(["home-feed", limit], () => getHomeFeed(limit), {
    keepPreviousData: true,
  });
}
