import type { InputHTMLAttributes } from "react";

type AuthFieldProps = Omit<InputHTMLAttributes<HTMLInputElement>, "id"> & {
  id: string;
  label: string;
  hint?: string;
  error?: string;
  testId?: string;
};

export function AuthField({
  id,
  label,
  hint,
  error,
  testId,
  className = "",
  ...inputProps
}: AuthFieldProps) {
  const message = error ?? hint;
  const messageId = message ? `${id}-message` : undefined;

  return (
    <div>
      <label
        className="mb-2 block text-sm font-black tracking-[0.12em] uppercase"
        htmlFor={id}
      >
        {label}
      </label>
      <input
        {...inputProps}
        aria-describedby={messageId}
        aria-invalid={Boolean(error)}
        className={`h-12 w-full border-black bg-white px-3 text-base font-bold text-black outline-none transition-none focus-visible:[outline:4px_solid_#000] focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:border-dashed disabled:bg-white disabled:text-black disabled:opacity-100 ${error ? "border-4" : "border-2"} ${className}`}
        data-auth-control
        data-testid={testId}
        id={id}
      />
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
