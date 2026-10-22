import React, { useState, useEffect } from 'react';
import {
  PhoneCall,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Repeat,
  X,
  Store,
  Clock,
  Sparkles,
  ArrowLeft,
  Navigation,
} from 'lucide-react';

export default function VerificationModal({
  shop,
  product,
  isOpen,
  onClose,
  onFindAlternatives,
  onResult,
}) {
  const [phase, setPhase] = useState('calling'); // 'calling' | 'result'
  const [outcome, setOutcome] = useState(null); // 'confirmed' | 'price_changed' | 'no_response'
  const [updatedPrice, setUpdatedPrice] = useState(0);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!isOpen || !shop) return;

    setPhase('calling');
    setOutcome(null);
    setUpdatedPrice(0);
    setError('');

    // Ask the agent to contact the store and verify live stock/price.
    let cancelled = false;
    const run = async () => {
      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: '',
            context: {
              action: 'verify_shop',
              shop_id: shop.shop_id,
              product_id: product?.product_id || '',
            },
          }),
        });
        const data = await res.json();
        if (cancelled) return;

        const card = (data.cards || []).find((c) => c.type === 'verification');
        const status = card?.data?.status || 'no_response';

        setOutcome(status);
        let finalPrice = shop.price_toman || 0;
        if (status === 'price_changed') {
          // Prefer the price reported by the agent, fall back to the listed one
          finalPrice = card?.data?.new_price || shop.price_toman || 0;
          setUpdatedPrice(finalPrice);
        }
        setPhase('result');
        if (onResult) {
          onResult(shop.shop_id, status, finalPrice);
        }
      } catch (err) {
        if (cancelled) return;
        console.error('Verification failed', err);
        setError('ارتباط با سرور برقرار نشد. لطفاً دوباره تلاش کنید.');
        setPhase('result');
      }
    };

    run();
    return () => {
      cancelled = true;
    };
  }, [isOpen, shop, product?.product_id]);

  if (!isOpen || !shop) return null;

  const formatPrice = (val) => {
    if (!val || val <= 0) return 'نامشخص';
    return Number(val).toLocaleString('fa-IR');
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-md w-full shadow-2xl border border-gray-100 overflow-hidden animate-slide-up">
        {/* Modal Header */}
        <div className="bg-gradient-to-r from-gray-900 to-gray-800 text-white p-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-[#E8453C] flex items-center justify-center text-white">
              <PhoneCall className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-bold text-sm">استعلام هوشمند ایجنت با فروشگاه</h3>
              <p className="text-[11px] text-gray-300">{shop.name}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors cursor-pointer p-1"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5">
          {phase === 'calling' ? (
            /* Calling Animation */
            <div className="py-8 flex flex-col items-center justify-center text-center">
              <div className="relative w-20 h-20 mb-4 flex items-center justify-center">
                <div className="absolute inset-0 rounded-full bg-red-100 animate-ping opacity-75" />
                <div className="relative w-16 h-16 rounded-full bg-red-50 border-2 border-[#E8453C] flex items-center justify-center text-[#E8453C]">
                  <PhoneCall className="w-7 h-7 animate-bounce" />
                </div>
              </div>
              <h4 className="font-extrabold text-gray-900 text-sm mb-1">
                در حال برقراری تماس و استعلام زنده...
              </h4>
              <p className="text-xs text-gray-500 max-w-xs leading-relaxed">
                ایجنت در حال بررسی لحظه‌ای موجودی و راستی‌آزمایی قیمت کالا از فروشنده است.
              </p>
            </div>
          ) : (
            /* Result Screen */
            <div className="space-y-4">
              {error && (
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-amber-900">
                  <div className="flex items-center gap-2 mb-2 font-bold text-amber-800">
                    <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0" />
                    <span>استعلام انجام نشد</span>
                  </div>
                  <p className="text-xs text-amber-700 leading-relaxed">{error}</p>
                </div>
              )}

              {!error && outcome === 'confirmed' && (
                <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 text-emerald-900">
                  <div className="flex items-center gap-2 mb-2 font-bold text-emerald-800">
                    <CheckCircle className="w-5 h-5 text-emerald-600 shrink-0" />
                    <span>موجودی و قیمت قطعی تأیید شد!</span>
                  </div>
                  <p className="text-xs text-emerald-700 leading-relaxed mb-3">
                    فروشنده موجودی این کالا را در فروشگاه تأیید کرد و قیمت{' '}
                    <strong className="font-black text-emerald-900">
                      {formatPrice(shop.price_toman)} تومان
                    </strong>{' '}
                    معتبر است.
                  </p>
                  <div className="text-[11px] bg-white/80 rounded-lg p-2.5 border border-emerald-100 space-y-1">
                    <div>🕒 ساعت کاری امروز: {shop.hours_detail || shop.open_status}</div>
                    {shop.mall_guide && <div>🏬 موقعیت در پاساژ: {shop.mall_guide}</div>}
                  </div>
                </div>
              )}

              {!error && outcome === 'price_changed' && (
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-amber-900">
                  <div className="flex items-center gap-2 mb-2 font-bold text-amber-800">
                    <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0" />
                    <span>کالا موجود است؛ اما تغییر قیمت ثبت شد!</span>
                  </div>
                  <p className="text-xs text-amber-700 leading-relaxed mb-3">
                    قیمت ثبت‌شده در ترب {formatPrice(shop.price_toman)} تومان بود، اما فروشنده قیمت امروز
                    را اعلام کرد:
                  </p>
                  <div className="bg-white rounded-lg p-3 border border-amber-200 flex items-center justify-between">
                    <span className="text-xs text-gray-500">قیمت قطعی روز:</span>
                    <span className="font-black text-amber-800 text-sm">
                      {formatPrice(updatedPrice)} تومان
                    </span>
                  </div>
                </div>
              )}

              {!error && outcome === 'no_response' && (
                <div className="bg-rose-50 border border-rose-200 rounded-xl p-4 text-rose-900">
                  <div className="flex items-center gap-2 mb-2 font-bold text-rose-800">
                    <XCircle className="w-5 h-5 text-rose-600 shrink-0" />
                    <span>فروشگاه پاسخگو نیست یا بسته است!</span>
                  </div>
                  <p className="text-xs text-rose-700 leading-relaxed mb-3">
                    فروشگاه «{shop.name}» در حال حاضر پاسخ نداد. برای جلوگیری از اتلاف وقت شما در
                    مسیر، سیستم ایجنتیک فوراً فروشگاه‌های جایگزین باز در همین محدوده را پیدا کرده است.
                  </p>
                  <button
                    onClick={() => {
                      onClose();
                      onFindAlternatives(shop);
                    }}
                    className="w-full flex items-center justify-center gap-2 bg-[#E8453C] hover:bg-[#d03a31] text-white font-bold text-xs py-2.5 px-3 rounded-lg transition-colors cursor-pointer shadow-xs"
                  >
                    <Repeat className="w-4 h-4" />
                    <span>مشاهده نزدیک‌ترین فروشگاه‌های جایگزین باز</span>
                  </button>
                </div>
              )}

              {/* Action Buttons */}
              <div className="pt-2 flex items-center gap-2 justify-end">
                {outcome !== 'no_response' && (
                  <button
                    onClick={onClose}
                    className="flex-1 bg-[#E8453C] hover:bg-[#d03a31] text-white font-bold text-xs py-2.5 px-3 rounded-lg transition-colors cursor-pointer text-center"
                  >
                    متوجه شدم و آماده مراجعه‌ام
                  </button>
                )}
                <button
                  onClick={onClose}
                  className="bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold text-xs py-2.5 px-3 rounded-lg transition-colors cursor-pointer"
                >
                  بستن
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
