import { AdminProductForm } from "@/components/AdminProductForm";

export default function AddProductPage() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
      <section className="mb-8 max-w-3xl">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-black/40">
          Cold-start pipeline
        </p>
        <h1 className="mt-3 font-serif text-5xl font-semibold leading-tight text-[#111111] sm:text-6xl">
          Add a new product to the recommendation graph.
        </h1>
        <p className="mt-4 text-base leading-7 text-black/55">
          Upload an image, fill the product metadata, and create both named
          vectors through the backend insertion flow.
        </p>
      </section>

      <AdminProductForm />
    </div>
  );
}
