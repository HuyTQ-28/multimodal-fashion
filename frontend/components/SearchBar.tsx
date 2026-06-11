"use client";

import { Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

type SearchBarProps = {
  initialQuery?: string;
  large?: boolean;
};

export function SearchBar({ initialQuery = "", large = false }: SearchBarProps) {
  const router = useRouter();
  const [query, setQuery] = useState(initialQuery);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const cleanQuery = query.trim();
    if (cleanQuery) {
      router.push(`/search?q=${encodeURIComponent(cleanQuery)}`);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className={`flex items-center rounded-full border border-black/10 bg-white/80 shadow-xl shadow-black/5 backdrop-blur-xl transition focus-within:border-black/25 ${
        large ? "px-5 py-4" : "px-4 py-3"
      }`}
    >
      <Search size={large ? 22 : 18} className="text-black/40" />
      <input
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Try black shirt, linen jacket, white dress..."
        className="w-full bg-transparent px-4 text-base text-[#111111] outline-none placeholder:text-black/35"
      />
      <button
        type="submit"
        className="rounded-full bg-[#111111] px-5 py-2 text-sm font-medium text-white transition hover:bg-[#2a2a2a]"
      >
        Search
      </button>
    </form>
  );
}
