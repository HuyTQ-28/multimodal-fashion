export type ActionType = "click" | "like" | "add_to_cart";

export type Product = {
  article_id: string;
  image_url: string;
  prod_name: string;
  detail_desc: string;
  product_type_name: string;
  colour_group_name: string;
  graphical_appearance_name: string;
  index_name: string;
  score?: number | null;
};

export type ProductCreatePayload = Omit<Product, "score" | "article_id"> & {
  article_id?: string;
};

export type InteractionPayload = {
  session_id: string;
  article_id: string;
  action_type: ActionType;
};

export type ProductMutationResult = {
  status: string;
  article_id: string;
  uuid: string;
};
