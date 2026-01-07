import type { StoreSummary } from '../types';

interface StoreCardProps {
  store: StoreSummary;
}

export function StoreCard({ store }: StoreCardProps) {
  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'לא ידוע';
    const date = new Date(dateStr);
    return date.toLocaleDateString('he-IL', {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div
      className={`p-6 rounded-lg border-2 ${
        store.is_recommended
          ? 'border-green-500 bg-green-50'
          : 'border-gray-200 bg-white'
      }`}
    >
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-xl font-bold">{store.store_name}</h3>
          {store.is_recommended && (
            <span className="inline-block mt-1 px-2 py-1 bg-green-500 text-white text-xs font-medium rounded">
              הכי זול
            </span>
          )}
        </div>
        <div className="text-left">
          <p className="text-3xl font-bold text-gray-900">
            {store.total_price.toFixed(2)} <span className="text-lg">₪</span>
          </p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 text-sm">
        <div className="text-center p-2 bg-gray-100 rounded">
          <p className="font-medium text-green-600">{store.matched_count}</p>
          <p className="text-gray-500">נמצאו</p>
        </div>
        <div className="text-center p-2 bg-gray-100 rounded">
          <p className="font-medium text-red-600">{store.missing_count}</p>
          <p className="text-gray-500">חסרים</p>
        </div>
        <div className="text-center p-2 bg-gray-100 rounded">
          <p className="font-medium text-yellow-600">{store.warned_count}</p>
          <p className="text-gray-500">אזהרות</p>
        </div>
      </div>

      <p className="mt-4 text-xs text-gray-400 text-center">
        נכון ל: {formatDate(store.as_of)}
      </p>
    </div>
  );
}
