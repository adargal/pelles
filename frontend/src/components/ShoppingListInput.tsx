import { useState } from 'react';

interface ShoppingListInputProps {
  onCompare: (items: string[]) => void;
  isLoading: boolean;
}

export function ShoppingListInput({ onCompare, isLoading }: ShoppingListInputProps) {
  const [text, setText] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const items = text
      .split('\n')
      .map((line) => line.trim())
      .filter((line) => line.length > 0);

    if (items.length > 0) {
      onCompare(items);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl mx-auto">
      <div className="mb-4">
        <label htmlFor="shopping-list" className="block text-lg font-medium text-gray-700 mb-2">
          רשימת קניות
        </label>
        <textarea
          id="shopping-list"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="הכניסו פריט אחד בכל שורה, לדוגמה:&#10;חלב&#10;לחם&#10;ביצים&#10;גבינה צהובה"
          className="w-full h-64 p-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none text-right"
          dir="rtl"
          disabled={isLoading}
        />
      </div>

      <div className="flex justify-between items-center">
        <p className="text-sm text-gray-500">
          המחירים עשויים להשתנות. הנתונים מתעדכנים אחת לשבוע.
        </p>
        <button
          type="submit"
          disabled={isLoading || text.trim().length === 0}
          className="px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
        >
          {isLoading ? 'מחפש...' : 'השווה מחירים'}
        </button>
      </div>
    </form>
  );
}
