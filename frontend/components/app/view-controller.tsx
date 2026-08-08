'use client';

import { useEffect, useState } from 'react';
import { motion } from 'motion/react';
import { useSessionContext } from '@livekit/components-react';
import type { AppConfig } from '@/app-config';
import { AgentSessionView_01 } from '@/components/agents-ui/blocks/agent-session-view-01';
import { WelcomeView } from '@/components/app/welcome-view';

const MotionWelcomeView = motion.create(WelcomeView);
const MotionSessionView = motion.create(AgentSessionView_01);

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

  // Detect connection/disconnection
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
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error(
          'Microphone access is not supported by this browser.'
        );
      }

      // Request microphone permission before connecting.
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: true,
      });

      // We only need this request to verify permission.
      // LiveKit will create/use the actual microphone track.
      stream.getTracks().forEach((track) => track.stop());

      setHasStarted(true);

      await start();
    } catch (error) {
      console.error('Unable to start Kural:', error);
      setIsConnecting(false);

      if (
        error instanceof DOMException &&
        (error.name === 'NotAllowedError' ||
          error.name === 'PermissionDeniedError')
      ) {
        setMicError(
          'Microphone access was blocked. Please allow microphone access in your browser settings and try again.'
        );
      } else if (
        error instanceof DOMException &&
        error.name === 'NotFoundError'
      ) {
        setMicError(
          'No microphone was found. Please connect a microphone and try again.'
        );
      } else {
        setMicError(
          'Kural could not connect. Please check your microphone and internet connection, then try again.'
        );
      }
    }
  };

  const handleRestart = () => {
    setHasEnded(false);
    setHasStarted(false);
    setMicError(null);
  };

  // ─────────────────────────────────────────────
  // ACTIVE CALL
  // ─────────────────────────────────────────────

  if (isConnected) {
    return (
      <MotionSessionView
        key="session-view"
        {...VIEW_MOTION_PROPS}
        supportsChatInput={appConfig.supportsChatInput}
        supportsVideoInput={appConfig.supportsVideoInput}
        supportsScreenShare={appConfig.supportsScreenShare}
        isPreConnectBufferEnabled={appConfig.isPreConnectBufferEnabled}
        audioVisualizerType={appConfig.audioVisualizerType}
        audioVisualizerColor={appConfig.audioVisualizerColor}
        audioVisualizerColorShift={appConfig.audioVisualizerColorShift}
        audioVisualizerBarCount={appConfig.audioVisualizerBarCount}
        audioVisualizerGridRowCount={appConfig.audioVisualizerGridRowCount}
        audioVisualizerGridColumnCount={appConfig.audioVisualizerGridColumnCount}
        audioVisualizerRadialBarCount={appConfig.audioVisualizerRadialBarCount}
        audioVisualizerRadialRadius={appConfig.audioVisualizerRadialRadius}
        audioVisualizerWaveLineWidth={
          appConfig.audioVisualizerWaveLineWidth
        }
        className="fixed inset-0"
      />
    );
  }

  // ─────────────────────────────────────────────
  // CONNECTING
  // ─────────────────────────────────────────────

  if (isConnecting) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#fffaf5] px-6">
        <div className="text-center">
          <div className="mx-auto mb-8 flex h-24 w-24 items-center justify-center rounded-full bg-[#ff7a45]/10">
            <div className="h-12 w-12 animate-pulse rounded-full bg-[#ff7a45]" />
          </div>

          <p className="mb-2 text-sm font-semibold tracking-[0.2em] text-[#ff7a45] uppercase">
            Kural
          </p>

          <h2 className="text-2xl font-semibold text-[#252525]">
            Connecting...
          </h2>

          <p className="mt-3 text-sm text-[#777]">
            Please wait while Kural joins the conversation.
          </p>
        </div>
      </div>
    );
  }

  // ─────────────────────────────────────────────
  // CALL ENDED
  // ─────────────────────────────────────────────

  if (hasEnded) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#fffaf5] px-6">
        <div className="w-full max-w-md text-center">
          <div className="mx-auto mb-6 flex h-24 w-24 items-center justify-center rounded-full bg-[#ff7a45]/10">
            <span className="text-4xl text-[#ff7a45]">✓</span>
          </div>

          <p className="mb-2 text-sm font-semibold tracking-[0.2em] text-[#ff7a45] uppercase">
            Kural
          </p>

          <h2 className="text-3xl font-semibold text-[#252525]">
            Conversation ended
          </h2>

          <p className="mt-3 text-sm leading-6 text-[#777]">
            Thank you for speaking with Kural. Start a new conversation
            whenever you are ready.
          </p>

          <button
            onClick={handleRestart}
            className="mt-8 w-full rounded-full bg-[#ff7a45] px-8 py-4 text-sm font-bold tracking-wide text-white transition hover:bg-[#e96835]"
          >
            Start Again
          </button>
        </div>
      </div>
    );
  }

  // ─────────────────────────────────────────────
  // READY
  // ─────────────────────────────────────────────

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