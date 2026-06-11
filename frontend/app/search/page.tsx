"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";

import { EmptyState } from "@/components/EmptyState";
import { ProductGrid } from "@/components/ProductGrid";
import { ProductCardSkeleton } from "@/components/ProductCardSkeleton";
import { SearchBar } from "@/components/SearchBar";
import { useHybridSearch } from "@/hooks/useHybridSearch";

export default function SearchPage() {
  return (
    <Suspense fallback={<SearchPageSkeleton />}>
      <SearchPageContent />
    </Suspense>
  );
}

function SearchPageContent() {
  const searchParams = useSearchParams();
  const query = searchParams.get("q") ?? "";
  const { data, isLoading } = useHybridSearch(query, 20);

  return (
    <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
      <section className="mx-auto max-w-3xl text-center">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-black/40">
          Hybrid search
        </p>
        <h1 className="mt-3 font-serif text-5xl font-semibold text-[#111111] sm:text-6xl">
          Search by mood, fabric, color.
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-base leading-7 text-black/55">
          Combine text relevance with the distilled recommendation space for
          faster discovery.
        </p>
        <div className="mt-8">
          <SearchBar initialQuery={query} large />
        </div>
      </section>

      <section className="mt-12 rounded-[2rem] bg-white px-4 py-6 shadow-sm shadow-black/5 ring-1 ring-black/[0.04] sm:px-6 lg:px-8">
        {query.trim() ? (
          <ProductGrid
            products={data ?? []}
            loading={isLoading}
            emptyTitle="No pieces matched"
            emptyDescription="Try a broader style phrase like linen shirt, black dress, or minimal jacket."
          />
        ) : (
          <EmptyState
            title="Start with a style cue"
            description="Try linen shirt, black dress, monochrome coat, soft knit, or minimal jacket."
          />
        )}
      </section>
    </div>
  );
}

function SearchPageSkeleton() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
      <div className="mx-auto h-64 max-w-3xl animate-pulse rounded-[2rem] bg-white/60" />
      <div className="mt-12 rounded-[2rem] bg-white px-4 py-6 shadow-sm shadow-black/5 ring-1 ring-black/[0.04] sm:px-6 lg:px-8">
        <div className="grid grid-cols-2 gap-x-4 gap-y-8 md:grid-cols-3 md:gap-y-10 lg:grid-cols-4">
        {Array.from({ length: 10 }).map((_, index) => (
          <ProductCardSkeleton key={index} />
        ))}
        </div>
      </div>
    </div>
  );
}
