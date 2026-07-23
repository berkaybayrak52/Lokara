import type { ButtonHTMLAttributes, ReactNode } from 'react';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** One primary (filled green) action per screen; everything else is secondary. */
  variant?: 'primary' | 'secondary';
  children: ReactNode;
}

const BASE =
  'inline-flex items-center justify-center rounded-lg px-4 py-2 font-sans font-semibold ' +
  'transition-colors duration-150 ease-out ' +
  'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-green ' +
  'disabled:cursor-not-allowed disabled:opacity-50 motion-reduce:transition-none';

const VARIANTS: Record<NonNullable<ButtonProps['variant']>, string> = {
  primary: 'bg-green text-white hover:bg-forest active:bg-forest',
  secondary: 'border border-slate text-ink hover:bg-mint active:bg-mint',
};

export function Button({ variant = 'primary', className, children, ...rest }: ButtonProps) {
  const classes = [BASE, VARIANTS[variant], className].filter(Boolean).join(' ');
  return (
    <button className={classes} {...rest}>
      {children}
    </button>
  );
}
