"use client";

import { useState } from "react";

import { EmptyState } from "@/components/EmptyState";
import { ProductCard } from "@/components/ProductCard";
import { ProductCardSkeleton } from "@/components/ProductCardSkeleton";
import { ProductDetailModal } from "@/components/ProductDetailModal";
import { useProductInteractions } from "@/hooks/useProductInteractions";
import { useSessionId } from "@/hooks/useSessionId";
import type { Product } from "@/types/product";

type ProductGridProps = {
  products?: Product[];
  loading?: boolean;
  emptyTitle?: string;
  emptyDescription?: string;
};

export function ProductGrid({
  products = [],
  loading = false,
  emptyTitle = "No products found",
  emptyDescription = "Try another search or refresh your recommendations.",
}: ProductGridProps) {
  const sessionId = useSessionId();
  const { pendingKey, recordInteraction } = useProductInteractions(sessionId);
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);

  if (loading) {
    return (
      <div className="grid grid-cols-2 gap-x-4 gap-y-8 md:grid-cols-3 md:gap-y-10 lg:grid-cols-4">
        {Array.from({ length: 8 }).map((_, index) => (
          <ProductCardSkeleton key={index} />
        ))}
      </div>
    );
  }

  if (products.length === 0) {
    return <EmptyState title={emptyTitle} description={emptyDescription} />;
  }

  return (
    <>
      <div className="grid grid-cols-2 gap-x-4 gap-y-8 md:grid-cols-3 md:gap-y-10 lg:grid-cols-4">
        {products.map((product) => (
          <ProductCard
            key={product.article_id}
            product={product}
            onOpenDetails={setSelectedProduct}
            onInteract={recordInteraction}
            pendingKey={pendingKey}
          />
        ))}
      </div>

      <ProductDetailModal
        product={selectedProduct}
        open={selectedProduct !== null}
        onClose={() => setSelectedProduct(null)}
        onLike={(product) => recordInteraction(product, "like")}
        onAddToCart={(product) => recordInteraction(product, "add_to_cart")}
      />
    </>
  );
}
