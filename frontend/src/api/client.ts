import type { ComparisonRequest, ComparisonResponse, OverrideRequest } from '../types';

const API_BASE = '/api';

export async function compareItems(items: string[]): Promise<ComparisonResponse> {
  const response = await fetch(`${API_BASE}/compare`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ items } as ComparisonRequest),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || 'Failed to compare items');
  }

  return response.json();
}

export async function overrideMatch(
  comparisonId: string,
  itemQuery: string,
  storeId: string,
  productId: string
): Promise<ComparisonResponse> {
  const response = await fetch(`${API_BASE}/compare/${comparisonId}/override`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      item_query: itemQuery,
      store_id: storeId,
      product_id: productId,
    } as OverrideRequest),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || 'Failed to override selection');
  }

  return response.json();
}
