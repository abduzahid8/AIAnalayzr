import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type PropsWithChildren,
} from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';

import { vigilApi } from '@/src/lib/api';
import type {
  AnalysisRequest,
  AnalysisResponse,
  ChatMessage,
} from '@/src/types/vigil';

const SESSION_KEY = 'vigil_session_id';

type VigilContextValue = {
  apiBaseUrl: string;
  analysis: AnalysisResponse | null;
  sessionId: string | null;
  chatMessages: ChatMessage[];
  isAnalyzing: boolean;
  isSendingChat: boolean;
  lastError: string | null;
  runAnalysis: (payload: AnalysisRequest) => Promise<void>;
  sendChat: (message: string) => Promise<void>;
  clearError: () => void;
  resetAnalysis: () => void;
};

const VigilContext = createContext<VigilContextValue | undefined>(undefined);

function createMessage(role: ChatMessage['role'], content: string, meta?: string): ChatMessage {
  return {
    id: `${role}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    role,
    content,
    meta,
  };
}

function getErrorMessage(error: unknown) {
  if (error instanceof Error) {
    return error.message;
  }

  return 'Something went wrong while contacting the Vigil API.';
}

function getDefaultAssistantMessage(company?: string) {
  return createMessage(
    'assistant',
    company
      ? `Analysis ready for ${company}. Ask what to do next, whether to launch, hire, or hedge risk.`
      : 'Run an analysis first, then use the advisor tab to ask follow-up strategy questions.',
  );
}

export function VigilProvider({ children }: PropsWithChildren) {
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    getDefaultAssistantMessage(),
  ]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isSendingChat, setIsSendingChat] = useState(false);
  const [lastError, setLastError] = useState<string | null>(null);

  useEffect(() => {
    AsyncStorage.getItem(SESSION_KEY).then((stored) => {
      if (stored && !sessionId) setSessionId(stored);
    });
  }, []);

  const clearError = useCallback(() => {
    setLastError(null);
  }, []);

  const resetAnalysis = useCallback(() => {
    setAnalysis(null);
    setSessionId(null);
    setLastError(null);
    setChatMessages([getDefaultAssistantMessage()]);
    AsyncStorage.removeItem(SESSION_KEY);
  }, []);

  const runAnalysis = useCallback(async (payload: AnalysisRequest) => {
    setIsAnalyzing(true);
    setLastError(null);

    try {
      const result = await vigilApi.analyse(payload);
      setAnalysis(result);
      setSessionId(result.session_id);
      AsyncStorage.setItem(SESSION_KEY, result.session_id);
      setChatMessages([
        getDefaultAssistantMessage(result.company),
        createMessage(
          'assistant',
          result.executive_headline || result.executive_summary,
          `Risk ${Math.round(result.risk_score)} (${result.risk_tier})`,
        ),
      ]);
    } catch (error) {
      setLastError(getErrorMessage(error));
    } finally {
      setIsAnalyzing(false);
    }
  }, []);

  const sendChat = useCallback(
    async (message: string) => {
      if (!sessionId) {
        setLastError('Run an analysis before starting the advisor chat.');
        return;
      }

      setLastError(null);
      setIsSendingChat(true);
      setChatMessages((current) => [...current, createMessage('user', message)]);

      try {
        const reply = await vigilApi.chat(sessionId, message);
        setChatMessages((current) => [
          ...current,
          createMessage(
            'assistant',
            reply.reply,
            reply.risk_score != null && reply.risk_tier
              ? `Risk ${Math.round(reply.risk_score)} (${reply.risk_tier})`
              : undefined,
          ),
        ]);
      } catch (error) {
        const messageText = getErrorMessage(error);
        setLastError(messageText);
        setChatMessages((current) => [
          ...current,
          createMessage('assistant', `I could not reach the advisor right now. ${messageText}`),
        ]);
      } finally {
        setIsSendingChat(false);
      }
    },
    [sessionId],
  );

  const value = useMemo<VigilContextValue>(
    () => ({
      apiBaseUrl: vigilApi.apiBaseUrl,
      analysis,
      sessionId,
      chatMessages,
      isAnalyzing,
      isSendingChat,
      lastError,
      runAnalysis,
      sendChat,
      clearError,
      resetAnalysis,
    }),
    [
      analysis,
      chatMessages,
      clearError,
      isAnalyzing,
      isSendingChat,
      lastError,
      resetAnalysis,
      runAnalysis,
      sendChat,
      sessionId,
    ],
  );

  return <VigilContext.Provider value={value}>{children}</VigilContext.Provider>;
}

export function useVigil() {
  const context = useContext(VigilContext);

  if (!context) {
    throw new Error('useVigil must be used inside VigilProvider.');
  }

  return context;
}
