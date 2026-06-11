const CLOUDINARY_HOST = "res.cloudinary.com";

type ProductImageOptions = {
  width?: number;
  quality?: number;
};

export function getProductImageUrl(
  imageUrl: string | null | undefined,
  options: ProductImageOptions = {},
): string {
  if (!imageUrl) {
    return "/window.svg";
  }

  if (!imageUrl.includes(CLOUDINARY_HOST) || !imageUrl.includes("/upload/")) {
    return imageUrl;
  }

  const width = options.width ?? 420;
  const quality = options.quality ?? 72;
  const transform = `f_auto,q_${quality},c_fill,w_${width}`;

  return imageUrl.replace("/upload/", `/upload/${transform}/`);
}
