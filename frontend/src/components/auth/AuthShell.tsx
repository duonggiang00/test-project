import Link from "next/link";

import { PlayStudyBrand } from "@/components/branding/PlayStudyBrand";
import styles from "./AuthShell.module.css";

type AuthShellProps = {
  eyebrow: string;
  title: string;
  description: string;
  children: React.ReactNode;
};

export function AuthShell({
  eyebrow,
  title,
  description,
  children,
}: AuthShellProps) {
  return (
    <div
      className={`${styles.surface} min-h-dvh bg-white text-black lg:grid lg:grid-cols-[minmax(18rem,0.8fr)_minmax(0,1.2fr)]`}
      data-auth-surface
      data-testid="auth-shell"
    >
      <aside className="flex min-h-48 flex-col justify-between bg-black p-6 text-white sm:p-8 lg:min-h-dvh lg:p-12">
        <div>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b-2 border-white pb-3">
            <PlayStudyBrand tone="dark" size="small" />
            <span className="text-xs font-bold tracking-[0.22em] uppercase">
              / Authentication
            </span>
          </div>
          <p className="mt-7 text-4xl leading-[0.95] font-black tracking-[-0.06em] uppercase sm:text-5xl lg:mt-12 lg:text-7xl">
            Learn.
            <br />
            Create.
            <br />
            Track.
          </p>
        </div>
        <p className="mt-8 max-w-xs border-t-2 border-white pt-3 text-xs font-bold tracking-[0.18em] uppercase lg:mt-12">
          Class-centered learning system
        </p>
      </aside>

      <main className="min-w-0 bg-white px-5 py-7 sm:px-10 sm:py-10 lg:flex lg:min-h-dvh lg:items-center lg:px-16 lg:py-12">
        <div className="mx-auto w-full max-w-xl">
          <Link
            className="inline-flex min-h-11 items-center border-b-2 border-black text-sm font-bold tracking-[0.12em] uppercase outline-none focus:[outline:4px_solid_#000] focus:outline-offset-4"
            href="/"
          >
            &larr; Home
          </Link>

          <header className="mt-10 border-b-4 border-black pb-5">
            <p className="text-xs font-bold tracking-[0.2em] uppercase">
              {eyebrow}
            </p>
            <h1 className="mt-2 text-4xl leading-none font-black tracking-[-0.04em] uppercase sm:text-5xl">
              {title}
            </h1>
            <p className="mt-4 max-w-lg text-base leading-6 font-medium">
              {description}
            </p>
          </header>

          <div className="mt-7">{children}</div>
        </div>
      </main>
    </div>
  );
}
