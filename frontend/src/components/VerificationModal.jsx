import React, { useState, useEffect } from 'react';
import {
  PhoneCall,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Repeat,
  X,
  ShieldCheck,
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
      <div className="bg-white rounded-2xl max-w-md w-full shadow-2xl border border-[#e6e6e6] overflow-hidden animate-slide-up">
        {/* Torob Modal Header */}
        <div className="bg-white border-b border-[#e6e6e6] p-4 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-[#fff0f2] border border-[#f5c2c7] flex items-center justify-center text-[#d73948]">
              <PhoneCall className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <h3 className="font-extrabold text-sm text-[#222222]">
                  استعلام زنده موجودی و قیمت ترب
                </h3>
                <span className="bg-[#eff6ff] text-[#3468cc] text-[10px] font-bold px-1.5 py-0.2 rounded border border-[#bfdbfe] flex items-center gap-0.5">
                  <ShieldCheck className="w-2.5 h-2.5" />
                  <span>ضمانت ترب</span>
                </span>
              </div>
              <p className="text-[11px] text-[#888888] font-medium mt-0.5">{shop.name}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-[#888888] hover:text-[#222222] hover:bg-[#f2f3f5] rounded-lg transition-colors cursor-pointer p-1.5"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5">
          {phase === 'calling' ? (
            /* Calling Animation */
            <div className="py-8 flex flex-col items-center justify-center text-center">
              <div className="relative w-20 h-20 mb-4 flex items-center justify-center">
                <div className="absolute inset-0 rounded-full bg-[#fff0f2] animate-ping opacity-80" />
                <div className="relative w-16 h-16 rounded-full bg-[#fff0f2] border-2 border-[#d73948] flex items-center justify-center text-[#d73948]">
                  <PhoneCall className="w-7 h-7 animate-bounce" />
                </div>
              </div>
              <h4 className="font-extrabold text-[#222222] text-sm mb-1">
                در حال استعلام لحظه‌ای دستیار هوشمند ترب با فروشنده...
              </h4>
              <p className="text-xs text-[#888888] max-w-xs leading-relaxed">
                ایجنت ترب در حال بررسی موجودی فیزیکی کالا و تایید قیمت نهایی امروز در فروشگاه است.
              </p>
            </div>
          ) : (
            /* Result Screen */
            <div className="space-y-4">
              {error && (
                <div className="bg-[#fff8e6] border border-[#fde68a] rounded-xl p-4 text-[#92400e]">
                  <div className="flex items-center gap-2 mb-2 font-bold text-[#b45309]">
                    <AlertTriangle className="w-5 h-5 text-[#f59e0b] shrink-0" />
                    <span>استعلام انجام نشد</span>
                  </div>
                  <p className="text-xs text-[#92400e] leading-relaxed">{error}</p>
                </div>
              )}

              {!error && outcome === 'confirmed' && (
                <div className="bg-[#eefceb] border border-[#b7ebae] rounded-xl p-4 text-[#14532d]">
                  <div className="flex items-center gap-2 mb-2 font-extrabold text-[#248212]">
                    <CheckCircle className="w-5 h-5 text-[#16a34a] shrink-0" />
                    <span>موجودی و قیمت قطعی در فروشگاه تأیید شد!</span>
                  </div>
                  <p className="text-xs text-[#166534] leading-relaxed mb-3">
                    فروشنده موجودی این کالا را در مغازه تأیید کرد و قیمت ثبت‌شده در ترب{' '}
                    <strong className="font-black text-[#14532d]">
                      {formatPrice(shop.price_toman)} تومان
                    </strong>{' '}
                    کاملاً معتبر است.
                  </p>
                  <div className="text-[11px] bg-white rounded-lg p-3 border border-[#b7ebae] space-y-1 text-[#333333]">
                    <div>🕒 وضعیت ساعت کاری: {shop.hours_detail || shop.open_status}</div>
                    {shop.mall_guide && <div>🏬 آدرس دقیق داخل پاساژ: {shop.mall_guide}</div>}
                  </div>
                </div>
              )}

              {!error && outcome === 'price_changed' && (
                <div className="bg-[#fff8e6] border border-[#fde68a] rounded-xl p-4 text-[#92400e]">
                  <div className="flex items-center gap-2 mb-2 font-extrabold text-[#b45309]">
                    <AlertTriangle className="w-5 h-5 text-[#f59e0b] shrink-0" />
                    <span>کالا موجود است؛ اما تغییر قیمت لحظه‌ای ثبت شد!</span>
                  </div>
                  <p className="text-xs text-[#92400e] leading-relaxed mb-3">
                    قیمت قبلی در ترب {formatPrice(shop.price_toman)} تومان بود، اما فروشنده قیمت قطعی
                    امروز را اعلام کرد:
                  </p>
                  <div className="bg-white rounded-lg p-3 border border-[#fde68a] flex items-center justify-between">
                    <span className="text-xs text-[#555555] font-medium">قیمت جدید تاییدشده:</span>
                    <span className="font-black text-[#d73948] text-sm">
                      {formatPrice(updatedPrice)} تومان
                    </span>
                  </div>
                </div>
              )}

              {!error && outcome === 'no_response' && (
                <div className="bg-[#fff0f2] border border-[#f5c2c7] rounded-xl p-4 text-[#7f161e]">
                  <div className="flex items-center gap-2 mb-2 font-extrabold text-[#d73948]">
                    <XCircle className="w-5 h-5 text-[#d73948] shrink-0" />
                    <span>فروشگاه پاسخگو نیست یا در حال حاضر بسته است!</span>
                  </div>
                  <p className="text-xs text-[#7f161e] leading-relaxed mb-3">
                    فروشگاه «{shop.name}» در حال حاضر پاسخگو نبود. برای جلوگیری از اتلاف وقت شما در
                    بازار، دستیار هوشمند ترب فوراً فروشگاه‌های جایگزین باز در همین محدوده را آماده کرده است.
                  </p>
                  <button
                    onClick={() => {
                      onClose();
                      onFindAlternatives(shop);
                    }}
                    className="w-full flex items-center justify-center gap-2 bg-[#d73948] hover:bg-[#ae1f27] text-white font-bold text-xs py-2.5 px-3 rounded-lg transition-colors cursor-pointer shadow-2xs"
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
                    className="flex-1 bg-[#d73948] hover:bg-[#ae1f27] text-white font-bold text-xs py-2.5 px-3 rounded-lg transition-colors cursor-pointer text-center"
                  >
                    تأیید و مراجعه حضوری
                  </button>
                )}
                <button
                  onClick={onClose}
                  className="bg-[#f2f3f5] hover:bg-[#e6e6e6] text-[#333333] font-bold text-xs py-2.5 px-4 rounded-lg transition-colors cursor-pointer"
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
