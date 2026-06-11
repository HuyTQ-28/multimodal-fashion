type ProductCardSkeletonProps = {
  compact?: boolean;
};

export function ProductCardSkeleton({ compact = false }: ProductCardSkeletonProps) {
  return (
    <div className="animate-pulse overflow-hidden rounded-[1.1rem] bg-white/70 p-2 shadow-sm">
      <div
        className={`rounded-[0.85rem] bg-black/10 ${
          compact ? "aspect-[6/7]" : "aspect-[6/7]"
        }`}
      />
      <div className="mt-2.5 h-3.5 w-3/4 rounded-full bg-black/10" />
      <div className="mt-1.5 h-2.5 w-1/2 rounded-full bg-black/10" />
      <div className="mt-2 flex gap-1.5">
        <div className="h-8 flex-1 rounded-full bg-black/10" />
        <div className="h-8 flex-1 rounded-full bg-black/10" />
      </div>
    </div>
  );
}
