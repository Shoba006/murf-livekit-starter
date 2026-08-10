'use client';

import { useMemo } from 'react';
import {
  type AgentState,
  useAgent,
  useSessionContext,
  useSessionMessages,
  useVoiceAssistant,
} from '@livekit/components-react';
import { PhoneOffIcon } from 'lucide-react';
import { KuralOrb, type KuralVisualState } from '@/components/app/kural-orb';
import { KuralShell } from '@/components/app/kural-shell';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/shadcn/utils';

function agentStateToVisual(state: AgentState | undefined): KuralVisualState {
  if (state === 'speaking') return 'speaking';
  if (state === 'listening' || state === 'thinking' || state === 'connecting' || state === 'initializing') {
    return 'listening';
  }
  return 'listening';
}

function getStatusMessage(state: AgentState | undefined): string {
  switch (state) {
    case 'speaking':
      return 'Kural is speaking…';
    case 'thinking':
      return 'Understanding your question…';
    case 'connecting':
    case 'initializing':
      return 'Getting ready…';
    case 'listening':
    default:
      return 'Listening to you…';
  }
}

function getStatusHint(state: AgentState | undefined): string {
  switch (state) {
    case 'speaking':
      return 'Please wait while Kural responds.';
    case 'thinking':
      return 'Kural is preparing a helpful response.';
    case 'listening':
    default:
      return 'Speak naturally — Kural will respond when you pause.';
  }
}

interface TranscriptEntry {
  role: 'user' | 'assistant';
  text: string;
}

function CompactTranscript({ messages }: { messages: TranscriptEntry[] }) {
  const recent = messages.slice(-4);
  if (recent.length === 0) return null;

  return (
    <div
      className="mt-8 w-full max-w-md rounded-2xl border border-slate-200 bg-white/80 p-4 shadow-sm backdrop-blur-sm"
      aria-label="Recent conversation"
    >
      <p className="mb-3 text-xs font-semibold tracking-wide text-slate-500 uppercase">
        Conversation
      </p>
      <div className="space-y-3">
        {recent.map((entry, i) => (
          <div key={i} className="text-left">
            <p className="text-xs font-semibold text-teal-700">
              {entry.role === 'user' ? 'You' : 'Kural'}
            </p>
            <p className="mt-0.5 text-sm leading-relaxed text-slate-700">{entry.text}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

interface KuralSessionViewProps {
  className?: string;
}

export function KuralSessionView({ className }: KuralSessionViewProps) {
  const session = useSessionContext();
  const { messages } = useSessionMessages(session);
  const { state: agentState } = useAgent();
  const { state: voiceState } = useVoiceAssistant();

  const effectiveState = voiceState ?? agentState;
  const visualState = agentStateToVisual(effectiveState);

  const transcriptEntries = useMemo<TranscriptEntry[]>(() => {
    return messages
      .filter((m) => m.message.trim().length > 0)
      .map((m) => ({
        role: m.from?.isLocal ? ('user' as const) : ('assistant' as const),
        text: m.message,
      }));
  }, [messages]);

  const handleEnd = () => {
    session.end();
  };

  return (
    <KuralShell className={className}>
      <div className="flex w-full max-w-lg flex-col items-center text-center">
        <p className="text-sm font-medium text-teal-700">Health Access Assistant</p>
        <h1 className="mt-1 text-2xl font-semibold text-slate-800 md:text-3xl">Kural</h1>

        <div className="mt-8">
          <KuralOrb state={visualState} />
        </div>

        <div className="mt-6 space-y-2" role="status" aria-live="polite">
          <p
            className={cn(
              'text-xl font-semibold',
              visualState === 'speaking' ? 'text-sky-700' : 'text-teal-800'
            )}
          >
            {getStatusMessage(effectiveState)}
          </p>
          <p className="max-w-sm text-sm leading-relaxed text-slate-500">
            {getStatusHint(effectiveState)}
          </p>
        </div>

        <CompactTranscript messages={transcriptEntries} />

        <Button
          variant="outline"
          size="lg"
          onClick={handleEnd}
          className="mt-8 min-h-12 w-full max-w-xs rounded-full border-slate-200 bg-white text-slate-700 shadow-sm hover:bg-slate-50 focus-visible:ring-teal-500/40"
          aria-label="End conversation"
        >
          <PhoneOffIcon className="size-4" aria-hidden="true" />
          End Conversation
        </Button>

        <p className="mt-6 max-w-sm text-xs leading-relaxed text-slate-400">
          Kural provides general health guidance and does not replace professional medical advice.
        </p>
      </div>
    </KuralShell>
  );
}
