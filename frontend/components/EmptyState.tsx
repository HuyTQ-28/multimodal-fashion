import { SearchX } from "lucide-react";

type EmptyStateProps = {
  title: string;
  description: string;
};

export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div className="flex min-h-72 flex-col items-center justify-center rounded-[2rem] border border-dashed border-black/10 bg-white/50 px-6 text-center">
      <SearchX className="mb-4 text-black/35" size={34} />
      <h2 className="text-xl font-semibold text-[#111111]">{title}</h2>
      <p className="mt-2 max-w-md text-sm leading-6 text-black/55">
        {description}
      </p>
    </div>
  );
}
