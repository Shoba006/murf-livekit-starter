'use client';

import { useEffect, useState } from 'react';
import { motion } from 'motion/react';
import { useSessionContext } from '@livekit/components-react';
import type { AppConfig } from '@/app-config';
import { KuralOrb } from '@/components/app/kural-orb';
import { KuralSessionView } from '@/components/app/kural-session-view';
import { KuralShell } from '@/components/app/kural-shell';
import { WelcomeView } from '@/components/app/welcome-view';
import { Button } from '@/components/ui/button';

const MotionWelcomeView = motion.create(WelcomeView);
const MotionSessionView = motion.create(KuralSessionView);

const VIEW_MOTION_PROPS = {
  variants: {
    visible: { opacity: 1 },
    hidden: { opacity: 0 },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
  transition: {
    duration: 0.35,
    ease: 'linear',
  },
};

interface ViewControllerProps {
  appConfig: AppConfig;
}

export function ViewController({ appConfig }: ViewControllerProps) {
  const { isConnected, start } = useSessionContext();

  const [isConnecting, setIsConnecting] = useState(false);
  const [hasStarted, setHasStarted] = useState(false);
  const [hasEnded, setHasEnded] = useState(false);
  const [micError, setMicError] = useState<string | null>(null);

  useEffect(() => {
    if (isConnected) {
      setIsConnecting(false);
      setHasEnded(false);
    } else if (hasStarted && !isConnecting) {
      setHasEnded(true);
    }
  }, [isConnected, hasStarted, isConnecting]);

  const handleStartCall = async () => {
    setMicError(null);
    setHasEnded(false);
    setIsConnecting(true);

    try {
      setHasStarted(true);
      await start();
    } catch (error) {
      console.error('Unable to start Kural:', error);
      setIsConnecting(false);
      setHasStarted(false);

      if (error instanceof DOMException) {
        if (
          error.name === 'NotAllowedError' ||
          error.name === 'PermissionDeniedError'
        ) {
          setMicError(
            'Please allow microphone access in your browser settings so Kural can hear you.'
          );
        } else if (error.name === 'NotFoundError') {
          setMicError(
            'No microphone was found. Please connect a microphone and try again.'
          );
        } else {
          setMicError(
            'Kural could not connect. Please check your microphone and internet connection, then try again.'
          );
        }
      } else {
        const message =
          error instanceof Error ? error.message.toLowerCase() : '';

        if (
          message.includes('permission') ||
          message.includes('microphone') ||
          message.includes('notallowed')
        ) {
          setMicError(
            'Please allow microphone access in your browser settings so Kural can hear you.'
          );
        } else {
          setMicError(
            'Kural could not connect. Please check your microphone and internet connection, then try again.'
          );
        }
      }
    }
  };

  const handleRestart = () => {
    setHasEnded(false);
    setHasStarted(false);
    setMicError(null);
  };

  if (isConnected) {
    return (
      <MotionSessionView
        key="session-view"
        {...VIEW_MOTION_PROPS}
        className="fixed inset-0"
      />
    );
  }

  if (isConnecting) {
    return (
      <KuralShell>
        <div className="flex w-full max-w-lg flex-col items-center text-center">
          <p className="text-sm font-medium text-teal-700">Health Access Assistant</p>
          <h1 className="mt-1 text-2xl font-semibold text-slate-800 md:text-3xl">Kural</h1>

          <div className="mt-10">
            <KuralOrb state="connecting" />
          </div>

          <div className="mt-8 space-y-2" role="status" aria-live="polite">
            <p className="text-xl font-semibold text-slate-800">Connecting…</p>
            <p className="max-w-sm text-sm leading-relaxed text-slate-500">
              Please wait while Kural joins the conversation.
            </p>
          </div>

          <div
            className="mt-6 flex gap-1.5"
            aria-hidden="true"
          >
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="size-2 rounded-full bg-teal-400"
                style={{
                  animation: 'kural-wave 1.2s ease-in-out infinite',
                  animationDelay: `${i * 0.2}s`,
                }}
              />
            ))}
          </div>
        </div>
      </KuralShell>
    );
  }

  if (hasEnded) {
    return (
      <KuralShell>
        <div className="flex w-full max-w-lg flex-col items-center text-center">
          <p className="text-sm font-medium text-teal-700">Health Access Assistant</p>
          <h1 className="mt-1 text-2xl font-semibold text-slate-800 md:text-3xl">Kural</h1>

          <div className="mt-10">
            <KuralOrb state="ended" />
          </div>

          <div className="mt-8 space-y-2" role="status">
            <p className="text-xl font-semibold text-slate-800">Conversation ended</p>
            <p className="max-w-sm text-sm leading-relaxed text-slate-500">
              Thank you for speaking with Kural. Start a new conversation whenever you are ready.
            </p>
          </div>

          <Button
            size="lg"
            onClick={handleRestart}
            className="mt-8 min-h-14 w-full max-w-xs rounded-full bg-teal-600 text-base font-semibold text-white shadow-[0_4px_16px_rgba(13,148,136,0.3)] hover:bg-teal-700 focus-visible:ring-teal-500/40"
            aria-label="Start a new conversation"
          >
            Start Again
          </Button>
        </div>
      </KuralShell>
    );
  }

  return (
    <MotionWelcomeView
      key="welcome"
      {...VIEW_MOTION_PROPS}
      startButtonText={appConfig.startButtonText}
      onStartCall={handleStartCall}
      micError={micError}
    />
  );
}
