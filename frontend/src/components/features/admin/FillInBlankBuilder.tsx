"use client";

import React, { useEffect } from "react";
import { Plus, Trash2 } from "lucide-react";

export interface BlankAnswer {
  blank_index: number;
  acceptable_answers: string[];
}

interface FillInBlankBuilderProps {
  content: string; // The question content, containing [BLANK] tags
  blanks: BlankAnswer[];
  onChange: (blanks: BlankAnswer[]) => void;
}

export default function FillInBlankBuilder({ content, blanks, onChange }: FillInBlankBuilderProps) {
  useEffect(() => {
    const matches = content.match(/\[BLANK\]/g);
    const count = matches ? matches.length : 0;

    if (count !== blanks.length) {
      const newBlanks: BlankAnswer[] = [];
      for (let i = 0; i < count; i++) {
        const existing = blanks.find(b => b.blank_index === i);
        if (existing) {
          newBlanks.push(existing);
        } else {
          newBlanks.push({ blank_index: i, acceptable_answers: [""] });
        }
      }
      onChange(newBlanks);
    }
  }, [content, blanks, onChange]);

  const handleAddAnswer = (blankIndex: number) => {
    const newBlanks = blanks.map((blank) => {
      if (blank.blank_index === blankIndex) {
        return { ...blank, acceptable_answers: [...blank.acceptable_answers, ""] };
      }
      return blank;
    });
    onChange(newBlanks);
  };

  const handleRemoveAnswer = (blankIndex: number, answerIndex: number) => {
    const newBlanks = blanks.map((blank) => {
      if (blank.blank_index === blankIndex) {
        return {
          ...blank,
          acceptable_answers: blank.acceptable_answers.filter((_, i) => i !== answerIndex),
        };
      }
      return blank;
    });
    onChange(newBlanks);
  };

  const handleChangeAnswer = (blankIndex: number, answerIndex: number, value: string) => {
    const newBlanks = blanks.map((blank) => {
      if (blank.blank_index === blankIndex) {
        const newAnswers = [...blank.acceptable_answers];
        newAnswers[answerIndex] = value;
        return { ...blank, acceptable_answers: newAnswers };
      }
      return blank;
    });
    onChange(newBlanks);
  };

  if (blanks.length === 0) {
    return (
      <div className="p-4 border-4 border-black bg-white shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] text-center">
        <p className="uppercase font-mono font-bold text-gray-500">NO [BLANK] TAGS FOUND IN CONTENT</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {blanks.map((blank) => (
        <div 
          key={`blank-${blank.blank_index}`} 
          className="p-6 border-4 border-black bg-white shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] flex flex-col gap-4"
        >
          <h3 className="text-xl font-bold uppercase font-mono border-b-4 border-black pb-2">
            Blank #{blank.blank_index + 1}
          </h3>
          
          <div className="flex flex-col gap-3">
            {blank.acceptable_answers.map((answer, answerIndex) => (
              <div key={answerIndex} className="flex items-center gap-2">
                <input
                  type="text"
                  value={answer}
                  onChange={(e) => handleChangeAnswer(blank.blank_index, answerIndex, e.target.value)}
                  placeholder="ACCEPTABLE ANSWER"
                  className="flex-1 p-3 border-4 border-black font-mono uppercase outline-none focus:bg-gray-100 placeholder:text-gray-400"
                />
                <button
                  type="button"
                  onClick={() => handleRemoveAnswer(blank.blank_index, answerIndex)}
                  disabled={blank.acceptable_answers.length <= 1}
                  className="p-3 border-4 border-black bg-white hover:bg-gray-200 disabled:opacity-50 flex items-center justify-center transition-colors cursor-pointer disabled:cursor-not-allowed"
                >
                  <Trash2 className="w-5 h-5 text-black" />
                </button>
              </div>
            ))}
          </div>

          <button
            type="button"
            onClick={() => handleAddAnswer(blank.blank_index)}
            className="self-start flex items-center gap-2 px-4 py-2 border-4 border-black bg-white shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:translate-y-[2px] hover:translate-x-[2px] hover:shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] transition-all font-mono uppercase font-bold cursor-pointer text-black"
          >
            <Plus className="w-5 h-5 text-black" />
            Add Alternative
          </button>
        </div>
      ))}
    </div>
  );
}
