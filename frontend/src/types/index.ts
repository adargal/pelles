export type ConfidenceLevel = 'high' | 'medium' | 'low';

export interface Product {
  id: string;
  store_id: string;
  name: string;
  price: number;
  url: string | null;
  image_url: string | null;
  size_descriptor: string | null;
  fetched_at: string;
}

export interface StoreMatch {
  product: Product | null;
  confidence: ConfidenceLevel | null;
  alternatives: Product[];
  warning: string | null;
  match_score: number;
}

export interface ItemMatch {
  query: string;
  matches: Record<string, StoreMatch>;
}

export interface StoreSummary {
  store_id: string;
  store_name: string;
  total_price: number;
  matched_count: number;
  missing_count: number;
  warned_count: number;
  is_recommended: boolean;
  as_of: string | null;
}

export interface ComparisonResponse {
  comparison_id: string;
  stores: StoreSummary[];
  items: ItemMatch[];
}

export interface ComparisonRequest {
  items: string[];
}

export interface OverrideRequest {
  item_query: string;
  store_id: string;
  product_id: string;
}
