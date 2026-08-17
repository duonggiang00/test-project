import { LoginForm } from "@/components/auth/LoginForm";

type LoginPageProps = {
  searchParams: Promise<{ registered?: string | string[] }>;
};

export default async function LoginPage({ searchParams }: LoginPageProps) {
  const registered = (await searchParams).registered;

  return <LoginForm registrationComplete={registered === "1"} />;
}
