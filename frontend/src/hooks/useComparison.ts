import { useState, useCallback } from 'react';
import type { ComparisonResponse } from '../types';
import { compareItems, overrideMatch } from '../api/client';

interface UseComparisonReturn {
  comparison: ComparisonResponse | null;
  isLoading: boolean;
  error: string | null;
  compare: (items: string[]) => Promise<void>;
  override: (itemQuery: string, storeId: string, productId: string) => Promise<void>;
  reset: () => void;
}

export function useComparison(): UseComparisonReturn {
  const [comparison, setComparison] = useState<ComparisonResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const compare = useCallback(async (items: string[]) => {
    setIsLoading(true);
    setError(null);

    try {
      const result = await compareItems(items);
      setComparison(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      setComparison(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const override = useCallback(async (itemQuery: string, storeId: string, productId: string) => {
    if (!comparison) return;

    try {
      const result = await overrideMatch(
        comparison.comparison_id,
        itemQuery,
        storeId,
        productId
      );
      setComparison(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update selection');
    }
  }, [comparison]);

  const reset = useCallback(() => {
    setComparison(null);
    setError(null);
  }, []);

  return {
    comparison,
    isLoading,
    error,
    compare,
    override,
    reset,
  };
}
