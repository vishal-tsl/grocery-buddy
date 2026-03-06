/**
 * Product image URL provider – BasketSavings only.
 * Only images from BasketSavings (path or images.basketsavings.com URL) are shown.
 * All other sources (Google, OpenFoodFacts, etc.) are ignored.
 */
export type ImageSize = "xs" | "s" | "m" | "l";

const getImageSize = (size?: ImageSize): string | null => {
  switch (size) {
    case "xs":
      return "50";
    case "s":
      return "100";
    case "m":
      return "400";
    case "l":
      return "900";
    default:
      return null;
  }
};

const BASKETSAVINGS_IMAGES = "https://images.basketsavings.com/";
const BASKETSAVINGS_IMG = "https://img.basketsavings.com";

function buildBasketSavingsImageUrl(imageId: string, size?: ImageSize): string {
  const url = new URL(BASKETSAVINGS_IMG + "/");
  url.searchParams.append("imageId", imageId);
  url.searchParams.append("keepRatio", "1");
  const resize = getImageSize(size);
  if (resize) {
    url.searchParams.append("width", resize);
    url.searchParams.append("height", resize);
  }
  return url.href;
}

/** Returns a product image URL only for BasketSavings images; otherwise undefined. */
export const urlImageProvider = (
  imageUri?: string | null,
  size?: ImageSize
): string | undefined => {
  if (!imageUri) {
    return undefined;
  }

  const uri = `${imageUri}`.trim();

  // BasketSavings full URL → use img.basketsavings.com with path as imageId
  if (uri.startsWith(BASKETSAVINGS_IMAGES)) {
    const path = uri.slice(BASKETSAVINGS_IMAGES.length);
    if (path) return buildBasketSavingsImageUrl(path, size);
  }

  // Other absolute URLs → not used (BasketSavings only)
  if (uri.startsWith("https://") || uri.startsWith("http://")) {
    return undefined;
  }

  // Relative path / imageId (e.g. 2024/7/5/10/uuid) → img.basketsavings.com
  return buildBasketSavingsImageUrl(uri, size);
};
