"use client";

import { useState, useRef } from "react";
import { useProfile, updateProfile, uploadAvatar } from "@/hooks/useProfile";
import Image from "next/image";
import { toast } from "@/components/ui/toast";
import { getBackendErrorMessage } from "@/lib/errors";

const emptyProfileDraft = {
  full_name: "",
  phone_number: "",
  date_of_birth: "",
  bio: "",
};

export default function ProfileForm() {
  const { profile, mutate } = useProfile();
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState(emptyProfileDraft);
  const [isSaving, setIsSaving] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!profile) return null;

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setErrorMsg("");
    try {
      await updateProfile(formData);
      await mutate();
      setIsEditing(false);
    } catch (err: unknown) {
      setErrorMsg(getBackendErrorMessage(err, "The profile could not be updated."));
    } finally {
      setIsSaving(false);
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      try {
        await uploadAvatar(file);
        await mutate();
      } catch (err: unknown) {
        toast.add({
          title: "Error",
          description: getBackendErrorMessage(err, "The avatar could not be uploaded."),
          type: "error",
        });
      }
    }
  };

  return (
    <div className="bg-white border-4 border-black p-6 md:p-8 shadow-[8px_8px_0_0_rgba(0,0,0,1)]">
      <div className="flex items-center justify-between mb-6 border-b-4 border-black pb-4">
        <h2 className="text-2xl font-black uppercase flex items-center gap-3">
          <span className="material-symbols-outlined text-black text-3xl">manage_accounts</span>
          Hồ Sơ Cá Nhân
        </h2>
        {!isEditing && (
          <button
            onClick={() => {
              setFormData({
                full_name: profile.full_name || "",
                phone_number: profile.phone_number || "",
                date_of_birth: profile.date_of_birth || "",
                bio: profile.bio || "",
              });
              setIsEditing(true);
            }}
            className="px-4 py-2 bg-black text-white font-mono font-bold uppercase border-2 border-black hover:bg-white hover:text-black transition-all shadow-[4px_4px_0_0_rgba(0,0,0,1)]"
          >
            Chỉnh sửa
          </button>
        )}
      </div>

      <div className="flex flex-col md:flex-row gap-8">
        {/* Avatar Section */}
        <div className="flex flex-col items-center gap-4">
          <div className="w-32 h-32 border-4 border-black bg-gray-100 flex items-center justify-center overflow-hidden relative shadow-[4px_4px_0_0_rgba(0,0,0,1)]">
            {profile.avatar_url ? (
              <Image src={profile.avatar_url} alt="Avatar" fill className="object-cover" />
            ) : (
              <span className="material-symbols-outlined text-6xl text-black">person</span>
            )}
          </div>
          <button
            onClick={() => fileInputRef.current?.click()}
            className="px-4 py-2 bg-white text-black font-mono font-bold text-sm uppercase border-2 border-black hover:bg-black hover:text-white transition-all shadow-[2px_2px_0_0_rgba(0,0,0,1)]"
          >
            Đổi Avatar
          </button>
          <input
            type="file"
            accept="image/*"
            ref={fileInputRef}
            onChange={handleFileChange}
            className="hidden"
          />
        </div>

        {/* Info Section */}
        <div className="flex-1">
          {errorMsg && (
            <div className="mb-4 p-3 border-2 border-black bg-red-100 text-black font-mono font-bold uppercase text-sm">
              {errorMsg}
            </div>
          )}
          {!isEditing ? (
            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <span className="font-mono text-xs text-gray-500 uppercase block mb-1">Họ và tên</span>
                  <span className="font-mono text-lg font-bold text-black border-b-2 border-black block pb-1">{profile.full_name || "Chưa cập nhật"}</span>
                </div>
                <div>
                  <span className="font-mono text-xs text-gray-500 uppercase block mb-1">Email</span>
                  <span className="font-mono text-lg font-bold text-black border-b-2 border-black block pb-1">{profile.email}</span>
                </div>
                <div>
                  <span className="font-mono text-xs text-gray-500 uppercase block mb-1">Số điện thoại</span>
                  <span className="font-mono text-lg font-bold text-black border-b-2 border-black block pb-1">{profile.phone_number || "Chưa cập nhật"}</span>
                </div>
                <div>
                  <span className="font-mono text-xs text-gray-500 uppercase block mb-1">Ngày sinh</span>
                  <span className="font-mono text-lg font-bold text-black border-b-2 border-black block pb-1">{profile.date_of_birth || "Chưa cập nhật"}</span>
                </div>
              </div>
              <div>
                <span className="font-mono text-xs text-gray-500 uppercase block mb-1">Giới thiệu (Bio)</span>
                <p className="font-mono text-base font-bold text-black border-2 border-black p-3 bg-gray-50 min-h-[80px]">
                  {profile.bio || "Chưa cập nhật"}
                </p>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="flex flex-col">
                  <label className="font-mono text-sm font-bold uppercase mb-2">Họ và tên</label>
                  <input
                    type="text"
                    name="full_name"
                    value={formData.full_name}
                    onChange={handleInputChange}
                    className="border-4 border-black p-3 font-mono focus:outline-none focus:ring-0 focus:border-black shadow-[4px_4px_0_0_rgba(0,0,0,1)]"
                  />
                </div>
                <div className="flex flex-col">
                  <label className="font-mono text-sm font-bold uppercase mb-2">Email (Không đổi)</label>
                  <input
                    type="text"
                    value={profile.email}
                    disabled
                    className="border-4 border-black p-3 font-mono bg-gray-200 cursor-not-allowed"
                  />
                </div>
                <div className="flex flex-col">
                  <label className="font-mono text-sm font-bold uppercase mb-2">Số điện thoại</label>
                  <input
                    type="text"
                    name="phone_number"
                    value={formData.phone_number}
                    onChange={handleInputChange}
                    className="border-4 border-black p-3 font-mono focus:outline-none focus:ring-0 focus:border-black shadow-[4px_4px_0_0_rgba(0,0,0,1)]"
                  />
                </div>
                <div className="flex flex-col">
                  <label className="font-mono text-sm font-bold uppercase mb-2">Ngày sinh</label>
                  <input
                    type="date"
                    name="date_of_birth"
                    value={formData.date_of_birth}
                    onChange={handleInputChange}
                    className="border-4 border-black p-3 font-mono focus:outline-none focus:ring-0 focus:border-black shadow-[4px_4px_0_0_rgba(0,0,0,1)]"
                  />
                </div>
              </div>
              <div className="flex flex-col">
                <label className="font-mono text-sm font-bold uppercase mb-2">Giới thiệu (Bio)</label>
                <textarea
                  name="bio"
                  value={formData.bio}
                  onChange={handleInputChange}
                  rows={3}
                  className="border-4 border-black p-3 font-mono focus:outline-none focus:ring-0 focus:border-black shadow-[4px_4px_0_0_rgba(0,0,0,1)]"
                />
              </div>
              <div className="flex justify-end gap-4 mt-6 pt-4 border-t-4 border-black">
                <button
                  type="button"
                  onClick={() => {
                    setIsEditing(false);
                    setFormData({
                      full_name: profile?.full_name || "",
                      phone_number: profile?.phone_number || "",
                      date_of_birth: profile?.date_of_birth || "",
                      bio: profile?.bio || "",
                    });
                  }}
                  className="px-6 py-3 bg-white text-black font-mono font-bold uppercase border-2 border-black hover:bg-gray-100 transition-all"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  disabled={isSaving}
                  className="px-6 py-3 bg-black text-white font-mono font-bold uppercase border-2 border-black hover:bg-white hover:text-black transition-all shadow-[4px_4px_0_0_rgba(0,0,0,1)] disabled:opacity-50"
                >
                  {isSaving ? "Đang lưu..." : "Lưu thay đổi"}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
