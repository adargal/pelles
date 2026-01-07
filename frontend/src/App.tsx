import { useComparison } from './hooks/useComparison';
import { ShoppingListInput } from './components/ShoppingListInput';
import { ComparisonResults } from './components/ComparisonResults';

function App() {
  const { comparison, isLoading, error, compare, override, reset } = useComparison();

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-6">
          <h1 className="text-3xl font-bold text-gray-900 text-center">
            Pelles
          </h1>
          <p className="text-center text-gray-600 mt-1">
            השוואת מחירי סופרמרקט בישראל
          </p>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-6xl mx-auto px-4 py-8">
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        {!comparison ? (
          <ShoppingListInput onCompare={compare} isLoading={isLoading} />
        ) : (
          <ComparisonResults
            comparison={comparison}
            onOverride={override}
            onReset={reset}
          />
        )}

        {isLoading && (
          <div className="fixed inset-0 bg-black bg-opacity-30 flex items-center justify-center z-50">
            <div className="bg-white p-8 rounded-lg shadow-lg text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
              <p className="text-gray-700">מחפש מוצרים...</p>
              <p className="text-sm text-gray-500 mt-2">זה עשוי לקחת מספר שניות</p>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-auto">
        <div className="max-w-6xl mx-auto px-4 py-4 text-center text-sm text-gray-500">
          <p>המחירים הם אינדיקטיביים ולא מתעדכנים בזמן אמת.</p>
          <p className="mt-1">חנויות נתמכות: Shufersal, Super Hefer Large</p>
        </div>
      </footer>
    </div>
  );
}

export default App;
