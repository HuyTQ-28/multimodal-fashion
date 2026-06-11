"use client";

import { useState } from "react";
import { mutate } from "swr";

import { postInteraction } from "@/services/products";
import type { ActionType, Product } from "@/types/product";
import { useInteractionCounter } from "@/hooks/useInteractionCounter";

export function useProductInteractions(sessionId: string | null) {
  const [pendingKey, setPendingKey] = useState<string | null>(null);
  const {
    canRecommend,
    incrementInteractionCount,
    interactionCount,
    remainingInteractions,
  } = useInteractionCounter();

  async function recordInteraction(
    product: Product,
    actionType: ActionType,
  ): Promise<void> {
    if (!sessionId) {
      return;
    }

    const key = `${product.article_id}:${actionType}`;
    setPendingKey(key);
    try {
      await postInteraction({
        session_id: sessionId,
        article_id: product.article_id,
        action_type: actionType,
      });
      const nextInteractionCount = incrementInteractionCount();

      if (nextInteractionCount % 5 === 0) {
        await mutate((cacheKey) => {
          return Array.isArray(cacheKey) && cacheKey[0] === "recommendations";
        });
      }
    } finally {
      setPendingKey(null);
    }
  }

  return {
    canRecommend,
    interactionCount,
    pendingKey,
    recordInteraction,
    remainingInteractions,
  };
}
