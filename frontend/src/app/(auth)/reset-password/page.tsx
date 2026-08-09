"use client";

import { useState, use } from "react";
import { useRouter } from "next/navigation";
import { resetPassword } from "@/services/apiService";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { toast } from "@/components/ui/toast";
import { Eye, EyeOff } from "lucide-react";
import Link from "next/link";
import { getBackendErrorMessage } from "@/lib/errors";

interface PageProps {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}

export default function ResetPasswordPage({ searchParams }: PageProps) {
  const resolvedSearchParams = use(searchParams);
  const token = typeof resolvedSearchParams.token === 'string' ? resolvedSearchParams.token : null;

  const router = useRouter();
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!token) {
      toast.add({ title: "Lỗi", description: "Mã khôi phục không hợp lệ", type: "error" });
      return;
    }

    if (password !== confirmPassword) {
      toast.add({ title: "Lỗi", description: "Mật khẩu xác nhận không khớp", type: "error" });
      return;
    }

    if (password.length < 8) {
      toast.add({ title: "Lỗi", description: "Mật khẩu phải có ít nhất 8 ký tự", type: "error" });
      return;
    }

    setIsLoading(true);

    try {
      await resetPassword({ token, new_password: password });
      toast.add({
        title: "Thành công",
        description: "Mật khẩu đã được đặt lại thành công. Vui lòng đăng nhập.",
        type: "success"
      });
      router.push("/login");
    } catch (error) {
      toast.add({
        title: "Password reset failed",
        description: getBackendErrorMessage(
          error,
          "The reset link is invalid or has expired.",
        ),
        type: "error"
      });
    } finally {
      setIsLoading(false);
    }
  };

  if (!token) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-white text-black px-4 font-mono">
        <Card className="w-full max-w-md border-4 border-black rounded-none shadow-[4px_4px_0_0_rgba(0,0,0,1)] bg-white text-black p-6 text-center space-y-4">
          <h2 className="text-xl font-bold uppercase">Lỗi truy cập</h2>
          <p>Đường dẫn khôi phục không hợp lệ hoặc thiếu Token.</p>
          <Button className="w-full border-4 border-black rounded-none shadow-[4px_4px_0_0_rgba(0,0,0,1)] font-mono tracking-widest uppercase font-bold bg-black text-white hover:bg-white hover:text-black transition-colors" onClick={() => router.push("/login")}>
            Về trang Đăng nhập
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex h-screen w-full items-center justify-center bg-white text-black px-4 font-mono">
      <Card className="w-full max-w-md border-4 border-black rounded-none shadow-[4px_4px_0_0_rgba(0,0,0,1)] bg-white text-black">
        <CardHeader className="space-y-2 text-center border-b-4 border-black pb-6">
          <CardTitle className="text-2xl font-mono tracking-widest uppercase font-bold text-black">Đặt Lại Mật Khẩu</CardTitle>
          <CardDescription className="font-mono text-black uppercase">
            Vui lòng nhập mật khẩu mới
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-6 pt-6">
            <div className="space-y-2">
              <label className="text-sm font-bold leading-none font-mono tracking-widest uppercase text-black" htmlFor="password">
                Mật khẩu mới
              </label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
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
                Xác nhận Mật khẩu mới
              </label>
              <div className="relative">
                <Input
                  id="confirmPassword"
                  type={showConfirmPassword ? "text" : "password"}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
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
            >
              {isLoading ? "Đang xử lý..." : "Cập Nhật Mật Khẩu"}
            </Button>
            <div className="text-center w-full mt-2">
              <Link href="/login" className="text-sm font-bold font-mono uppercase text-black hover:underline underline-offset-4">
                Hủy và về đăng nhập
              </Link>
            </div>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
