import { AlertCircleIcon, MicIcon } from 'lucide-react';
import { KuralOrb } from '@/components/app/kural-orb';
import { KuralShell } from '@/components/app/kural-shell';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/shadcn/utils';

interface WelcomeViewProps {
  startButtonText: string;
  onStartCall: () => void;
  micError?: string | null;
}

export const WelcomeView = ({
  startButtonText,
  onStartCall,
  micError,
  ref,
}: React.ComponentProps<'div'> & WelcomeViewProps) => {
  return (
    <KuralShell ref={ref}>
      <div className="flex w-full max-w-lg flex-col items-center text-center">
        <p className="text-sm font-medium text-teal-700">Health Access Assistant</p>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight text-slate-800 md:text-4xl">
          Kural
        </h1>
        <p className="mt-3 max-w-sm text-base leading-relaxed text-slate-600 md:text-lg">
          Speak naturally. Get accessible health guidance.
        </p>

        <div className="mt-10">
          <KuralOrb state="ready" />
        </div>

        <div className="mt-8 w-full max-w-xs space-y-4">
          {micError ? (
            <div
              role="alert"
              className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-left shadow-sm"
            >
              <div className="flex gap-3">
                <AlertCircleIcon
                  className="mt-0.5 size-5 shrink-0 text-amber-600"
                  aria-hidden="true"
                />
                <div>
                  <p className="font-semibold text-amber-900">Microphone access is needed</p>
                  <p className="mt-1 text-sm leading-relaxed text-amber-800">{micError}</p>
                  <p className="mt-2 text-sm leading-relaxed text-amber-700">
                    In your browser, click the lock or site-settings icon in the address bar, allow
                    microphone access, then try again.
                  </p>
                </div>
              </div>
              <Button
                size="lg"
                onClick={onStartCall}
                className="mt-4 w-full rounded-full bg-teal-600 text-white hover:bg-teal-700 focus-visible:ring-teal-500/40"
              >
                Try Again
              </Button>
            </div>
          ) : (
            <Button
              size="lg"
              onClick={onStartCall}
              className={cn(
                'min-h-14 w-full rounded-full bg-teal-600 text-base font-semibold text-white',
                'shadow-[0_4px_16px_rgba(13,148,136,0.3)] hover:bg-teal-700',
                'focus-visible:ring-teal-500/40'
              )}
              aria-label="Start conversation with Kural"
            >
              <MicIcon className="size-5" aria-hidden="true" />
              {startButtonText}
            </Button>
          )}
        </div>

        <p className="mt-8 max-w-sm text-xs leading-relaxed text-slate-400">
          Kural provides general health guidance and does not replace professional medical advice.
          Always consult a qualified healthcare provider for medical concerns.
        </p>
      </div>
    </KuralShell>
  );
};
