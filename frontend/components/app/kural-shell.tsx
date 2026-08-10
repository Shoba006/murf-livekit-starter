import { forwardRef } from 'react';
import { cn } from '@/lib/shadcn/utils';

interface KuralShellProps {
  children: React.ReactNode;
  className?: string;
}

export function KuralHeader() {
  return (
    <header className="flex w-full items-center justify-between px-5 pt-6 pb-2 md:px-8 md:pt-8">
      <div className="flex items-center gap-3">
        <div
          className="flex size-10 items-center justify-center rounded-full bg-teal-600 text-lg font-bold text-white shadow-sm"
          aria-hidden="true"
        >
          K
        </div>
        <div>
          <p className="text-lg font-semibold tracking-tight text-slate-800">Kural</p>
          <p className="text-xs font-medium text-teal-700">Health Access</p>
        </div>
      </div>
      <span className="hidden rounded-full border border-teal-200 bg-teal-50 px-3 py-1 text-xs font-medium text-teal-800 sm:inline-block">
        Voice Assistant
      </span>
    </header>
  );
}

export const KuralShell = forwardRef<HTMLDivElement, KuralShellProps>(
  function KuralShell({ children, className }, ref) {
    return (
      <div
        ref={ref}
        className={cn(
          'flex min-h-svh w-full flex-col bg-[#F8FAFB] text-slate-800',
          className
        )}
      >
        <KuralHeader />
        <main className="flex flex-1 flex-col items-center justify-center px-5 pb-10 md:px-8">
          {children}
        </main>
      </div>
    );
  }
);
