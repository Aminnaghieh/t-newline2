import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import FiltersBar from './components/FiltersBar';
import ProductCard from './components/ProductCard';
import ShopCard from './components/ShopCard';
import MapView from './components/MapView';
import ChatPanel from './components/ChatPanel';
import VerificationModal from './components/VerificationModal';
import {
  Store,
  Package,
  Map as MapIcon,
  MessageSquare,
  Sparkles,
  AlertCircle,
  TrendingDown,
  Layers,
  ArrowRight,
} from 'lucide-react';

export default function App() {
  // Session & Step State
  const [sessionId, setSessionId] = useState('');
  const [currentStep, setCurrentStep] = useState('greeting');

  // User Location State (Default: Tehran - Jomhouri / Charsou / Aladdin)
  const [userLocation, setUserLocation] = useState({
    lat: 35.695,
    lon: 51.406,
    name: 'جمهوری / چارسو / علاءالدین',
  });
  const [isDetectingLocation, setIsDetectingLocation] = useState(false);

  // Chat State
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content:
        'سلام! 👋 من **تُرب‌گرد** هستم، دستیار هوشمند ایجنتیک شما برای **خرید حضوری در پاساژها و فروشگاه‌های تهران**.\n\nچه محصولی مدنظرتونه؟ می‌توانید بنویسید (مثلاً «کتونی پیاده‌روی تا ۳ میلیون با اسنپ‌پی») یا از دسته‌های پیشنهادی زیر انتخاب کنید.',
    },
  ]);
  const [suggestions, setSuggestions] = useState([
    'کفش کتونی نایک',
    'گوشی سامسونگ اقساطی',
    'لپ‌تاپ ایسوس',
    'ساعت هوشمند',
    'هدفون بلوتوثی',
  ]);
  const [isLoading, setIsLoading] = useState(false);

  // Results State
  const [products, setProducts] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [shops, setShops] = useState([]);
  const [selectedShop, setSelectedShop] = useState(null);

  // Filters State
  const [filters, setFilters] = useState({
    onlyOpen: false,
    bnplProvider: '',
    onlyMalls: false,
    maxBudget: 0,
    radiusKm: 5.0,
  });

  // Verification & Alternative State
  const [verificationShop, setVerificationShop] = useState(null);
  const [isVerificationOpen, setIsVerificationOpen] = useState(false);
  const [verifiedStatusMap, setVerifiedStatusMap] = useState({});

  // Active view tab (especially for mobile/responsive)
  // Default to 'products' because on first load we only have products –
  // showing an empty shop list is confusing.
  const [activeTab, setActiveTab] = useState('products'); // 'shops' | 'products' | 'map' | 'chat'

  // Initialize session and default product search
  useEffect(() => {
    // Initial fetch of popular products (e.g. sneakers) to populate UI immediately!
    fetchProducts('کفش کتونی');
  }, []);

  const fetchProducts = async (query = 'کتونی') => {
    try {
      const res = await fetch(`/api/products/search?q=${encodeURIComponent(query)}&limit=8`);
      const data = await res.json();
      if (data.products && data.products.length > 0) {
        setProducts(data.products);
      }
    } catch (err) {
      console.error('Failed to fetch initial products', err);
    }
  };

  // Detect GPS Location
  const handleDetectLocation = () => {
    if (!navigator.geolocation) {
      alert('مرورگر شما از موقعیت‌یابی پشتیبانی نمی‌کند.');
      return;
    }
    setIsDetectingLocation(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude, longitude } = pos.coords;
        setUserLocation({
          lat: latitude,
          lon: longitude,
          name: 'موقعیت فعلی شما (GPS)',
        });
        setIsDetectingLocation(false);
        // Refresh shops if product is selected
        if (selectedProduct) {
          fetchShopsForProduct(selectedProduct.product_id, latitude, longitude);
        }
      },
      (err) => {
        console.warn('Geolocation error', err);
        setIsDetectingLocation(false);
        alert('امکان دسترسی به لوکیشن GPS وجود نداشت. از لیست محله‌ها انتخاب کنید.');
      },
      { timeout: 8000 }
    );
  };

  const handleLocationSelect = (lat, lon, name) => {
    setUserLocation({ lat, lon, name });
    if (selectedProduct) {
      fetchShopsForProduct(selectedProduct.product_id, lat, lon);
    }
  };

  // Send message to agent backend
  const handleSendMessage = async (text, context = null) => {
    setIsLoading(true);
    const newMessages = [...messages, { role: 'user', content: text }];
    setMessages(newMessages);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          lat: userLocation.lat,
          lon: userLocation.lon,
          session_id: sessionId,
          context: context,
        }),
      });

      const data = await res.json();
      if (data.session_id) setSessionId(data.session_id);
      if (data.step) setCurrentStep(data.step);

      setMessages((prev) => [...prev, { role: 'assistant', content: data.message }]);
      if (data.suggestions) setSuggestions(data.suggestions);

      // Process cards returned by agent
      if (data.cards) {
        data.cards.forEach((card) => {
          if (card.type === 'product_list' && card.data?.products) {
            setProducts(card.data.products);
            setActiveTab('products');
          } else if (card.type === 'shop_list' && card.data?.shops) {
            setShops(card.data.shops);
            setActiveTab('shops');
          } else if (card.type === 'product_detail') {
            setSelectedProduct(card.data);
          }
        });
      }
    } catch (err) {
      console.error('Chat error', err);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'متأسفانه در برقراری ارتباط خطایی رخ داد. لطفاً دوباره تلاش کنید.',
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  // Fetch shops when a product is clicked
  const handleSelectProduct = async (product) => {
    setSelectedProduct(product);
    setCurrentStep('comparison');
    fetchShopsForProduct(product.product_id, userLocation.lat, userLocation.lon);
  };

  const fetchShopsForProduct = async (productId, lat, lon, overrideFilters = null) => {
    const activeFilters = overrideFilters || filters;
    setIsLoading(true);
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: '',
          lat,
          lon,
          session_id: sessionId,
          context: {
            action: 'find_shops',
            product_id: productId,
            radius_km: activeFilters.radiusKm,
            bnpl_provider: activeFilters.bnplProvider,
          },
        }),
      });
      const data = await res.json();
      if (data.cards) {
        const shopCard = data.cards.find((c) => c.type === 'shop_list');
        if (shopCard && shopCard.data?.shops) {
          setShops(shopCard.data.shops);
          setActiveTab('shops');

          // The server may have widened the radius (5 → 10 → 20 km) because
          // nothing was found nearby. Adopt the radius it actually applied,
          // otherwise the client-side filter would drop the very results
          // the agent just surfaced.
          const appliedRadius = data.filters?.radius_km;
          if (typeof appliedRadius === 'number' && appliedRadius > 0) {
            setFilters((prev) => ({ ...prev, radiusKm: appliedRadius }));
          }
        }
      }
      if (data.message) {
        setMessages((prev) => [...prev, { role: 'assistant', content: data.message }]);
      }
    } catch (err) {
      console.error('Failed to fetch shops', err);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: '❌ دریافت فروشگاه‌ها با خطا مواجه شد. لطفاً دوباره تلاش کنید.',
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  // Trigger Live Verification Modal
  const handleVerifyShop = (shop) => {
    setVerificationShop(shop);
    setIsVerificationOpen(true);
    setCurrentStep('verification');
  };

  // Called by the verification modal once the agent has a result, so the
  // shop card can display the "verified" badge.
  const handleVerificationResult = (shopId, status, updatedPrice) => {
    if (!shopId) return;
    setVerifiedStatusMap((prev) => ({
      ...prev,
      [shopId]: status,
    }));
    // Reflect a price change directly on the card
    if (status === 'price_changed' && updatedPrice) {
      setShops((prev) =>
        prev.map((s) =>
          s.shop_id === shopId
            ? { ...s, price_toman: updatedPrice, price_display: `${updatedPrice.toLocaleString('fa-IR')} تومان` }
            : s
        )
      );
    }
  };

  // Find Alternative Shops (fallback logic)
  const handleFindAlternatives = async (shop) => {
    if (!selectedProduct) return;
    setIsLoading(true);
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: '',
          lat: userLocation.lat,
          lon: userLocation.lon,
          session_id: sessionId,
          context: {
            action: 'find_alternatives',
            shop_id: shop.shop_id,
            product_id: selectedProduct.product_id,
          },
        }),
      });
      const data = await res.json();
      if (data.cards) {
        const shopCard = data.cards.find((c) => c.type === 'shop_list');
        if (shopCard && shopCard.data?.shops) {
          setShops(shopCard.data.shops);
          setActiveTab('shops');
        }
      }
      if (data.message) {
        setMessages((prev) => [...prev, { role: 'assistant', content: data.message }]);
      }
    } catch (err) {
      console.error('Failed to find alternatives', err);
    } finally {
      setIsLoading(false);
    }
  };

  // Filtered Shops
  const filteredShops = shops.filter((s) => {
    if (filters.onlyOpen && !s.is_open) return false;
    if (filters.bnplProvider && (!s.bnpl_providers || !s.bnpl_providers.includes(filters.bnplProvider)))
      return false;
    if (filters.onlyMalls && !s.mall_info?.mall_name) return false;
    if (filters.radiusKm && s.distance_m && s.distance_m > filters.radiusKm * 1000) return false;
    if (filters.maxBudget > 0 && s.price_toman && s.price_toman > filters.maxBudget) return false;
    return true;
  });

  return (
    <div className="min-h-screen bg-[#F8F9FA] text-gray-800 flex flex-col font-sans">
      {/* App Header */}
      <Header
        currentStep={currentStep}
        userLocation={userLocation}
        onLocationSelect={handleLocationSelect}
        onDetectLocation={handleDetectLocation}
        isDetectingLocation={isDetectingLocation}
      />

      {/* Main Content Layout */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-3 sm:p-4 grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left Column (Desktop 5 cols, Mobile full): Chat Assistant Panel */}
        <section className="lg:col-span-5 h-[520px] lg:h-[calc(100vh-140px)] flex flex-col">
          <ChatPanel
            messages={messages}
            onSendMessage={handleSendMessage}
            isLoading={isLoading}
            suggestions={suggestions}
            onSuggestionClick={(s) => handleSendMessage(s)}
            onReset={() => {
              setMessages([
                {
                  role: 'assistant',
                  content: 'گفتگو ریست شد. چه محصولی را می‌خواهید برای خرید حضوری بررسی کنیم؟',
                },
              ]);
              setCurrentStep('discovery');
              setSelectedProduct(null);
              setShops([]);
            }}
          />
        </section>

        {/* Right Column (Desktop 7 cols, Mobile full): Interactive Dashboard */}
        <section className="lg:col-span-7 flex flex-col space-y-3 h-auto lg:h-[calc(100vh-140px)] overflow-y-auto pr-0.5">
          {/* Active Product Banner if selected */}
          {selectedProduct && (
            <div className="bg-white rounded-xl border border-red-200 p-3 shadow-xs flex items-center justify-between gap-3 animate-fade-in">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-lg bg-gray-50 border border-gray-100 p-1 flex items-center justify-center shrink-0">
                  {selectedProduct.image_url ? (
                    <img
                      src={selectedProduct.image_url}
                      alt={selectedProduct.persian_title}
                      className="w-full h-full object-contain"
                    />
                  ) : (
                    <Package className="w-6 h-6 text-gray-400" />
                  )}
                </div>
                <div>
                  <span className="text-[10px] text-[#E8453C] font-bold block">کالای انتخابی:</span>
                  <h4 className="font-bold text-xs text-gray-900 line-clamp-1">
                    {selectedProduct.persian_title}
                  </h4>
                </div>
              </div>

              <button
                onClick={() => {
                  setSelectedProduct(null);
                  setActiveTab('products');
                }}
                className="text-xs text-gray-500 hover:text-gray-800 bg-gray-100 hover:bg-gray-200 px-2.5 py-1.5 rounded-lg transition-colors cursor-pointer shrink-0 font-medium"
              >
                تغییر کالا
              </button>
            </div>
          )}

          {/* Interactive Filters Bar */}
          <FiltersBar
            filters={filters}
            onFilterChange={setFilters}
            onApply={(next) => {
              // Re-query the server so radius / BNPL filters affect the
              // candidate set, not only the client-side rendering.
              // `next` is passed explicitly because `filters` is still the
              // previous state inside this render cycle.
              if (selectedProduct) {
                fetchShopsForProduct(
                  selectedProduct.product_id,
                  userLocation.lat,
                  userLocation.lon,
                  next
                );
              }
            }}
            totalResults={filteredShops.length}
          />

          {/* Dashboard Tab Navigation */}
          <div className="bg-white rounded-xl border border-gray-200 p-1 flex items-center gap-1 shadow-2xs">
            <button
              onClick={() => setActiveTab('shops')}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                activeTab === 'shops'
                  ? 'bg-[#E8453C] text-white shadow-xs'
                  : 'text-gray-600 hover:bg-gray-50'
              }`}
            >
              <Store className="w-4 h-4" />
              <span>فروشگاه‌های حضوری ({filteredShops.length})</span>
            </button>

            <button
              onClick={() => setActiveTab('products')}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                activeTab === 'products'
                  ? 'bg-[#E8453C] text-white shadow-xs'
                  : 'text-gray-600 hover:bg-gray-50'
              }`}
            >
              <Package className="w-4 h-4" />
              <span>کشف و مقایسه مدل‌ها ({products.length})</span>
            </button>

            <button
              onClick={() => setActiveTab('map')}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                activeTab === 'map'
                  ? 'bg-[#E8453C] text-white shadow-xs'
                  : 'text-gray-600 hover:bg-gray-50'
              }`}
            >
              <MapIcon className="w-4 h-4" />
              <span>نقشه و موقعیت</span>
            </button>
          </div>

          {/* Content Area Based on Active Tab */}
          <div className="flex-1 min-h-[350px]">
            {/* Loading skeletons */}
            {isLoading && (
              <div className="space-y-3" aria-busy="true" aria-label="در حال بارگذاری">
                {[0, 1, 2].map((i) => (
                  <div key={i} className="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
                    <div className="flex items-center gap-3">
                      <div className="skeleton h-4 w-40" />
                      <div className="skeleton h-4 w-16 rounded-full" />
                    </div>
                    <div className="skeleton h-3 w-full" />
                    <div className="flex items-center justify-between">
                      <div className="skeleton h-4 w-28" />
                      <div className="skeleton h-4 w-20" />
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Tab 1: Shops List */}
            {!isLoading && activeTab === 'shops' && (
              <div className="space-y-3">
                {filteredShops.length > 0 ? (
                  filteredShops.map((shop) => (
                    <ShopCard
                      key={shop.shop_id}
                      shop={shop}
                      onVerify={handleVerifyShop}
                      onFindAlternatives={handleFindAlternatives}
                      isVerified={Boolean(verifiedStatusMap[shop.shop_id])}
                      verifiedStatus={verifiedStatusMap[shop.shop_id]}
                      isSelected={selectedShop?.shop_id === shop.shop_id}
                      onSelect={(s) => setSelectedShop(s)}
                    />
                  ))
                ) : (
                  <div className="bg-white rounded-xl border border-gray-200 p-8 text-center space-y-3">
                    <Store className="w-10 h-10 text-gray-300 mx-auto" />
                    <h4 className="font-bold text-sm text-gray-700">
                      فروشگاهی با این فیلترها پیدا نشد
                    </h4>
                    <p className="text-xs text-gray-400 max-w-sm mx-auto">
                      پیشنهاد می‌کنیم فیلترهای اقساطی یا شعاع فاصله را تغییر دهید، یا از تب «کشف
                      مدل‌ها» کالای دیگری را انتخاب کنید.
                    </p>
                    <button
                      onClick={() => setActiveTab('products')}
                      className="bg-[#E8453C] text-white text-xs font-bold px-4 py-2 rounded-lg cursor-pointer"
                    >
                      مشاهده مدل‌های دیگر
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* Tab 2: Products Catalog */}
            {!isLoading && activeTab === 'products' && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {products.map((p) => (
                  <ProductCard
                    key={p.product_id}
                    product={p}
                    onSelect={handleSelectProduct}
                    isSelected={selectedProduct?.product_id === p.product_id}
                  />
                ))}
              </div>
            )}

            {/* Tab 3: Interactive Map */}
            {!isLoading && activeTab === 'map' && (
              <div className="h-[480px]">
                <MapView
                  shops={filteredShops}
                  userLocation={userLocation}
                  selectedShop={selectedShop}
                  onSelectShop={(s) => setSelectedShop(s)}
                />
              </div>
            )}
          </div>
        </section>
      </main>

      {/* Live Verification Modal */}
      <VerificationModal
        isOpen={isVerificationOpen}
        shop={verificationShop}
        product={selectedProduct}
        onClose={() => setIsVerificationOpen(false)}
        onFindAlternatives={handleFindAlternatives}
        onResult={handleVerificationResult}
      />
    </div>
  );
}
