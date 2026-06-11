"use client";

import Image from "next/image";
import { ImagePlus, Loader2, PackagePlus } from "lucide-react";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { createProduct } from "@/services/products";
import { uploadImageToCloudinary } from "@/services/cloudinaryClient";
import { getApiErrorMessage } from "@/services/apiClient";
import type { ProductCreatePayload } from "@/types/product";

type FormValues = Omit<ProductCreatePayload, "article_id" | "image_url">;

const fieldLabels: Array<[keyof FormValues, string, "input" | "textarea"]> = [
  ["prod_name", "Product Name", "input"],
  ["detail_desc", "Detail Description", "textarea"],
  ["product_type_name", "Product Type", "input"],
  ["colour_group_name", "Color Group", "input"],
  ["graphical_appearance_name", "Graphical Appearance", "input"],
  ["index_name", "Index Name", "input"],
];

export function AdminProductForm() {
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormValues>({
    defaultValues: {
      prod_name: "",
      detail_desc: "",
      product_type_name: "",
      colour_group_name: "",
      graphical_appearance_name: "",
      index_name: "",
    },
  });

  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  function handleImageChange(file: File | null) {
    setImageFile(file);
    if (!file) {
      setPreviewUrl(null);
      return;
    }

    const objectUrl = URL.createObjectURL(file);
    setPreviewUrl(objectUrl);
  }

  async function onSubmit(values: FormValues) {
    if (!imageFile) {
      toast.error("Please choose a product image.");
      return;
    }

    setSubmitting(true);
    try {
      const imageUrl = await uploadImageToCloudinary(imageFile);
      const result = await createProduct({
        ...values,
        image_url: imageUrl,
      });
      toast.success(`Inserted ${result.article_id}`);
      reset();
      handleImageChange(null);
    } catch (error) {
      toast.error(getApiErrorMessage(error));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      className="grid gap-6 rounded-[2rem] bg-white/75 p-5 shadow-xl shadow-black/5 ring-1 ring-black/[0.04] backdrop-blur lg:grid-cols-[0.85fr_1.15fr] lg:p-8"
    >
      <label className="group relative flex min-h-[460px] cursor-pointer flex-col items-center justify-center overflow-hidden rounded-[1.5rem] border border-dashed border-black/15 bg-[#eee7dc] text-center transition hover:border-black/35">
        {previewUrl ? (
          <Image
            src={previewUrl}
            alt="Product preview"
            fill
            sizes="(min-width: 1024px) 35vw, 100vw"
            className="object-cover"
          />
        ) : (
          <div className="px-8">
            <ImagePlus className="mx-auto mb-4 text-black/35" size={42} />
            <p className="text-lg font-semibold text-[#111111]">
              Upload product image
            </p>
            <p className="mt-2 text-sm leading-6 text-black/50">
              Preview locally first. The image uploads to Cloudinary only when
              you submit.
            </p>
          </div>
        )}
        <input
          type="file"
          accept="image/*"
          className="sr-only"
          onChange={(event) => handleImageChange(event.target.files?.[0] ?? null)}
        />
      </label>

      <div className="grid gap-4">
        {fieldLabels.map(([name, label, kind]) => (
          <label key={name} className="block">
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-black/45">
              {label}
            </span>
            {kind === "textarea" ? (
              <textarea
                rows={5}
                {...register(name, { required: `${label} is required.` })}
                className="mt-2 w-full resize-none rounded-2xl border border-black/10 bg-white px-4 py-3 text-sm text-[#111111] outline-none transition focus:border-black/35"
              />
            ) : (
              <input
                {...register(name, { required: `${label} is required.` })}
                className="mt-2 h-12 w-full rounded-full border border-black/10 bg-white px-4 text-sm text-[#111111] outline-none transition focus:border-black/35"
              />
            )}
            {errors[name]?.message ? (
              <span className="mt-1 block text-xs text-red-600">
                {errors[name]?.message}
              </span>
            ) : null}
          </label>
        ))}

        <button
          type="submit"
          disabled={submitting}
          className="mt-3 inline-flex h-12 items-center justify-center gap-2 rounded-full bg-gradient-to-r from-[#111111] to-[#4a3427] px-6 text-sm font-semibold text-white shadow-lg shadow-black/10 transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {submitting ? <Loader2 className="animate-spin" size={18} /> : <PackagePlus size={18} />}
          {submitting ? "Creating Product..." : "Create Product"}
        </button>
      </div>
    </form>
  );
}
