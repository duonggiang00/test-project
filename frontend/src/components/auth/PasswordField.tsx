import type { ChangeEventHandler, FocusEventHandler } from "react";

type PasswordFieldProps = {
  id: string;
  label: string;
  value: string;
  showPassword: boolean;
  onChange: ChangeEventHandler<HTMLInputElement>;
  onBlur?: FocusEventHandler<HTMLInputElement>;
  onToggle: () => void;
  autoComplete: string;
  hint?: string;
  error?: string;
  disabled?: boolean;
  testId?: string;
};

export function PasswordField({
  id,
  label,
  value,
  showPassword,
  onChange,
  onBlur,
  onToggle,
  autoComplete,
  hint,
  error,
  disabled = false,
  testId,
}: PasswordFieldProps) {
  const message = error ?? hint;
  const messageId = message ? `${id}-message` : undefined;
  const actionLabel = showPassword ? `Hide ${label.toLowerCase()}` : `Show ${label.toLowerCase()}`;

  return (
    <div>
      <label
        className="mb-2 block text-sm font-black tracking-[0.12em] uppercase"
        htmlFor={id}
      >
        {label}
      </label>
      <div
        className={`grid grid-cols-[minmax(0,1fr)_auto] border-black bg-white focus-within:[outline:4px_solid_#000] focus-within:outline-offset-2 ${error ? "border-4" : "border-2"}`}
      >
        <input
          aria-describedby={messageId}
          aria-invalid={Boolean(error)}
          autoComplete={autoComplete}
          className="h-12 min-w-0 border-0 bg-white px-3 text-base font-bold text-black outline-none disabled:cursor-not-allowed disabled:bg-white disabled:text-black disabled:opacity-100"
          data-auth-control
          data-testid={testId}
          disabled={disabled}
          id={id}
          name={id}
          onBlur={onBlur}
          onChange={onChange}
          required
          type={showPassword ? "text" : "password"}
          value={value}
        />
        <button
          aria-label={actionLabel}
          aria-pressed={showPassword}
          className="min-h-12 min-w-20 border-l-2 border-black bg-white px-3 text-xs font-black tracking-[0.12em] text-black uppercase outline-none hover:bg-black hover:text-white focus-visible:bg-black focus-visible:text-white disabled:cursor-not-allowed disabled:border-dashed disabled:bg-white disabled:text-black"
          disabled={disabled}
          onClick={onToggle}
          type="button"
        >
          {showPassword ? "Hide" : "Show"}
        </button>
      </div>
      {message ? (
        <p
          className="mt-2 text-sm leading-5 font-bold"
          id={messageId}
          role={error ? "alert" : undefined}
        >
          <span aria-hidden="true">{error ? "!" : "—"}</span> {message}
        </p>
      ) : null}
    </div>
  );
}
