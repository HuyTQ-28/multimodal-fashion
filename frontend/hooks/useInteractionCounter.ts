"use client";

import { useEffect, useState } from "react";

const INTERACTION_COUNT_KEY = "freedom_rt_interaction_count";
const INTERACTION_COUNT_EVENT = "freedom_rt_interaction_count_changed";
export const RECOMMENDATION_THRESHOLD = 5;

export function useInteractionCounter() {
  const [interactionCount, setInteractionCount] = useState(0);

  useEffect(() => {
    const storedCount = Number(window.localStorage.getItem(INTERACTION_COUNT_KEY) ?? "0");
    queueMicrotask(() => setInteractionCount(Number.isFinite(storedCount) ? storedCount : 0));

    function handleCountChanged() {
      const nextCount = Number(window.localStorage.getItem(INTERACTION_COUNT_KEY) ?? "0");
      setInteractionCount(Number.isFinite(nextCount) ? nextCount : 0);
    }

    window.addEventListener(INTERACTION_COUNT_EVENT, handleCountChanged);
    window.addEventListener("storage", handleCountChanged);
    return () => {
      window.removeEventListener(INTERACTION_COUNT_EVENT, handleCountChanged);
      window.removeEventListener("storage", handleCountChanged);
    };
  }, []);

  function incrementInteractionCount(): number {
    const currentCount = Number(window.localStorage.getItem(INTERACTION_COUNT_KEY) ?? "0");
    const nextCount = (Number.isFinite(currentCount) ? currentCount : 0) + 1;
    window.localStorage.setItem(INTERACTION_COUNT_KEY, String(nextCount));
    window.dispatchEvent(new Event(INTERACTION_COUNT_EVENT));
    setInteractionCount(nextCount);
    return nextCount;
  }

  return {
    interactionCount,
    incrementInteractionCount,
    canRecommend: interactionCount >= RECOMMENDATION_THRESHOLD,
    remainingInteractions: Math.max(RECOMMENDATION_THRESHOLD - interactionCount, 0),
  };
}
