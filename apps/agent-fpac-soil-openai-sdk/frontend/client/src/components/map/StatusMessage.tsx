import type { HTMLAttributes, ReactNode } from 'react';
import { CircleAlert, CircleCheck, Info, TriangleAlert } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

export type StatusVariant = 'info' | 'success' | 'warning' | 'error';

const VARIANTS: Record<StatusVariant, { box: string; icon: string; Icon: LucideIcon }> = {
  info: { box: 'border-border bg-muted', icon: 'text-muted-foreground', Icon: Info },
  success: {
    box: 'border-[var(--border-success)] bg-[var(--background-success)]',
    icon: 'text-[var(--success)]',
    Icon: CircleCheck,
  },
  warning: {
    box: 'border-[var(--border-warning)] bg-[var(--background-warning)]',
    icon: 'text-[var(--warning)]',
    Icon: TriangleAlert,
  },
  error: {
    box: 'border-[var(--border-danger)] bg-[var(--background-danger)]',
    icon: 'text-destructive',
    Icon: CircleAlert,
  },
};

// Message bar for map status: an icon plus wrapping text (never truncated). The
// variant is also carried by the icon shape, not colour alone. Errors are alerts.
export function StatusMessage({
  variant,
  children,
  className,
  ...props
}: { variant: StatusVariant; children: ReactNode } & HTMLAttributes<HTMLDivElement>) {
  const { box, icon, Icon } = VARIANTS[variant];
  return (
    <div
      role={variant === 'error' ? 'alert' : undefined}
      {...props}
      className={cn(
        'flex items-start gap-2 rounded-md border px-2 py-1.5 text-foreground text-sm',
        box,
        className,
      )}
    >
      <Icon aria-hidden="true" className={cn('mt-0.5 size-4 shrink-0', icon)} />
      <div className="flex min-w-0 flex-1 flex-col gap-1 break-words">{children}</div>
    </div>
  );
}
