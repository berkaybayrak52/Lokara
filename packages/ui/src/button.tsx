import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import type { ButtonHTMLAttributes } from 'react';

import { cn } from './lib/cn';

/**
 * shadcn-style Button themed to the brand tokens (docs/05) — never shadcn's
 * default palette. One `default` (filled Lokara-Grün) action per screen;
 * everything else is secondary/outline/ghost/link. No destructive variant yet:
 * the brand board defines no semantic red (TODO(M3): status colors).
 */
const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg font-sans ' +
    'font-semibold transition-colors duration-150 ease-out ' +
    'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring ' +
    'disabled:pointer-events-none disabled:opacity-50 motion-reduce:transition-none ' +
    "[&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground hover:bg-forest active:bg-forest',
        secondary: 'bg-secondary text-secondary-foreground hover:bg-mint/70 active:bg-mint/70',
        outline: 'border border-slate bg-transparent text-ink hover:bg-mint active:bg-mint',
        ghost: 'text-ink hover:bg-mint active:bg-mint',
        link: 'text-green underline-offset-4 hover:underline',
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'h-9 px-3',
        lg: 'h-11 px-6',
        icon: 'size-10',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
);

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  /** Render the child element (e.g. a Link) with button styling instead. */
  asChild?: boolean;
}

export function Button({ className, variant, size, asChild = false, ...props }: ButtonProps) {
  const Comp = asChild ? Slot : 'button';
  return <Comp className={cn(buttonVariants({ variant, size, className }))} {...props} />;
}

export { buttonVariants };
