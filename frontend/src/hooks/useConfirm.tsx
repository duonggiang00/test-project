import React, { useState, useCallback } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

export function useConfirm() {
  const [isOpen, setIsOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [resolveRef, setResolveRef] = useState<(value: boolean) => void>();

  const confirm = useCallback((msg: string): Promise<boolean> => {
    setMessage(msg);
    setIsOpen(true);
    return new Promise((resolve) => {
      setResolveRef(() => resolve);
    });
  }, []);

  const handleConfirm = useCallback(() => {
    setIsOpen(false);
    if (resolveRef) resolveRef(true);
  }, [resolveRef]);

  const handleCancel = useCallback(() => {
    setIsOpen(false);
    if (resolveRef) resolveRef(false);
  }, [resolveRef]);

  const ConfirmDialog = useCallback(() => (
    <Dialog open={isOpen} onOpenChange={(open) => { if (!open) handleCancel(); }}>
      <DialogContent className="border-4 border-black shadow-[8px_8px_0_0_rgba(0,0,0,1)] bg-white rounded-none sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle className="font-black text-xl uppercase tracking-tight font-mono">Xác nhận</DialogTitle>
          <DialogDescription className="hidden">Confirmation dialog</DialogDescription>
        </DialogHeader>
        <div className="py-4 font-mono font-bold text-black">{message}</div>
        <DialogFooter className="flex gap-2 justify-end sm:justify-end">
          <Button data-testid="confirm-dialog-cancel" variant="outline" onClick={handleCancel} className="border-2 border-black rounded-none shadow-[2px_2px_0_0_rgba(0,0,0,1)] font-mono uppercase font-bold hover:bg-gray-100 text-black">
            Hủy
          </Button>
          <Button data-testid="confirm-dialog-confirm" onClick={handleConfirm} className="border-2 border-black rounded-none shadow-[2px_2px_0_0_rgba(0,0,0,1)] font-mono uppercase font-bold bg-black text-white hover:bg-gray-800 transition-all">
            Đồng ý
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  ), [isOpen, message, handleCancel, handleConfirm]);

  return { confirm, ConfirmDialog };
}
