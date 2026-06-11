import { Sparkles } from "lucide-react";
import Link from "next/link";

export function Navbar() {
  return (
    <header className="sticky top-0 z-40 border-b border-black/5 bg-[#f7f4ef]/75 backdrop-blur-2xl">
      <div className="mx-auto flex max-w-7xl items-center gap-5 px-4 py-3 sm:px-6 lg:px-8">
        <Link
          href="/"
          className="flex items-center gap-2 text-sm font-semibold uppercase tracking-[0.24em] text-[#111111]"
        >
          <span className="flex size-9 items-center justify-center rounded-full bg-[#111111] text-white">
            <Sparkles size={16} />
          </span>
          FREEDOM-RT
        </Link>

        <nav className="ml-auto flex items-center gap-4 text-sm font-medium text-black/65">
          <Link className="transition hover:text-black" href="/">
            Home
          </Link>
          <Link className="transition hover:text-black" href="/search">
            Search
          </Link>
          <Link className="transition hover:text-black" href="/admin/add-product">
            Admin
          </Link>
        </nav>
      </div>
    </header>
  );
}
