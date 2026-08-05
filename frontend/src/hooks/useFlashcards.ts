import useSWR from "swr";
import { fetcher } from "./useFetch";
import type { Topic, FlashcardDeck, Flashcard } from "@/types";
import api from "@/lib/api";

export function useTopicDecks(topicId: string | null) {
  const { data, error, isLoading, mutate } = useSWR<FlashcardDeck[]>(
    topicId ? `/flashcards/topics/${topicId}/decks` : null,
    fetcher
  );

  return {
    decks: data || [],
    isLoading,
    isError: error,
    mutate,
  };
}

export function useDeckDetail(deckId: string | null) {
  const { data, error, isLoading, mutate } = useSWR<FlashcardDeck>(
    deckId ? `/flashcards/decks/${deckId}` : null,
    fetcher
  );

  return {
    deck: data,
    isLoading,
    isError: error,
    mutate,
  };
}

export interface DeckCreate {
  topic_id: string;
  title: string;
  description?: string;
}

export interface CardCreate {
  front_content: string;
  back_content: string;
  order_index?: number;
}

export interface BriefUpdate {
  brief_content: string;
}

export const createDeck = async (data: DeckCreate): Promise<FlashcardDeck> => {
  const response = await api.post<FlashcardDeck>("/flashcards/decks", data);
  return response.data;
};

export const createCard = async (deckId: string, data: CardCreate): Promise<Flashcard> => {
  const response = await api.post<Flashcard>(`/flashcards/decks/${deckId}/cards`, data);
  return response.data;
};

export const updateTopicBrief = async (topicId: string, data: BriefUpdate): Promise<Topic> => {
  const response = await api.put<Topic>(`/flashcards/topics/${topicId}/brief`, data);
  return response.data;
};

export const generateTopicKitAi = async (materialId: string, topicId: string): Promise<unknown> => {
  const response = await api.post(`/flashcards/ai/generate-topic-kit`, {
    material_id: materialId,
    topic_id: topicId,
  });
  return response.data;
};

export function useStudyCards(deckId: string | null) {
  const { data, error, isLoading, mutate } = useSWR<Flashcard[]>(
    deckId ? `/flashcards/student/decks/${deckId}/study` : null,
    fetcher
  );

  return {
    cards: data || [],
    isLoading,
    isError: error,
    mutate,
  };
}

export interface ReviewSubmit {
  rating: "EASY" | "GOOD" | "HARD" | "AGAIN";
}

export const submitCardReview = async (cardId: string, data: ReviewSubmit): Promise<unknown> => {
  const response = await api.post(`/flashcards/student/cards/${cardId}/review`, data);
  return response.data;
};
