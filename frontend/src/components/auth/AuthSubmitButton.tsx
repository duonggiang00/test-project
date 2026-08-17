type AuthSubmitButtonProps = {
  isLoading: boolean;
  idleLabel: string;
  loadingLabel: string;
  testId?: string;
};

export function AuthSubmitButton({
  isLoading,
  idleLabel,
  loadingLabel,
  testId,
}: AuthSubmitButtonProps) {
  return (
    <button
      className="min-h-12 w-full border-4 border-black bg-black px-5 py-3 text-sm font-black tracking-[0.16em] text-white uppercase shadow-[6px_6px_0_0_#000] outline-none transition-none hover:-translate-x-0.5 hover:-translate-y-0.5 hover:bg-white hover:text-black hover:shadow-[8px_8px_0_0_#000] focus-visible:bg-white focus-visible:text-black focus-visible:[outline:4px_solid_#000] focus-visible:outline-offset-4 active:translate-x-1 active:translate-y-1 active:shadow-none disabled:translate-x-0 disabled:translate-y-0 disabled:cursor-not-allowed disabled:border-dashed disabled:bg-white disabled:text-black disabled:shadow-none"
      data-testid={testId}
      disabled={isLoading}
      type="submit"
    >
      {isLoading ? loadingLabel : idleLabel}
    </button>
  );
}
