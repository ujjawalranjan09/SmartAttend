import * as React from "react";
import { cn } from "@/lib/utils";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

const baseInputClasses =
  "flex w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm " +
  "placeholder:text-[var(--muted-foreground)] " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] focus-visible:border-transparent " +
  "disabled:cursor-not-allowed disabled:opacity-50 transition-colors";

/**
 * Input. Pass `leftIcon`/`rightIcon` (typically a lucide icon) to render an
 * icon-affixed field with correct padding, e.g. <Input leftIcon={<Search/>} />.
 */
const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, leftIcon, rightIcon, ...props }, ref) => {
    if (!leftIcon && !rightIcon) {
      return (
        <input
          type={type}
          className={cn(baseInputClasses, "h-10", className)}
          ref={ref}
          {...props}
        />
      );
    }
    return (
      <div className="relative flex h-10 w-full items-center">
        {leftIcon && (
          <span className="pointer-events-none absolute left-3 flex items-center justify-center text-[var(--muted-foreground)] [&_svg]:size-4">
            {leftIcon}
          </span>
        )}
        <input
          type={type}
          className={cn(
            baseInputClasses,
            "h-10",
            leftIcon && "pl-9",
            rightIcon && "pr-9",
            className
          )}
          ref={ref}
          {...props}
        />
        {rightIcon && (
          <span className="absolute right-3 flex items-center justify-center text-[var(--muted-foreground)] [&_svg]:size-4">
            {rightIcon}
          </span>
        )}
      </div>
    );
  }
);
Input.displayName = "Input";

export { Input };
