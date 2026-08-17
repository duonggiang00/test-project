type PlayStudyBrandProps = {
  tone?: "light" | "dark";
  size?: "small" | "medium";
  showWordmark?: boolean;
  className?: string;
};

const sizeClasses = {
  small: {
    container: "gap-3",
    mark: "h-10 w-10 border-2 text-xl",
    wordmark: "text-lg tracking-[0.14em]",
  },
  medium: {
    container: "gap-4",
    mark: "h-12 w-12 border-4 text-2xl",
    wordmark: "text-2xl tracking-[0.12em]",
  },
} as const;

export function PlayStudyBrand({
  tone = "light",
  size = "medium",
  showWordmark = true,
  className = "",
}: PlayStudyBrandProps) {
  const classes = sizeClasses[size];
  const markClasses =
    tone === "dark"
      ? "border-white bg-white text-black"
      : "border-black bg-black text-white";
  const wordmarkClasses = tone === "dark" ? "text-white" : "text-black";

  return (
    <span
      className={`inline-flex min-w-0 items-center ${classes.container} ${className}`}
      data-testid="playstudy-brand"
    >
      <span
        aria-hidden="true"
        className={`flex shrink-0 items-center justify-center rounded-none font-mono font-black uppercase ${classes.mark} ${markClasses}`}
        data-testid="playstudy-mark"
      >
        <svg
          className="h-[70%] w-[70%]"
          viewBox="0 0 64 64"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M16 12H40V20H48V36H40V44H24V52H16V12ZM24 20V36H40V20H24Z"
            fill="currentColor"
            fillRule="evenodd"
          />
        </svg>
      </span>
      {showWordmark ? (
        <span
          className={`truncate font-mono font-black uppercase ${classes.wordmark} ${wordmarkClasses}`}
        >
          PlayStudy
        </span>
      ) : (
        <span className="sr-only">PlayStudy</span>
      )}
    </span>
  );
}
