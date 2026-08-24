"use client";

import { AppIcon } from "@/components/ui/app-icon";

import { useState } from "react";
import { updatePassword } from "@/hooks/useProfile";
import { getBackendErrorMessage } from "@/lib/errors";

export default function PasswordForm() {
  const [formData, setFormData] = useState({
    old_password: "",
    new_password: "",
    confirm_password: "",
  });
  const [isSaving, setIsSaving] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setErrorMsg("");
    setSuccessMsg("");

    if (formData.new_password !== formData.confirm_password) {
      setErrorMsg("Mật khẩu xác nhận không khớp");
      setIsSaving(false);
      return;
    }
    if (formData.new_password.length < 8) {
      setErrorMsg("Mật khẩu mới phải có ít nhất 8 ký tự");
      setIsSaving(false);
      return;
    }

    try {
      await updatePassword({
        old_password: formData.old_password,
        new_password: formData.new_password,
      });
      setSuccessMsg("Cập nhật mật khẩu thành công!");
      setFormData({ old_password: "", new_password: "", confirm_password: "" });
    } catch (err: unknown) {
      setErrorMsg(getBackendErrorMessage(err, "The password could not be updated."));
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="bg-white border-4 border-black p-6 md:p-8 shadow-[8px_8px_0_0_rgba(0,0,0,1)]">
      <div className="flex items-center justify-between mb-6 border-b-4 border-black pb-4">
        <h2 className="text-2xl font-black uppercase flex items-center gap-3">
          <AppIcon name="lock" className="text-black size-8" />
          Bảo Mật & Mật Khẩu
        </h2>
      </div>

      <form onSubmit={handleSubmit} className="max-w-md space-y-4">
        {errorMsg && (
          <div className="p-3 border-2 border-black bg-white text-black font-mono font-bold uppercase text-sm">
            {errorMsg}
          </div>
        )}
        {successMsg && (
          <div className="p-3 border-2 border-black bg-white text-black font-mono font-bold uppercase text-sm">
            {successMsg}
          </div>
        )}

        <div className="flex flex-col">
          <label className="font-mono text-sm font-bold uppercase mb-2">Mật khẩu hiện tại</label>
          <input
            type="password"
            name="old_password"
            value={formData.old_password}
            onChange={handleInputChange}
            required
            className="border-4 border-black p-3 font-mono focus:outline-none focus:ring-0 focus:border-black shadow-[4px_4px_0_0_rgba(0,0,0,1)]"
          />
        </div>

        <div className="flex flex-col">
          <label className="font-mono text-sm font-bold uppercase mb-2">Mật khẩu mới</label>
          <input
            type="password"
            name="new_password"
            value={formData.new_password}
            onChange={handleInputChange}
            required
            className="border-4 border-black p-3 font-mono focus:outline-none focus:ring-0 focus:border-black shadow-[4px_4px_0_0_rgba(0,0,0,1)]"
          />
        </div>

        <div className="flex flex-col">
          <label className="font-mono text-sm font-bold uppercase mb-2">Xác nhận mật khẩu mới</label>
          <input
            type="password"
            name="confirm_password"
            value={formData.confirm_password}
            onChange={handleInputChange}
            required
            className="border-4 border-black p-3 font-mono focus:outline-none focus:ring-0 focus:border-black shadow-[4px_4px_0_0_rgba(0,0,0,1)]"
          />
        </div>

        <button
          type="submit"
          disabled={isSaving}
          className="w-full px-6 py-3 mt-4 bg-black text-white font-mono font-bold uppercase border-2 border-black hover:bg-white hover:text-black transition-all shadow-[4px_4px_0_0_rgba(0,0,0,1)] disabled:opacity-50"
        >
          {isSaving ? "Đang cập nhật..." : "Đổi mật khẩu"}
        </button>
      </form>
    </div>
  );
}
