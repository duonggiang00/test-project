type AuthNoticeProps = {
  kind: "error" | "success" | "info";
  title: string;
  children: React.ReactNode;
};

const SYMBOLS = {
  error: "!",
  success: "✓",
  info: "→",
} as const;

export function AuthNotice({ kind, title, children }: AuthNoticeProps) {
  return (
    <div
      className={`grid grid-cols-[auto_1fr] gap-3 bg-white p-4 text-black ${kind === "error" ? "border-4" : "border-2"} border-black`}
      role={kind === "error" ? "alert" : "status"}
    >
      <span
        aria-hidden="true"
        className="flex size-7 items-center justify-center border-2 border-black bg-black text-sm font-black text-white"
      >
        {SYMBOLS[kind]}
      </span>
      <div className="min-w-0 break-words">
        <p className="text-sm font-black tracking-[0.1em] uppercase">{title}</p>
        <div className="mt-1 text-sm leading-5 font-medium">{children}</div>
      </div>
    </div>
  );
}
