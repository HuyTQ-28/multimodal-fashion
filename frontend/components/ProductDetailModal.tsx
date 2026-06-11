"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Heart, ShoppingBag, X } from "lucide-react";
import Image from "next/image";
import { useEffect } from "react";
import { toast } from "sonner";

import { ActionButton } from "@/components/ActionButton";
import { getProductImageUrl } from "@/services/imageUrl";
import type { Product } from "@/types/product";

type ProductDetailModalProps = {
  product: Product | null;
  open: boolean;
  onClose: () => void;
  onLike: (product: Product) => Promise<void>;
  onAddToCart: (product: Product) => Promise<void>;
};

const detailRows: Array<[keyof Product, string]> = [
  ["product_type_name", "Type"],
  ["colour_group_name", "Color"],
  ["graphical_appearance_name", "Pattern"],
  ["index_name", "Index"],
];

export function ProductDetailModal({
  product,
  open,
  onClose,
  onLike,
  onAddToCart,
}: ProductDetailModalProps) {
  useEffect(() => {
    if (!open) {
      return;
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }

    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [open, onClose]);

  async function handleLike() {
    if (!product) {
      return;
    }
    try {
      await onLike(product);
      toast.success("Preference updated");
    } catch {
      toast.error("Could not update preferences.");
    }
  }

  async function handleAddToCart() {
    if (!product) {
      return;
    }
    try {
      await onAddToCart(product);
      toast.success("Cart signal added");
    } catch {
      toast.error("Could not update preferences.");
    }
  }

  return (
    <AnimatePresence>
      {open && product ? (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 px-4 py-6 backdrop-blur-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
        >
          <motion.section
            role="dialog"
            aria-modal="true"
            aria-label={product.prod_name}
            className="relative grid max-h-[92vh] w-full max-w-5xl overflow-hidden rounded-[2rem] bg-[#f7f4ef] shadow-2xl shadow-black/30 md:grid-cols-[0.9fr_1.1fr]"
            initial={{ opacity: 0, scale: 0.95, y: 18 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 12 }}
            transition={{ type: "spring", stiffness: 240, damping: 24 }}
            onClick={(event) => event.stopPropagation()}
          >
            <button
              type="button"
              onClick={onClose}
              className="absolute right-4 top-4 z-10 flex size-10 items-center justify-center rounded-full bg-white/85 text-black shadow-sm backdrop-blur transition hover:bg-white"
              aria-label="Close product details"
            >
              <X size={18} />
            </button>

            <div className="relative min-h-[360px] bg-[#e7dfd2] md:min-h-[680px]">
              <Image
                src={getProductImageUrl(product.image_url, { width: 900, quality: 78 })}
                alt={product.prod_name || product.article_id}
                fill
                sizes="(min-width: 768px) 45vw, 100vw"
                className="object-cover"
                priority
                unoptimized
              />
            </div>

            <div className="overflow-y-auto px-6 py-8 sm:px-8 md:px-10">
              <p className="text-xs font-semibold uppercase tracking-[0.28em] text-black/45">
                Curated recommendation
              </p>
              <h2 className="mt-3 text-4xl font-semibold leading-tight text-[#111111] md:text-5xl">
                {product.prod_name || "Untitled item"}
              </h2>
              <p className="mt-5 max-w-xl text-base leading-7 text-black/60">
                {product.detail_desc || "No product description is available yet."}
              </p>

              <div className="mt-8 grid gap-3 sm:grid-cols-2">
                {detailRows.map(([key, label]) => (
                  <div
                    key={key}
                    className="rounded-2xl border border-black/5 bg-white/70 p-4"
                  >
                    <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-black/35">
                      {label}
                    </p>
                    <p className="mt-2 text-sm font-medium text-[#111111]">
                      {String(product[key] || "N/A")}
                    </p>
                  </div>
                ))}
              </div>

              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <ActionButton
                  type="button"
                  icon={<Heart size={17} />}
                  label="Favorite"
                  onClick={handleLike}
                />
                <ActionButton
                  type="button"
                  icon={<ShoppingBag size={17} />}
                  label="Add to Cart"
                  tone="accent"
                  onClick={handleAddToCart}
                />
              </div>
            </div>
          </motion.section>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
