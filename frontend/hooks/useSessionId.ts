"use client";

import { useEffect, useState } from "react";
import { v4 as uuidv4 } from "uuid";

const SESSION_KEY = "freedom_rt_session_id";

export function useSessionId(): string | null {
  const [sessionId, setSessionId] = useState<string | null>(null);

  useEffect(() => {
    const existingSession = window.localStorage.getItem(SESSION_KEY);
    if (existingSession) {
      queueMicrotask(() => setSessionId(existingSession));
      return;
    }

    const nextSession = uuidv4();
    window.localStorage.setItem(SESSION_KEY, nextSession);
    queueMicrotask(() => setSessionId(nextSession));
  }, []);

  return sessionId;
}
