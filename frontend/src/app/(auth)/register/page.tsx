"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { registerUser } from "@/services/apiService";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { getBackendErrorMessage } from "@/lib/errors";
import { toast } from "@/components/ui/toast";
import Link from "next/link";
import { Eye, EyeOff, ArrowLeft } from "lucide-react";

export default function RegisterPage() {
  const router = useRouter();
  
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (password !== confirmPassword) {
      toast.add({
        title: "Lỗi đăng ký",
        description: "Mật khẩu xác nhận không khớp",
        type: "error"
      });
      return;
    }

    if (password.length < 8) {
      toast.add({
        title: "Lỗi đăng ký",
        description: "Mật khẩu phải có ít nhất 8 ký tự",
        type: "error"
      });
      return;
    }

    setIsLoading(true);

    try {
      await registerUser({ email, password, full_name: fullName });
      
      toast.add({
        title: "Đăng ký thành công",
        description: `Vui lòng đăng nhập để tiếp tục`,
        type: "success"
      });

      router.push("/login");
    } catch (error) {
      toast.add({
        title: "Registration failed",
        description: getBackendErrorMessage(error),
        type: "error"
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen w-full items-center justify-center bg-white text-black px-4 font-mono py-12 relative">
      <Link 
        href="/" 
        className="absolute top-4 left-4 flex items-center gap-2 border-4 border-black px-4 py-2 font-bold uppercase tracking-widest shadow-[4px_4px_0_0_rgba(0,0,0,1)] bg-white hover:bg-black hover:text-white transition-colors"
      >
        <ArrowLeft size={20} strokeWidth={3} />
        Trang chủ
      </Link>
      <Card className="w-full max-w-md border-4 border-black rounded-none shadow-[8px_8px_0_0_rgba(0,0,0,1)] bg-white text-black">
        <CardHeader className="space-y-2 text-center border-b-4 border-black pb-6 bg-black text-white">
          <CardTitle className="text-3xl font-mono tracking-widest uppercase font-bold text-white">Đăng ký</CardTitle>
          <CardDescription className="font-mono text-gray-300 uppercase">
            Tạo tài khoản học sinh mới
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleRegister}>
          <CardContent className="space-y-6 pt-6">
            <div className="space-y-2">
              <label className="text-sm font-bold leading-none font-mono tracking-widest uppercase text-black" htmlFor="fullName">
                Họ và Tên
              </label>
              <Input
                id="fullName"
                type="text"
                placeholder="Nguyễn Văn A"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
                data-testid="register-fullname-input"
                className="border-4 border-black rounded-none shadow-[4px_4px_0_0_rgba(0,0,0,1)] font-mono text-black focus-visible:ring-0 focus-visible:ring-offset-0 focus:border-black bg-white"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-bold leading-none font-mono tracking-widest uppercase text-black" htmlFor="email">
                Email
              </label>
              <Input
                id="email"
                type="email"
                placeholder="student@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                data-testid="register-email-input"
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
                  data-testid="register-password-input"
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
            <div className="space-y-2">
              <label className="text-sm font-bold leading-none font-mono tracking-widest uppercase text-black" htmlFor="confirmPassword">
                Xác nhận Mật khẩu
              </label>
              <div className="relative">
                <Input
                  id="confirmPassword"
                  type={showConfirmPassword ? "text" : "password"}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  data-testid="register-confirm-password-input"
                  className="border-4 border-black rounded-none shadow-[4px_4px_0_0_rgba(0,0,0,1)] font-mono text-black focus-visible:ring-0 focus-visible:ring-offset-0 focus:border-black bg-white pr-10"
                />
                <button
                  type="button"
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-black"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                >
                  {showConfirmPassword ? <EyeOff size={20} strokeWidth={3} /> : <Eye size={20} strokeWidth={3} />}
                </button>
              </div>
            </div>
          </CardContent>
          <CardFooter className="pt-2 flex flex-col gap-4">
            <Button 
              className="w-full border-4 border-black rounded-none shadow-[4px_4px_0_0_rgba(0,0,0,1)] font-mono tracking-widest uppercase font-bold bg-black text-white hover:bg-white hover:text-black transition-colors"
              type="submit" 
              disabled={isLoading} 
              data-testid="register-submit-button"
            >
              {isLoading ? "Đang xử lý..." : "Đăng ký ngay"}
            </Button>
            <div className="text-center w-full mt-4">
              <Link href="/login" className="text-sm font-bold font-mono tracking-widest uppercase text-black hover:underline underline-offset-4">
                Đã có tài khoản? Đăng nhập
              </Link>
            </div>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
