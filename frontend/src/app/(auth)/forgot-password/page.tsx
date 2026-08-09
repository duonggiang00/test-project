"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { forgotPassword } from "@/services/apiService";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { toast } from "@/components/ui/toast";
import { getBackendErrorMessage } from "@/lib/errors";

export default function ForgotPasswordPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      await forgotPassword(email);
      setIsSuccess(true);
      toast.add({
        title: "Thành công",
        description: "Đã gửi yêu cầu khôi phục mật khẩu.",
        type: "success"
      });
    } catch (error) {
      toast.add({
        title: "Request failed",
        description: getBackendErrorMessage(
          error,
          "The password reset request could not be completed.",
        ),
        type: "error"
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen w-full items-center justify-center bg-white text-black px-4 font-mono">
      <Card className="w-full max-w-md border-4 border-black rounded-none shadow-[4px_4px_0_0_rgba(0,0,0,1)] bg-white text-black">
        <CardHeader className="space-y-2 text-center border-b-4 border-black pb-6">
          <CardTitle className="text-2xl font-mono tracking-widest uppercase font-bold text-black">Quên Mật Khẩu</CardTitle>
          <CardDescription className="font-mono text-black uppercase">
            Nhập email của bạn để nhận link khôi phục
          </CardDescription>
        </CardHeader>
        {!isSuccess ? (
          <form onSubmit={handleSubmit}>
            <CardContent className="space-y-6 pt-6">
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
                  className="border-4 border-black rounded-none shadow-[4px_4px_0_0_rgba(0,0,0,1)] font-mono text-black focus-visible:ring-0 focus-visible:ring-offset-0 focus:border-black bg-white"
                />
              </div>
            </CardContent>
            <CardFooter className="pt-2 flex flex-col gap-4">
              <Button 
                className="w-full border-4 border-black rounded-none shadow-[4px_4px_0_0_rgba(0,0,0,1)] font-mono tracking-widest uppercase font-bold bg-black text-white hover:bg-white hover:text-black transition-colors"
                type="submit" 
                disabled={isLoading} 
              >
                {isLoading ? "Đang xử lý..." : "Gửi Yêu Cầu"}
              </Button>
              <div className="text-center w-full mt-2">
                <Link href="/login" className="text-sm font-bold font-mono uppercase text-black hover:underline underline-offset-4">
                  Quay lại đăng nhập
                </Link>
              </div>
            </CardFooter>
          </form>
        ) : (
          <CardContent className="pt-6 space-y-6">
            <p className="text-center font-bold text-black uppercase">
              Vui lòng kiểm tra email của bạn để nhận link đổi mật khẩu. (Môi trường Dev: Xem Terminal Backend)
            </p>
            <Button 
              className="w-full border-4 border-black rounded-none shadow-[4px_4px_0_0_rgba(0,0,0,1)] font-mono tracking-widest uppercase font-bold bg-black text-white hover:bg-white hover:text-black transition-colors"
              onClick={() => router.push("/login")}
            >
              Quay lại đăng nhập
            </Button>
          </CardContent>
        )}
      </Card>
    </div>
  );
}
