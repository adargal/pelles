import type { ComparisonResponse } from '../types';
import { StoreCard } from './StoreCard';
import { ItemRow } from './ItemRow';

interface ComparisonResultsProps {
  comparison: ComparisonResponse;
  onOverride: (itemQuery: string, storeId: string, productId: string) => void;
  onReset: () => void;
}

export function ComparisonResults({ comparison, onOverride, onReset }: ComparisonResultsProps) {
  const storeIds = comparison.stores.map((s) => s.store_id);

  // Check if any store meets minimum coverage
  const hasRecommendation = comparison.stores.some((s) => s.is_recommended);

  return (
    <div className="w-full max-w-6xl mx-auto">
      {/* Store summary cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        {comparison.stores.map((store) => (
          <StoreCard key={store.store_id} store={store} />
        ))}
      </div>

      {!hasRecommendation && (
        <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <p className="text-yellow-800">
            אף חנות לא עומדת בסף המינימלי של מוצרים שנמצאו. בדוק את הפריטים שלא נמצאו.
          </p>
        </div>
      )}

      {/* Disclaimer */}
      <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <p className="text-sm text-blue-800">
          המחירים המוצגים הם אינדיקטיביים ועשויים להשתנות. המערכת משווה מחירים רגילים בלבד,
          ללא מבצעים או הנחות מועדון.
        </p>
      </div>

      {/* Item comparison table */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div className="p-4 bg-gray-50 border-b border-gray-200">
          <div
            className="grid gap-4 font-medium text-gray-700"
            style={{ gridTemplateColumns: `200px repeat(${storeIds.length}, 1fr)` }}
          >
            <div>פריט</div>
            {comparison.stores.map((store) => (
              <div key={store.store_id}>{store.store_name}</div>
            ))}
          </div>
        </div>

        <div className="p-4">
          {comparison.items.map((item) => (
            <ItemRow
              key={item.query}
              item={item}
              storeIds={storeIds}
              onOverride={onOverride}
            />
          ))}
        </div>
      </div>

      {/* Reset button */}
      <div className="mt-6 text-center">
        <button
          onClick={onReset}
          className="px-6 py-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
        >
          השוואה חדשה
        </button>
      </div>
    </div>
  );
}
