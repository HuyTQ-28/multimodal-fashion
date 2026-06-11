"use client";

import { Heart, ShoppingBag } from "lucide-react";
import { motion } from "framer-motion";
import Image from "next/image";
import { MouseEvent } from "react";
import { toast } from "sonner";

import { ActionButton } from "@/components/ActionButton";
import { getProductImageUrl } from "@/services/imageUrl";
import type { Product } from "@/types/product";

type ProductCardProps = {
  product: Product;
  onOpenDetails: (product: Product) => void;
  onInteract: (product: Product, actionType: "click" | "like" | "add_to_cart") => Promise<void>;
  pendingKey: string | null;
};

export function ProductCard({
  product,
  onOpenDetails,
  onInteract,
  pendingKey,
}: ProductCardProps) {
  async function handleOpen() {
    onOpenDetails(product);
    await onInteract(product, "click").catch(() => undefined);
  }

  async function handleAction(
    event: MouseEvent<HTMLButtonElement>,
    actionType: "like" | "add_to_cart",
  ) {
    event.stopPropagation();
    try {
      await onInteract(product, actionType);
      toast.success(actionType === "like" ? "Preference updated" : "Cart signal added");
    } catch {
      toast.error("Could not update preferences.");
    }
  }

  const imageUrl = getProductImageUrl(product.image_url, { width: 420, quality: 70 });

  return (
    <motion.article
      whileHover={{ y: -2 }}
      onClick={handleOpen}
      className="group mx-auto w-full max-w-[245px] cursor-pointer overflow-hidden rounded-[1rem] bg-white shadow-sm shadow-black/5 ring-1 ring-black/[0.04] transition hover:shadow-lg hover:shadow-black/10"
    >
      <div className="relative aspect-[6/7] overflow-hidden bg-[#ede7dc]">
        <Image
          src={imageUrl}
          alt={product.prod_name || product.article_id}
          fill
          sizes="(min-width: 1280px) 20vw, (min-width: 768px) 33vw, 50vw"
          className="object-cover transition duration-700 group-hover:scale-105"
          unoptimized
        />
      </div>

      <div className="p-2">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <h3 className="line-clamp-1 text-xs font-semibold text-[#111111]">
              {product.prod_name || "Untitled item"}
            </h3>
            <p className="mt-0.5 line-clamp-1 text-[9px] uppercase tracking-[0.14em] text-black/45">
              {product.product_type_name || product.index_name || product.article_id}
            </p>
          </div>
          {typeof product.score === "number" ? (
            <span className="shrink-0 rounded-full bg-black/[0.04] px-1.5 py-0.5 text-[9px] text-black/55">
              {product.score.toFixed(2)}
            </span>
          ) : null}
        </div>

        <div className="mt-2 grid grid-cols-2 gap-1">
          <ActionButton
            type="button"
            icon={<Heart size={13} />}
            label="Love"
            className="h-7 px-1.5 text-[10px]"
            disabled={pendingKey === `${product.article_id}:like`}
            onClick={(event) => handleAction(event, "like")}
          />
          <ActionButton
            type="button"
            icon={<ShoppingBag size={13} />}
            label="Cart"
            tone="dark"
            className="h-7 px-1.5 text-[10px]"
            disabled={pendingKey === `${product.article_id}:add_to_cart`}
            onClick={(event) => handleAction(event, "add_to_cart")}
          />
        </div>
      </div>
    </motion.article>
  );
}
