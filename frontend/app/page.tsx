"use client";

import { ArrowRight, RefreshCcw, Sparkles } from "lucide-react";
import Link from "next/link";

import { ProductGrid } from "@/components/ProductGrid";
import { RecommendationRail } from "@/components/RecommendationRail";
import { SearchBar } from "@/components/SearchBar";
import { useHomeFeed } from "@/hooks/useHomeFeed";
import { useRecommendations } from "@/hooks/useRecommendations";
import { useSessionId } from "@/hooks/useSessionId";
import { useInteractionCounter } from "@/hooks/useInteractionCounter";

export default function Home() {
  const sessionId = useSessionId();
  const { canRecommend, remainingInteractions } = useInteractionCounter();
  const homeFeed = useHomeFeed(20);
  const recommendations = useRecommendations(sessionId, 10, canRecommend);
  const personalizedProducts = recommendations.data ?? [];
  const homeProducts = homeFeed.data ?? [];
  const railProducts = personalizedProducts.length > 0 ? personalizedProducts : homeProducts.slice(0, 10);
  const gridProducts = homeProducts.slice(0, 20);
  const railLoading =
    homeFeed.isLoading || (canRecommend && !recommendations.data && recommendations.isLoading);
  const gridLoading = homeFeed.isLoading;

  return (
    <div className="mx-auto max-w-7xl px-4 pb-16 sm:px-6 lg:px-8">
      <section className="my-6 grid gap-10 rounded-[2rem] bg-[linear-gradient(135deg,#fff7f4_0%,#fff1ec_48%,#ffffff_100%)] px-5 py-12 shadow-sm shadow-[#ff6b5f14] lg:grid-cols-[1.1fr_0.9fr] lg:items-end lg:px-8 lg:py-16">
        <div>
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-black/10 bg-white/70 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-black/55">
            <Sparkles size={15} />
            Real-time fashion intelligence
          </div>
          <h1 className="font-serif text-6xl font-semibold leading-[0.95] tracking-tight text-[#111111] sm:text-7xl lg:text-8xl">
            Style that listens as you browse.
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-black/60">
            FREEDOM-RT shifts your feed with every quiet signal, from a glance
            to a favorite to a cart moment.
          </p>
        </div>

        <div className="rounded-[2rem] border border-white/70 bg-white/65 p-5 shadow-2xl shadow-black/5 backdrop-blur-xl">
          <SearchBar large />
          <Link
            href="/search?q=minimal%20jacket"
            className="mt-4 inline-flex items-center gap-2 px-2 text-sm font-medium text-black/55 transition hover:text-black"
          >
            Explore minimal jackets
            <ArrowRight size={16} />
          </Link>
        </div>
      </section>

      <RecommendationRail
        products={railProducts}
        loading={railLoading}
        personalized={canRecommend && personalizedProducts.length > 0}
        remainingInteractions={remainingInteractions}
      />

      <section className="bg-white py-6">
        <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-black/40">
              Initial catalog
            </p>
            <h2 className="mt-2 text-3xl font-semibold text-[#111111]">
              Browse the first 20 pieces
            </h2>
          </div>
          <button
            type="button"
            onClick={() => {
              void homeFeed.mutate();
              if (canRecommend) {
                void recommendations.mutate();
              }
            }}
            className="inline-flex items-center gap-2 rounded-full border border-black/10 bg-white/70 px-4 py-2 text-sm font-medium text-black/60 transition hover:bg-white hover:text-black"
          >
            <RefreshCcw size={16} />
            Refresh
          </button>
        </div>

        <ProductGrid
          products={gridProducts}
          loading={gridLoading}
          emptyTitle="No products yet"
          emptyDescription="The initial catalog feed is empty. Check the backend home feed or refresh."
        />
      </section>
    </div>
  );
}
