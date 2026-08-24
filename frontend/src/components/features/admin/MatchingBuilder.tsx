import React from "react";
import { Plus, Trash2 } from "lucide-react";

export interface MatchingPair {
  left: string;
  right: string;
}

interface MatchingBuilderProps {
  pairs: MatchingPair[];
  onChange: (pairs: MatchingPair[]) => void;
}

export default function MatchingBuilder({ pairs, onChange }: MatchingBuilderProps) {
  const handleAddPair = () => {
    onChange([...pairs, { left: "", right: "" }]);
  };

  const handleRemovePair = (index: number) => {
    const newPairs = [...pairs];
    newPairs.splice(index, 1);
    onChange(newPairs);
  };

  const handleChangeLeft = (index: number, value: string) => {
    const newPairs = [...pairs];
    newPairs[index].left = value;
    onChange(newPairs);
  };

  const handleChangeRight = (index: number, value: string) => {
    const newPairs = [...pairs];
    newPairs[index].right = value;
    onChange(newPairs);
  };

  return (
    <div className="flex flex-col gap-4 w-full">
      <div className="flex justify-between items-center">
        <h3 className="font-mono font-bold uppercase text-lg text-black">Matching Pairs</h3>
        <button
          type="button"
          onClick={handleAddPair}
          className="flex items-center gap-2 border-4 border-black bg-white px-4 py-2 font-mono font-bold uppercase text-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] active:translate-x-[4px] active:translate-y-[4px] active:shadow-none transition-all"
        >
          <Plus size={18} />
          Add Pair
        </button>
      </div>

      {pairs.length === 0 ? (
        <div className="border-4 border-black border-dashed p-8 text-center font-mono uppercase text-black">
          No matching pairs added yet.
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          {pairs.map((pair, index) => (
            <div
              key={index}
              className="flex items-start gap-4 border-4 border-black bg-white p-4 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]"
            >
              <div className="flex-1 flex flex-col gap-2">
                <label className="font-mono font-bold uppercase text-sm">Left Side</label>
                <textarea
                  value={pair.left}
                  onChange={(e) => handleChangeLeft(index, e.target.value)}
                  placeholder="e.g. Apple"
                  className="w-full resize-y min-h-[80px] border-4 border-black bg-white p-2 font-mono text-black focus:outline-none focus:ring-4 focus:ring-black/20"
                />
              </div>

              <div className="flex flex-col gap-2 justify-center py-8">
                <span className="font-mono font-bold text-xl">=</span>
              </div>

              <div className="flex-1 flex flex-col gap-2">
                <label className="font-mono font-bold uppercase text-sm">Right Side</label>
                <textarea
                  value={pair.right}
                  onChange={(e) => handleChangeRight(index, e.target.value)}
                  placeholder="e.g. Quả Táo"
                  className="w-full resize-y min-h-[80px] border-4 border-black bg-white p-2 font-mono text-black focus:outline-none focus:ring-4 focus:ring-black/20"
                />
              </div>

              <button
                type="button"
                onClick={() => handleRemovePair(index)}
                className="mt-8 flex items-center justify-center border-4 border-black bg-white p-2 font-mono font-bold uppercase text-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:bg-white hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] active:translate-x-[4px] active:translate-y-[4px] active:shadow-none transition-all"
                title="Remove Pair"
              >
                <Trash2 size={20} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
