import { apiClient } from "@/services/apiClient";
import type {
  InteractionPayload,
  Product,
  ProductCreatePayload,
  ProductMutationResult,
} from "@/types/product";

export async function getHomeFeed(limit: number): Promise<Product[]> {
  const response = await apiClient.get<Product[]>("/api/v1/home", {
    params: { limit },
  });
  return response.data;
}

export async function getRecommendations(
  sessionId: string,
  limit: number,
): Promise<Product[]> {
  const response = await apiClient.get<Product[]>("/api/v1/recommendations", {
    params: { session_id: sessionId, limit },
  });
  return response.data;
}

export async function postInteraction(
  payload: InteractionPayload,
): Promise<void> {
  await apiClient.post("/api/v1/interactions", payload);
}

export async function searchProducts(
  query: string,
  limit: number,
): Promise<Product[]> {
  const response = await apiClient.get<Product[]>("/api/v1/search", {
    params: { q: query, limit },
  });
  return response.data;
}

export async function createProduct(
  payload: ProductCreatePayload,
): Promise<ProductMutationResult> {
  const response = await apiClient.post<ProductMutationResult>(
    "/api/v1/products",
    payload,
  );
  return response.data;
}
