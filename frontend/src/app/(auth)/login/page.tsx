"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Eye, EyeOff, ArrowLeft } from "lucide-react";
import { login } from "@/services/apiService";
import { useUserStore } from "@/lib/store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { getBackendErrorMessage } from "@/lib/errors";
import { toast } from "@/components/ui/toast";

export default function LoginPage() {
  const router = useRouter();
  const { setUser } = useUserStore();
  
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const data = await login(email, password, rememberMe);
      
      if (typeof window !== "undefined") {
        // Token is now secured via HttpOnly cookies by BFF
      }
      
      setUser({
        id: data.user.id,
        email: data.user.email,
        role: data.user.role,
        full_name: data.user.full_name
      });
      toast.add({
        title: "Đăng nhập thành công",
        description: `Xin chào ${data.user.full_name}`,
        type: "success"
      });

      if (data.user.role === "teacher" || data.user.role === "admin") {
        router.push("/dashboard");
      } else {
        router.push("/student/home");
      }
    } catch (error) {
      toast.add({
        title: "Login failed",
        description: getBackendErrorMessage(error),
        type: "error"
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen w-full items-center justify-center bg-white text-black px-4 font-mono relative">
      <Link 
        href="/" 
        className="absolute top-4 left-4 flex items-center gap-2 border-4 border-black px-4 py-2 font-bold uppercase tracking-widest shadow-[4px_4px_0_0_rgba(0,0,0,1)] bg-white hover:bg-black hover:text-white transition-colors"
      >
        <ArrowLeft size={20} strokeWidth={3} />
        Trang chủ
      </Link>
      <Card className="w-full max-w-md border-4 border-black rounded-none shadow-[4px_4px_0_0_rgba(0,0,0,1)] bg-white text-black">
        <CardHeader className="space-y-2 text-center border-b-4 border-black pb-6">
          <CardTitle className="text-2xl font-mono tracking-widest uppercase font-bold text-black">Đăng nhập</CardTitle>
          <CardDescription className="font-mono text-black uppercase">
            Nhập email và mật khẩu của bạn để truy cập hệ thống
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleLogin}>
          <CardContent className="space-y-6 pt-6">
            <div className="space-y-2">
              <label className="text-sm font-bold leading-none font-mono tracking-widest uppercase text-black" htmlFor="email">
                Email
              </label>
              <Input
                id="email"
                type="email"
                placeholder="teacher@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                data-testid="login-email-input"
                className="border-4 border-black rounded-none shadow-[4px_4px_0_0_rgba(0,0,0,1)] font-mono text-black focus-visible:ring-0 focus-visible:ring-offset-0 focus:border-black bg-white"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-bold leading-none font-mono tracking-widest uppercase text-black" htmlFor="password">
                Mật khẩu
              </label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  data-testid="login-password-input"
                  className="border-4 border-black rounded-none shadow-[4px_4px_0_0_rgba(0,0,0,1)] font-mono text-black focus-visible:ring-0 focus-visible:ring-offset-0 focus:border-black bg-white pr-10"
                />
                <button
                  type="button"
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-black"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? <EyeOff size={20} strokeWidth={3} /> : <Eye size={20} strokeWidth={3} />}
                </button>
              </div>
            </div>
            <div className="flex items-center justify-between mt-4">
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="rememberMe"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="w-5 h-5 border-4 border-black rounded-none appearance-none checked:bg-black cursor-pointer transition-colors"
                />
                <label htmlFor="rememberMe" className="text-sm font-bold font-mono uppercase text-black cursor-pointer">
                  Ghi nhớ tôi
                </label>
              </div>
              <Link href="/forgot-password" className="text-sm font-bold font-mono uppercase text-black hover:underline underline-offset-4">
                Quên mật khẩu?
              </Link>
            </div>
          </CardContent>
          <CardFooter className="pt-2">
            <Button 
              className="w-full border-4 border-black rounded-none shadow-[4px_4px_0_0_rgba(0,0,0,1)] font-mono tracking-widest uppercase font-bold bg-black text-white hover:bg-white hover:text-black transition-colors"
              type="submit" 
              disabled={isLoading} 
              data-testid="login-submit-button"
            >
              {isLoading ? "Đang xử lý..." : "Đăng nhập"}
            </Button>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
