import Link from "next/link";
import { ArrowRight, LogIn, UserPlus } from "lucide-react";
import { PlayStudyBrand } from "@/components/branding/PlayStudyBrand";

export default function LandingPage() {
  return (
    <div className="flex flex-col min-h-screen bg-white text-black max-w-7xl mx-auto border-x-4 border-black">
      {/* Header */}
      <header className="flex items-center justify-between px-8 py-6 w-full border-b-4 border-black bg-white">
        <Link href="/" aria-label="PlayStudy home">
          <PlayStudyBrand />
        </Link>
        <nav className="hidden md:flex gap-6 items-center">
          {/* <Link href="#features" className="text-base font-bold font-mono tracking-widest uppercase hover:underline underline-offset-4">
            Tính Năng
          </Link> */}
          <div className="flex gap-4">
            <Link 
              href="/login" 
              className="flex items-center gap-2 text-sm font-bold font-mono uppercase tracking-widest border-4 border-black bg-white px-6 py-2 shadow-[4px_4px_0_0_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-[4px] hover:translate-y-[4px] transition-all"
            >
              <LogIn className="w-4 h-4" />
              Đăng Nhập
            </Link>
            <Link 
              href="/register" 
              className="flex items-center gap-2 text-sm font-bold font-mono uppercase tracking-widest border-4 border-black bg-black text-white px-6 py-2 shadow-[4px_4px_0_0_rgba(0,0,0,1)] hover:bg-white hover:text-black transition-all"
            >
              <UserPlus className="w-4 h-4" />
              Đăng Ký
            </Link>
          </div>
        </nav>
      </header>

      {/* Hero Section */}
      <main className="flex-1 flex flex-col items-center justify-center w-full px-6 text-center mt-24 mb-24">
        <div className="inline-flex items-center gap-2 px-6 py-3 border-4 border-black text-base font-bold mb-12 uppercase tracking-widest bg-white shadow-[8px_8px_0_0_rgba(0,0,0,1)]">
          <span>Nền tảng Giáo dục Online</span>
        </div>
        
        <h2 className="text-5xl md:text-7xl font-bold tracking-widest leading-tight mb-8 uppercase font-mono">
          Học Tập Thông Minh. <br />
          <span className="bg-black text-white px-4 leading-[1.5]">Kết Quả Vượt Trội.</span>
        </h2>
        
        <p className="text-lg md:text-xl font-mono text-black max-w-3xl mb-16 border-l-8 border-black pl-6 text-left">
          Hệ thống đánh giá và thi cử toàn diện kết hợp cùng Trí tuệ Nhân tạo. Giúp giáo viên tiết kiệm 80% thời gian ra đề và mang lại trải nghiệm làm bài đầy hứng khởi cho học sinh.
        </p>

        {/* Call to Action */}
        <div className="flex flex-col sm:flex-row gap-6 w-full justify-center">
          <Link 
            href="/register"
            className="flex items-center justify-center gap-3 px-10 py-5 bg-black text-white font-bold font-mono uppercase tracking-widest border-4 border-black shadow-[8px_8px_0_0_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-[8px] hover:translate-y-[8px] hover:bg-white hover:text-black transition-all text-xl"
          >
            Bắt Đầu Ngay <ArrowRight className="w-6 h-6" />
          </Link>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t-4 border-black py-8 px-8 flex justify-between items-center text-black font-mono font-bold uppercase text-sm">
        <p>© 2026 PlayStudy.</p>
        <p>Wireframe Edition.</p>
      </footer>
    </div>
  );
}
