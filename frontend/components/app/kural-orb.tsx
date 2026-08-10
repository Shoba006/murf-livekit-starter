'use client';

import { cn } from '@/lib/shadcn/utils';

export type KuralVisualState =
  | 'ready'
  | 'connecting'
  | 'listening'
  | 'speaking'
  | 'ended';

interface KuralOrbProps {
  state: KuralVisualState;
  className?: string;
  children?: React.ReactNode;
}

function ConnectingRing() {
  return (
    <>
      <div
        className="absolute inset-0 animate-spin rounded-full border-2 border-transparent border-t-teal-500 border-r-teal-300"
        style={{ animationDuration: '2s' }}
        aria-hidden="true"
      />
      <div
        className="absolute inset-2 animate-pulse rounded-full bg-teal-100"
        aria-hidden="true"
      />
    </>
  );
}

function ListeningPulse() {
  return (
    <>
      <div
        className="absolute inset-0 animate-ping rounded-full bg-teal-400/20"
        style={{ animationDuration: '2s' }}
        aria-hidden="true"
      />
      <div
        className="absolute inset-3 animate-pulse rounded-full bg-teal-100/80"
        style={{ animationDuration: '1.5s' }}
        aria-hidden="true"
      />
    </>
  );
}

function SpeakingWave() {
  return (
    <div
      className="absolute inset-x-4 bottom-4 flex items-end justify-center gap-1"
      aria-hidden="true"
    >
      {[0, 1, 2, 3, 4].map((i) => (
        <div
          key={i}
          className="w-1.5 rounded-full bg-teal-500"
          style={{
            height: `${12 + (i % 3) * 8}px`,
            animation: `kural-wave 0.8s ease-in-out infinite`,
            animationDelay: `${i * 0.12}s`,
          }}
        />
      ))}
    </div>
  );
}

export function KuralOrb({ state, className, children }: KuralOrbProps) {
  const isActive = state === 'listening' || state === 'speaking';
  const isConnecting = state === 'connecting';

  return (
    <div
      className={cn('relative mx-auto', className)}
      role="img"
      aria-label={
        state === 'ready'
          ? 'Kural is ready'
          : state === 'connecting'
            ? 'Kural is connecting'
            : state === 'listening'
              ? 'Kural is listening'
              : state === 'speaking'
                ? 'Kural is speaking'
                : 'Conversation ended'
      }
    >
      <div
        className={cn(
          'relative flex size-36 items-center justify-center rounded-full md:size-44',
          state === 'ready' && 'bg-teal-50 shadow-[0_4px_24px_rgba(13,148,136,0.12)]',
          state === 'connecting' && 'bg-teal-50',
          state === 'listening' && 'bg-teal-50 shadow-[0_4px_32px_rgba(13,148,136,0.18)]',
          state === 'speaking' && 'bg-sky-50 shadow-[0_4px_32px_rgba(14,165,233,0.18)]',
          state === 'ended' && 'bg-slate-100 shadow-sm'
        )}
      >
        {isConnecting && <ConnectingRing />}
        {state === 'listening' && <ListeningPulse />}
        {state === 'speaking' && (
          <>
            <div
              className="absolute inset-0 animate-pulse rounded-full bg-sky-100/60"
              style={{ animationDuration: '1.2s' }}
              aria-hidden="true"
            />
            <SpeakingWave />
          </>
        )}

        <div
          className={cn(
            'relative z-10 flex size-20 items-center justify-center rounded-full md:size-24',
            state === 'ready' && 'bg-gradient-to-br from-teal-500 to-teal-600',
            state === 'connecting' && 'bg-gradient-to-br from-teal-400 to-teal-600',
            state === 'listening' && 'bg-gradient-to-br from-teal-500 to-teal-600',
            state === 'speaking' && 'bg-gradient-to-br from-sky-500 to-teal-500',
            state === 'ended' && 'bg-gradient-to-br from-slate-300 to-slate-400'
          )}
        >
          {children ?? (
            <svg
              viewBox="0 0 24 24"
              fill="none"
              className="size-8 text-white md:size-10"
              aria-hidden="true"
            >
              <path
                d="M12 14a3 3 0 0 0 3-3V5a3 3 0 1 0-6 0v6a3 3 0 0 0 3 3Z"
                fill="currentColor"
              />
              <path
                d="M19 11a1 1 0 1 0-2 0 5 5 0 0 1-10 0 1 1 0 1 0-2 0 7 7 0 0 0 6 6.92V21H9a1 1 0 1 0 0 2h6a1 1 0 1 0 0-2h-2v-3.08A7 7 0 0 0 19 11Z"
                fill="currentColor"
              />
            </svg>
          )}
        </div>
      </div>

      {isActive && (
        <div className="mt-4 flex justify-center gap-1.5" aria-hidden="true">
          {[0, 1, 2, 3, 4, 5, 6].map((i) => (
            <div
              key={i}
              className={cn(
                'w-1 rounded-full',
                state === 'listening' ? 'bg-teal-400' : 'bg-sky-400'
              )}
              style={{
                height: `${8 + Math.sin(i * 0.8) * 6 + 6}px`,
                animation: `kural-wave 1s ease-in-out infinite`,
                animationDelay: `${i * 0.1}s`,
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
}
