"use client";

import { ChevronLeft, ChevronRight, Heart, ShoppingBag, Sparkles } from "lucide-react";
import { motion } from "framer-motion";
import Image from "next/image";
import { useRef, useState } from "react";
import { toast } from "sonner";

import { ProductCardSkeleton } from "@/components/ProductCardSkeleton";
import { ProductDetailModal } from "@/components/ProductDetailModal";
import { useProductInteractions } from "@/hooks/useProductInteractions";
import { useSessionId } from "@/hooks/useSessionId";
import { getProductImageUrl } from "@/services/imageUrl";
import type { Product } from "@/types/product";

type RecommendationRailProps = {
  products?: Product[];
  loading?: boolean;
  personalized?: boolean;
  remainingInteractions?: number;
};

export function RecommendationRail({
  products = [],
  loading = false,
  personalized = false,
  remainingInteractions = 0,
}: RecommendationRailProps) {
  const sessionId = useSessionId();
  const { recordInteraction } = useProductInteractions(sessionId);
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const railRef = useRef<HTMLDivElement | null>(null);

  function scrollRail(direction: "left" | "right") {
    railRef.current?.scrollBy({
      left: direction === "left" ? -620 : 620,
      behavior: "smooth",
    });
  }

  async function openProduct(product: Product) {
    setSelectedProduct(product);
    await recordInteraction(product, "click").catch(() => undefined);
  }

  async function handleAction(
    product: Product,
    actionType: "like" | "add_to_cart",
  ) {
    try {
      await recordInteraction(product, actionType);
      toast.success(actionType === "like" ? "Preference updated" : "Cart signal added");
    } catch {
      toast.error("Could not update preferences.");
    }
  }

  if (loading) {
    return (
      <div className="flex gap-4 overflow-hidden">
        {Array.from({ length: 5 }).map((_, index) => (
          <div key={index} className="min-w-[260px]">
            <ProductCardSkeleton compact />
          </div>
        ))}
      </div>
    );
  }

  const visibleProducts = products.slice(0, 10);

  if (visibleProducts.length === 0) {
    return null;
  }

  return (
    <section className="mb-12 overflow-hidden rounded-[2rem] border border-[#ffd8d1] bg-[linear-gradient(135deg,#fff8f6_0%,#ffe7e1_48%,#fff4ed_100%)] p-4 text-[#111111] shadow-xl shadow-[#ff6b5f1f] backdrop-blur sm:p-5">
      <div className="mb-4 flex items-center justify-between gap-4 px-1">
        <div>
          <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.22em] text-black/40">
            <Sparkles size={15} />
            Recommendation rail
          </p>
          <h2 className="mt-1 text-2xl font-semibold">
            {personalized ? "Because your taste is moving" : "Warm start picks"}
          </h2>
          {!personalized && remainingInteractions > 0 ? (
            <p className="mt-1 text-sm text-black/45">
              Interact {remainingInteractions} more times to unlock personalized recommendations.
            </p>
          ) : null}
        </div>
        <div className="flex items-center gap-2">
          <p className="hidden max-w-sm text-right text-sm leading-6 text-black/45 lg:block">
            {personalized
              ? "A live strip shaped by your latest clicks, loves, and cart signals."
              : "A lightweight preview before the live recommender starts."}
          </p>
          <button
            type="button"
            onClick={() => scrollRail("left")}
            className="flex size-10 items-center justify-center rounded-full border border-black/10 bg-white/80 text-black shadow-sm transition hover:bg-white"
            aria-label="Previous recommendations"
          >
            <ChevronLeft size={18} />
          </button>
          <button
            type="button"
            onClick={() => scrollRail("right")}
            className="flex size-10 items-center justify-center rounded-full bg-[#ff6b5f] text-white shadow-sm shadow-[#ff6b5f33] transition hover:bg-[#f2554b]"
            aria-label="Next recommendations"
          >
            <ChevronRight size={18} />
          </button>
        </div>
      </div>

      <div
        ref={railRef}
        className="flex snap-x gap-4 overflow-x-auto scroll-smooth pb-2 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      >
        {visibleProducts.map((product) => (
          <motion.article
            key={product.article_id}
            whileHover={{ y: -4 }}
            onClick={() => void openProduct(product)}
            className="group min-w-[calc((100%-3rem)/4)] basis-[calc((100%-3rem)/4)] snap-start cursor-pointer overflow-hidden rounded-[1.25rem] bg-white/95 shadow-sm shadow-black/5 ring-1 ring-black/[0.04] transition hover:shadow-xl hover:shadow-black/10 max-lg:min-w-[240px] max-lg:basis-[240px]"
          >
            <div className="relative aspect-[6/7] overflow-hidden bg-[#ede7dc]">
              <Image
                src={getProductImageUrl(product.image_url, { width: 420, quality: 70 })}
                alt={product.prod_name || product.article_id}
                fill
                sizes="(min-width: 1024px) 25vw, 240px"
                className="object-cover transition duration-700 group-hover:scale-105"
                unoptimized
              />
            </div>

            <div className="p-3">
              <h3 className="line-clamp-1 text-xs font-semibold">
                {product.prod_name || "Untitled item"}
              </h3>
              <p className="mt-1 line-clamp-1 text-[10px] uppercase tracking-[0.15em] text-black/40">
                {product.product_type_name || product.index_name || product.article_id}
              </p>
              <div className="mt-2 flex gap-1.5">
                <button
                  type="button"
                  onClick={(event) => {
                    event.stopPropagation();
                    void handleAction(product, "like");
                  }}
                  className="flex size-8 items-center justify-center rounded-full border border-black/10 bg-white text-black transition hover:bg-[#f7f4ef]"
                  aria-label="Like product"
                >
                  <Heart size={15} />
                </button>
                <button
                  type="button"
                  onClick={(event) => {
                    event.stopPropagation();
                    void handleAction(product, "add_to_cart");
                  }}
                  className="flex h-8 flex-1 items-center justify-center gap-1.5 rounded-full bg-[#ff6b5f] px-2 text-[11px] font-semibold text-white shadow-sm shadow-[#ff6b5f33] transition hover:bg-[#f2554b]"
                >
                  <ShoppingBag size={14} />
                  Cart
                </button>
              </div>
            </div>
          </motion.article>
        ))}
      </div>

      <ProductDetailModal
        product={selectedProduct}
        open={selectedProduct !== null}
        onClose={() => setSelectedProduct(null)}
        onLike={(product) => recordInteraction(product, "like")}
        onAddToCart={(product) => recordInteraction(product, "add_to_cart")}
      />
    </section>
  );
}
