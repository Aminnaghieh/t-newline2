import React, { useState, useEffect, useRef } from 'react';
import Header from './components/Header';
import FiltersBar from './components/FiltersBar';
import ProductCard from './components/ProductCard';
import ShopCard from './components/ShopCard';
import MapView from './components/MapView';
import ChatPanel from './components/ChatPanel';
import VerificationModal from './components/VerificationModal';
import { Store, Package, Map as MapIcon, Search } from 'lucide-react';

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

  // Direct Catalog Search Input (Torob Search Bar)
  const [searchQuery, setSearchQuery] = useState('');

  // Chat State (supports inline Generative UI `cards` per message)
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content:
        'سلام! 👋 من **تُرب‌گرد** هستم، دستیار هوشمند **ترب** برای **خرید حضوری از پاساژها و فروشگاه‌های اطراف شما**.\n\nچه کالایی مدنظرتونه؟ می‌توانید نام کالا یا شرایط خریدتان را بنویسید (مثلاً «کتونی پیاده‌روی تا ۳ میلیون با اسنپ‌پی نزدیک چارسو») یا از ویجت‌های تعاملی زیر استفاده کنید.',
      cards: [],
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
  const [productsMeta, setProductsMeta] = useState({
    located: false,
    fallback: false,
    radiusUsed: null,
    total: null,
    totalCapped: false,
  });
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [shops, setShops] = useState([]);
  const [selectedShop, setSelectedShop] = useState(null);

  const lastQueryRef = useRef('کفش کتونی');
  const filtersRef = useRef(null);
  const productsTimerRef = useRef(null);

  // Filters State
  const [filters, setFilters] = useState({
    onlyOpen: false,
    bnplProvider: '',
    onlyMalls: false,
    maxBudget: 0,
    radiusKm: 5.0,
  });

  useEffect(() => {
    filtersRef.current = filters;
  }, [filters]);

  // Verification & Alternative State
  const [verificationShop, setVerificationShop] = useState(null);
  const [isVerificationOpen, setIsVerificationOpen] = useState(false);
  const [verifiedStatusMap, setVerifiedStatusMap] = useState({});

  // Active view tab
  const [activeTab, setActiveTab] = useState('products');

  useEffect(() => {
    fetchProducts('کفش کتونی', userLocation.lat, userLocation.lon);
  }, []);

  const fetchProducts = async (query = 'کتونی', lat = null, lon = null) => {
    lastQueryRef.current = query;
    try {
      const params = new URLSearchParams({ q: query, limit: '8' });
      const located = lat != null && lon != null;
      if (located) {
        params.set('lat', String(lat));
        params.set('lon', String(lon));
        params.set('radius_km', String(filtersRef.current?.radiusKm || 5));
        if (filtersRef.current?.maxBudget > 0) {
          params.set('max_price', String(filtersRef.current.maxBudget));
        }
        params.set('sort', 'distance');
      }
      const res = await fetch(`/api/products/search?${params.toString()}`);
      const data = await res.json();
      if (data.products && data.products.length > 0) {
        setProducts(data.products);
      } else if (located) {
        setProducts([]);
      }
      setProductsMeta({
        located,
        fallback: Boolean(data.fallback),
        radiusUsed: data.radius_used ?? null,
        total: data.total ?? null,
        totalCapped: Boolean(data.total_capped),
      });
    } catch (err) {
      console.error('Failed to fetch initial products', err);
    }
  };

  const scheduleProductsRefresh = (lat, lon) => {
    if (productsTimerRef.current) clearTimeout(productsTimerRef.current);
    productsTimerRef.current = setTimeout(() => {
      fetchProducts(lastQueryRef.current, lat, lon);
    }, 400);
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
        setFilters((prev) => ({ ...prev, radiusKm: 5.0 }));
        scheduleProductsRefresh(latitude, longitude);
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
    setFilters((prev) => ({ ...prev, radiusKm: 5.0 }));
    scheduleProductsRefresh(lat, lon);
    if (selectedProduct) {
      fetchShopsForProduct(selectedProduct.product_id, lat, lon);
    }
  };

  // Send message to agent backend (attaches `data.cards` to assistant message for Generative UI)
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

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.message,
          cards: data.cards || [],
        },
      ]);
      if (data.suggestions) setSuggestions(data.suggestions);

      if (data.cards) {
        data.cards.forEach((card) => {
          if (card.type === 'product_list' && card.data?.products) {
            setProducts(card.data.products);
            setActiveTab('products');
            lastQueryRef.current = card.data.query || lastQueryRef.current;
            setProductsMeta({
              located: true,
              fallback: card.data.products.some((p) => p.in_radius === false),
              radiusUsed: null,
              total: null,
              totalCapped: false,
            });
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
          cards: [],
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

          const appliedRadius = data.filters?.radius_km;
          if (typeof appliedRadius === 'number' && appliedRadius > 0) {
            setFilters((prev) => ({ ...prev, radiusKm: appliedRadius }));
          }
        }
      }
      if (data.message) {
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', content: data.message, cards: data.cards || [] },
        ]);
      }
    } catch (err) {
      console.error('Failed to fetch shops', err);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: '❌ دریافت فروشگاه‌ها با خطا مواجه شد. لطفاً دوباره تلاش کنید.',
          cards: [],
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

  const handleVerificationResult = (shopId, status, updatedPrice) => {
    if (!shopId) return;
    setVerifiedStatusMap((prev) => ({
      ...prev,
      [shopId]: status,
    }));
    if (status === 'price_changed' && updatedPrice) {
      setShops((prev) =>
        prev.map((s) =>
          s.shop_id === shopId
            ? {
                ...s,
                price_toman: updatedPrice,
                price_display: `${updatedPrice.toLocaleString('fa-IR')} تومان`,
              }
            : s
        )
      );
    }
  };

  // Find Alternative Shops
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
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', content: data.message, cards: data.cards || [] },
        ]);
      }
    } catch (err) {
      console.error('Failed to find alternatives', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDirectSearch = (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    fetchProducts(searchQuery.trim(), userLocation.lat, userLocation.lon);
    setActiveTab('products');
  };

  // Filtered Shops
  const filteredShops = shops.filter((s) => {
    if (filters.onlyOpen && !s.is_open) return false;
    if (
      filters.bnplProvider &&
      (!s.bnpl_providers || !s.bnpl_providers.includes(filters.bnplProvider))
    )
      return false;
    if (filters.onlyMalls && !s.mall_info?.mall_name) return false;
    if (filters.radiusKm && s.distance_m && s.distance_m > filters.radiusKm * 1000) return false;
    if (filters.maxBudget > 0 && s.price_toman && s.price_toman > filters.maxBudget) return false;
    return true;
  });

  return (
    <div className="min-h-screen bg-[#f2f3f5] text-[#333333] flex flex-col font-sans">
      {/* Torob Official Header */}
      <Header
        currentStep={currentStep}
        userLocation={userLocation}
        onLocationSelect={handleLocationSelect}
        onDetectLocation={handleDetectLocation}
        isDetectingLocation={isDetectingLocation}
      />

      {/* Main Content Layout */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-3 sm:p-4 grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Right Column in RTL (Desktop 5 cols): Torob Smart Assistant with Generative UI */}
        <section className="lg:col-span-5 h-[540px] lg:h-[calc(100vh-135px)] flex flex-col">
          <ChatPanel
            messages={messages}
            onSendMessage={handleSendMessage}
            isLoading={isLoading}
            suggestions={suggestions}
            onSuggestionClick={(s) => handleSendMessage(s)}
            products={products}
            shops={filteredShops}
            onSelectProduct={handleSelectProduct}
            onVerifyShop={handleVerifyShop}
            onSelectShop={(s) => {
              setSelectedShop(s);
              setActiveTab('map');
            }}
            onReset={() => {
              setMessages([
                {
                  role: 'assistant',
                  content:
                    'گفتگو ریست شد. چه کالایی را می‌خواهید در فروشگاه‌های حضوری ترب بررسی کنیم؟',
                  cards: [],
                },
              ]);
              setCurrentStep('discovery');
              setSelectedProduct(null);
              setShops([]);
            }}
          />
        </section>

        {/* Left Column in RTL (Desktop 7 cols): Torob Catalog, Sellers & Map */}
        <section className="lg:col-span-7 flex flex-col space-y-3 h-auto lg:h-[calc(100vh-135px)] overflow-y-auto pr-0.5">
          {/* Torob Classic Search Bar for Fast Catalog Lookup */}
          <form
            onSubmit={handleDirectSearch}
            className="bg-white rounded-xl border border-[#e6e6e6] p-2 shadow-[0_2px_8px_rgba(0,0,0,0.04)] flex items-center gap-2"
          >
            <div className="flex-1 relative flex items-center">
              <Search className="w-4 h-4 text-[#d73948] absolute right-3 pointer-events-none" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="جستجوی مستقیم نام کالا در ترب (مثلاً: آیفون ۱۶، کتونی نایک، گلکسی A55)..."
                className="w-full text-xs bg-[#f8f9fa] border border-[#e6e6e6] rounded-lg pr-9 pl-3 py-2 text-[#333333] placeholder-[#888888] outline-none focus:border-[#d73948] focus:bg-white transition-all font-medium"
              />
            </div>
            <button
              type="submit"
              className="bg-[#d73948] hover:bg-[#ae1f27] text-white text-xs font-bold px-4 py-2 rounded-lg transition-colors cursor-pointer shrink-0"
            >
              جستجو در ترب
            </button>
          </form>

          {/* Active Product Banner */}
          {selectedProduct && (
            <div className="bg-white rounded-xl border-2 border-[#d73948]/30 p-3.5 shadow-[0_2px_10px_rgba(215,57,72,0.08)] flex items-center justify-between gap-3 animate-fade-in">
              <div className="flex items-center gap-3">
                <div className="w-14 h-14 rounded-lg bg-white border border-[#e6e6e6] p-1 flex items-center justify-center shrink-0">
                  {selectedProduct.image_url ? (
                    <img
                      src={selectedProduct.image_url}
                      alt={selectedProduct.persian_title}
                      className="w-full h-full object-contain"
                    />
                  ) : (
                    <Package className="w-6 h-6 text-[#cccccc]" />
                  )}
                </div>
                <div>
                  <span className="text-[10px] text-[#d73948] font-extrabold block mb-0.5">
                    کالای انتخابی برای مقایسه فروشندگان حضوری:
                  </span>
                  <h4 className="font-extrabold text-xs sm:text-sm text-[#222222] line-clamp-1">
                    {selectedProduct.persian_title}
                  </h4>
                </div>
              </div>

              <button
                onClick={() => {
                  setSelectedProduct(null);
                  setActiveTab('products');
                }}
                className="text-xs text-[#d73948] hover:text-white bg-[#fff0f2] hover:bg-[#d73948] border border-[#f5c2c7] px-3 py-1.5 rounded-lg transition-colors cursor-pointer shrink-0 font-bold"
              >
                تغییر کالا
              </button>
            </div>
          )}

          {/* Torob Filters Bar */}
          <FiltersBar
            filters={filters}
            onFilterChange={setFilters}
            onApply={(next) => {
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

          {/* Torob Segmented Tab Bar */}
          <div className="bg-white rounded-xl border border-[#e6e6e6] p-1.5 flex items-center gap-1.5 shadow-[0_2px_8px_rgba(0,0,0,0.04)]">
            <button
              onClick={() => setActiveTab('shops')}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 px-3 rounded-lg text-xs font-extrabold transition-all cursor-pointer ${
                activeTab === 'shops'
                  ? 'bg-[#d73948] text-white shadow-2xs'
                  : 'text-[#555555] hover:bg-[#f8f9fa] hover:text-[#222222]'
              }`}
            >
              <Store className="w-4 h-4" />
              <span>فروشنده‌های حضوری ({filteredShops.length.toLocaleString('fa-IR')})</span>
            </button>

            <button
              onClick={() => setActiveTab('products')}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 px-3 rounded-lg text-xs font-extrabold transition-all cursor-pointer ${
                activeTab === 'products'
                  ? 'bg-[#d73948] text-white shadow-2xs'
                  : 'text-[#555555] hover:bg-[#f8f9fa] hover:text-[#222222]'
              }`}
            >
              <Package className="w-4 h-4" />
              <span>کشف و مقایسه کالاها ({products.length.toLocaleString('fa-IR')})</span>
            </button>

            <button
              onClick={() => setActiveTab('map')}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 px-3 rounded-lg text-xs font-extrabold transition-all cursor-pointer ${
                activeTab === 'map'
                  ? 'bg-[#d73948] text-white shadow-2xs'
                  : 'text-[#555555] hover:bg-[#f8f9fa] hover:text-[#222222]'
              }`}
            >
              <MapIcon className="w-4 h-4" />
              <span>نقشه اطراف من</span>
            </button>
          </div>

          {/* Content Area Based on Active Tab */}
          <div className="flex-1 min-h-[350px]">
            {isLoading && (
              <div className="space-y-3" aria-busy="true" aria-label="در حال بارگذاری">
                {[0, 1, 2].map((i) => (
                  <div
                    key={i}
                    className="bg-white rounded-xl border border-[#e6e6e6] p-4 space-y-3"
                  >
                    <div className="flex items-center gap-3">
                      <div className="skeleton h-4 w-44" />
                      <div className="skeleton h-4 w-20 rounded-full" />
                    </div>
                    <div className="skeleton h-3 w-full" />
                    <div className="flex items-center justify-between">
                      <div className="skeleton h-5 w-32" />
                      <div className="skeleton h-8 w-28 rounded-lg" />
                    </div>
                  </div>
                ))}
              </div>
            )}

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
                  <div className="bg-white rounded-xl border border-[#e6e6e6] p-8 text-center space-y-3">
                    <div className="w-12 h-12 rounded-full bg-[#fff0f2] text-[#d73948] flex items-center justify-center mx-auto">
                      <Store className="w-6 h-6" />
                    </div>
                    <h4 className="font-extrabold text-sm text-[#222222]">
                      فروشگاهی با این فیلترها در اطراف شما پیدا نشد
                    </h4>
                    <p className="text-xs text-[#888888] max-w-sm mx-auto leading-relaxed">
                      پیشنهاد می‌کنیم فیلترهای اقساطی یا شعاع فاصله را تغییر دهید، یا ابتدا از تب
                      «کشف و مقایسه کالاها» محصول موردنظرتان را انتخاب کنید.
                    </p>
                    <button
                      onClick={() => setActiveTab('products')}
                      className="bg-[#d73948] hover:bg-[#ae1f27] text-white text-xs font-bold px-5 py-2.5 rounded-lg cursor-pointer transition-colors"
                    >
                      مشاهده لیست کالاهای ترب
                    </button>
                  </div>
                )}
              </div>
            )}

            {!isLoading && activeTab === 'products' && (
              <div className="space-y-3">
                {productsMeta.located && productsMeta.total === 0 && products.length > 0 ? (
                  <div
                    data-testid="products-total-fallback"
                    className="text-[11px] text-[#b45309] font-bold bg-[#fff8e6] border border-[#fde68a] px-3 py-1.5 rounded-lg"
                  >
                    در محدوده شما محصولی پیدا نشد؛ نزدیک‌ترین فروشندگان ترب را نشان می‌دهیم
                  </div>
                ) : productsMeta.located && productsMeta.total != null && productsMeta.total > 0 ? (
                  <div
                    data-testid="products-total"
                    className="text-[11px] text-[#555555] font-bold flex items-center justify-between bg-white border border-[#e6e6e6] px-3 py-2 rounded-lg"
                  >
                    <span>
                      {productsMeta.totalCapped
                        ? `${productsMeta.total.toLocaleString('fa-IR')}+`
                        : productsMeta.total.toLocaleString('fa-IR')}{' '}
                      کالا در فروشگاه‌های حضوری محدوده شما پیدا شد
                    </span>
                    <span className="text-[#d73948]">مرتب‌سازی: نزدیک‌ترین به شما</span>
                  </div>
                ) : null}

                {productsMeta.fallback && products.length > 0 && (
                  <div
                    data-testid="products-fallback-banner"
                    className="bg-[#fff8e6] border border-[#fde68a] text-[#92400e] rounded-xl p-3 text-[11px] leading-relaxed font-medium"
                  >
                    ⚠️ برخی مدل‌ها در شعاع {productsMeta.radiusUsed ?? 5} کیلومتری شما فروشگاه
                    حضوری ندارند؛ نزدیک‌ترین گزینه‌ها نمایش داده شده‌اند. برای اطمینان از موجودی از
                    دکمه «استعلام زنده» استفاده کنید.
                  </div>
                )}

                {products.length > 0 ? (
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
                ) : productsMeta.located ? (
                  <div
                    data-testid="products-empty"
                    className="bg-white rounded-xl border border-[#e6e6e6] p-8 text-center space-y-3"
                  >
                    <Package className="w-10 h-10 text-[#cccccc] mx-auto" />
                    <h4 className="font-extrabold text-sm text-[#222222]">
                      در این محدوده کالایی پیدا نشد
                    </h4>
                    <p className="text-xs text-[#888888] max-w-sm mx-auto">
                      شعاع جستجو را افزایش دهید یا از بالای صفحه محله دیگری در تهران انتخاب کنید.
                    </p>
                  </div>
                ) : null}
              </div>
            )}

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
