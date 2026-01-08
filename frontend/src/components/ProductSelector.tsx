import { useState } from 'react';
import type { Product } from '../types';
import { ImageModal } from './ImageModal';

interface ProductSelectorProps {
  alternatives: Product[];
  onSelect: (productId: string) => void;
  onClose: () => void;
}

export function ProductSelector({ alternatives, onSelect, onClose }: ProductSelectorProps) {
  const [enlargedImage, setEnlargedImage] = useState<{ url: string; alt: string } | null>(null);

  if (alternatives.length === 0) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
          <h3 className="text-lg font-bold mb-4">אין חלופות זמינות</h3>
          <button
            onClick={onClose}
            className="w-full py-2 bg-gray-200 rounded hover:bg-gray-300"
          >
            סגור
          </button>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-6 max-w-lg w-full mx-4 max-h-[80vh] overflow-y-auto">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-bold">בחר מוצר חלופי</h3>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700 text-2xl"
            >
              &times;
            </button>
          </div>

          <div className="space-y-3">
            {alternatives.map((product) => (
              <div
                key={product.id}
                className="w-full p-4 border rounded-lg hover:bg-gray-50 text-right flex gap-4"
              >
                {product.image_url && (
                  <img
                    src={product.image_url}
                    alt={product.name}
                    className="w-16 h-16 object-contain cursor-pointer hover:opacity-80 transition-opacity"
                    onClick={() => setEnlargedImage({ url: product.image_url!, alt: product.name })}
                  />
                )}
                <button
                  className="flex-1 text-right"
                  onClick={() => onSelect(product.id)}
                >
                  <p className="font-medium">{product.name}</p>
                  {product.size_descriptor && (
                    <p className="text-sm text-gray-500">{product.size_descriptor}</p>
                  )}
                  <p className="text-lg font-bold text-blue-600 mt-1">
                    {product.price.toFixed(2)} ₪
                  </p>
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>

      {enlargedImage && (
        <ImageModal
          imageUrl={enlargedImage.url}
          alt={enlargedImage.alt}
          onClose={() => setEnlargedImage(null)}
        />
      )}
    </>
  );
}
