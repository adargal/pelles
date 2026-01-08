import { useState } from 'react';
import type { ItemMatch, StoreMatch, ConfidenceLevel } from '../types';
import { ProductSelector } from './ProductSelector';
import { ImageModal } from './ImageModal';

interface ItemRowProps {
  item: ItemMatch;
  storeIds: string[];
  onOverride: (itemQuery: string, storeId: string, productId: string) => void;
}

function ConfidenceBadge({ confidence }: { confidence: ConfidenceLevel | null }) {
  if (!confidence) return null;

  const colors = {
    high: 'bg-green-100 text-green-800',
    medium: 'bg-yellow-100 text-yellow-800',
    low: 'bg-red-100 text-red-800',
  };

  const labels = {
    high: 'גבוה',
    medium: 'בינוני',
    low: 'נמוך',
  };

  return (
    <span className={`px-2 py-0.5 rounded text-xs ${colors[confidence]}`}>
      {labels[confidence]}
    </span>
  );
}

function StoreMatchCell({
  match,
  onChangeClick,
  onImageClick,
}: {
  match: StoreMatch;
  onChangeClick: () => void;
  onImageClick: (imageUrl: string, alt: string) => void;
}) {
  if (!match.product) {
    return (
      <div className="p-3 bg-gray-100 rounded text-center">
        <p className="text-gray-500 text-sm">לא נמצא</p>
        {match.alternatives.length > 0 && (
          <button
            onClick={onChangeClick}
            className="mt-1 text-xs text-blue-600 hover:underline"
          >
            בחר ידנית
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="p-3 bg-gray-50 rounded">
      <div className="flex gap-2 items-start">
        {match.product.image_url && (
          <img
            src={match.product.image_url}
            alt={match.product.name}
            className="w-12 h-12 object-contain cursor-pointer hover:opacity-80 transition-opacity"
            onClick={() => onImageClick(match.product!.image_url!, match.product!.name)}
          />
        )}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate" title={match.product.name}>
            {match.product.name}
          </p>
          {match.product.size_descriptor && (
            <p className="text-xs text-gray-500">{match.product.size_descriptor}</p>
          )}
          <div className="flex items-center gap-2 mt-1">
            <span className="font-bold text-blue-600">
              {match.product.price.toFixed(2)} ₪
            </span>
            <ConfidenceBadge confidence={match.confidence} />
          </div>
        </div>
      </div>

      {match.warning && (
        <p className="mt-2 text-xs text-yellow-700 bg-yellow-50 p-1 rounded">
          {match.warning}
        </p>
      )}

      {match.alternatives.length > 0 && (
        <button
          onClick={onChangeClick}
          className="mt-2 text-xs text-blue-600 hover:underline"
        >
          שנה בחירה
        </button>
      )}
    </div>
  );
}

export function ItemRow({ item, storeIds, onOverride }: ItemRowProps) {
  const [selectorOpen, setSelectorOpen] = useState<string | null>(null);
  const [enlargedImage, setEnlargedImage] = useState<{ url: string; alt: string } | null>(null);

  const handleSelect = (productId: string) => {
    if (selectorOpen) {
      onOverride(item.query, selectorOpen, productId);
      setSelectorOpen(null);
    }
  };

  const handleImageClick = (imageUrl: string, alt: string) => {
    setEnlargedImage({ url: imageUrl, alt });
  };

  return (
    <div className="border-b border-gray-200 py-4">
      <div className="grid gap-4" style={{ gridTemplateColumns: `200px repeat(${storeIds.length}, 1fr)` }}>
        <div className="font-medium text-gray-900 flex items-center">
          {item.query}
        </div>

        {storeIds.map((storeId) => {
          const match = item.matches[storeId];
          return (
            <StoreMatchCell
              key={storeId}
              match={match}
              onChangeClick={() => setSelectorOpen(storeId)}
              onImageClick={handleImageClick}
            />
          );
        })}
      </div>

      {selectorOpen && (
        <ProductSelector
          alternatives={item.matches[selectorOpen]?.alternatives || []}
          onSelect={handleSelect}
          onClose={() => setSelectorOpen(null)}
        />
      )}

      {enlargedImage && (
        <ImageModal
          imageUrl={enlargedImage.url}
          alt={enlargedImage.alt}
          onClose={() => setEnlargedImage(null)}
        />
      )}
    </div>
  );
}
