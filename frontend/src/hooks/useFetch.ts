import api from "@/lib/api";

export const fetcher = async (url: string) => {
  const res = await api.get(url);
  return res.data;
};
