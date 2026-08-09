"use client";

import { useUsers, updateUserRole, deleteUser } from "@/hooks/useUsers";
import { Loader2, Eye, Trash2 } from "lucide-react";
import { useState } from "react";
import Link from "next/link";
import { useConfirm } from "@/hooks/useConfirm";
import { logBackendError } from "@/lib/errors";

export default function StudentsPage() {
  const { users, isLoading, mutate } = useUsers();
  const [updating, setUpdating] = useState<string | null>(null);
  const { confirm, ConfirmDialog } = useConfirm();

  const handleRoleChange = async (userId: string, newRole: string) => {
    try {
      setUpdating(userId);
      await updateUserRole(userId, newRole);
      await mutate();
    } catch (error) {
      logBackendError("User role update failed", error);
    } finally {
      setUpdating(null);
    }
  };

  const handleDelete = async (userId: string) => {
    if (!await confirm("Are you sure you want to delete this user?")) return;
    try {
      setUpdating(userId);
      await deleteUser(userId);
      await mutate();
    } catch (error) {
      logBackendError("User delete failed", error);
    } finally {
      setUpdating(null);
    }
  };

  return (
    <div className="p-8 bg-white text-black min-h-screen">
      <h1 className="text-3xl font-bold font-mono uppercase mb-8 border-b-4 border-black pb-4">
        User Management
      </h1>
      
      {isLoading ? (
        <div className="flex items-center space-x-2 font-mono font-bold uppercase">
          <Loader2 className="w-6 h-6 animate-spin" />
          <span>Loading users...</span>
        </div>
      ) : (
        <div className="border-4 border-black overflow-x-auto shadow-[8px_8px_0_0_rgba(0,0,0,1)] bg-white">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b-4 border-black bg-white">
                <th className="p-4 border-r-4 border-black font-mono font-bold uppercase text-sm">Email</th>
                <th className="p-4 border-r-4 border-black font-mono font-bold uppercase text-sm">Full Name</th>
                <th className="p-4 border-r-4 border-black font-mono font-bold uppercase text-sm">Role</th>
                <th className="p-4 font-mono font-bold uppercase text-sm">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id} className="border-b-4 border-black last:border-0 bg-white">
                  <td className="p-4 border-r-4 border-black font-mono">{user.email}</td>
                  <td className="p-4 border-r-4 border-black font-mono">{user.full_name || "-"}</td>
                  <td className="p-4 border-r-4 border-black">
                    <select
                      className="border-2 border-black bg-white text-black p-2 w-full font-mono font-bold uppercase disabled:opacity-50 cursor-pointer focus:outline-none focus:ring-0 focus:bg-black focus:text-white"
                      value={user.role}
                      onChange={(e) => handleRoleChange(user.id, e.target.value)}
                      disabled={updating === user.id}
                    >
                      <option value="student">Student</option>
                      <option value="teacher">Teacher</option>
                      <option value="admin">Admin</option>
                    </select>
                  </td>
                  <td className="p-4">
                    <div className="flex items-center gap-3">
                      <Link 
                        href={`/students/${user.id}`}
                        className="inline-flex items-center justify-center border-2 border-black bg-white text-black p-2 hover:bg-black hover:text-white transition-none shadow-[2px_2px_0_0_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-[2px] hover:translate-y-[2px]"
                        title="View Profile"
                      >
                        <Eye className="w-5 h-5" />
                      </Link>
                      <button
                        className="inline-flex items-center justify-center border-2 border-black bg-white text-black p-2 hover:bg-black hover:text-white transition-none shadow-[2px_2px_0_0_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-[2px] hover:translate-y-[2px] disabled:opacity-50 disabled:hover:shadow-[2px_2px_0_0_rgba(0,0,0,1)] disabled:hover:translate-x-0 disabled:hover:translate-y-0"
                        onClick={() => handleDelete(user.id)}
                        disabled={updating === user.id}
                        title="Delete User"
                      >
                        {updating === user.id ? <Loader2 className="w-5 h-5 animate-spin" /> : <Trash2 className="w-5 h-5" />}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {users.length === 0 && (
                <tr>
                  <td colSpan={4} className="p-8 text-center font-mono font-bold uppercase text-lg">
                    No users found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
      <ConfirmDialog />
    </div>
  );
}
