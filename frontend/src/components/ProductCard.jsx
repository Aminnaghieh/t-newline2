import React from 'react';
import { Store, ArrowLeft, CheckCircle2, Heart, Bell } from 'lucide-react';

export default function ProductCard({ product, onSelect, isSelected }) {
  const formatPrice = (val) => {
    if (!val || val <= 0) return 'نامشخص';
    return Number(val).toLocaleString('fa-IR');
  };

  const formatDistance = (m) => {
    if (m == null || m < 0) return '';
    if (m >= 1000)
      return `${(m / 1000).toLocaleString('fa-IR', { maximumFractionDigits: 1 })} کیلومتر`;
    return `${Math.round(m).toLocaleString('fa-IR')} متر`;
  };

  const isLocated = product.nearby_shops_count != null || product.in_radius === false;
  const inRadius = product.in_radius !== false;
  const nearbyCount = product.nearby_shops_count ?? product.offer_count ?? 0;
  const nearestDistance = formatDistance(product.nearest_distance_m);

  return (
    <div
      onClick={() => onSelect(product)}
      data-testid="product-card"
      className={`group relative bg-white rounded-xl border p-3.5 transition-all duration-200 cursor-pointer flex flex-col justify-between ${
        isSelected
          ? 'border-[#d73948] ring-2 ring-[#d73948]/15 bg-[#fff0f2]/20 shadow-[0_4px_14px_rgba(215,57,72,0.12)]'
          : 'border-[#e6e6e6] hover:border-[#d73948]/40 hover:shadow-[0_6px_18px_rgba(0,0,0,0.07)]'
      }`}
    >
      {isSelected && (
        <div className="absolute top-2.5 left-2.5 z-10 bg-[#d73948] text-white p-1 rounded-full shadow-2xs">
          <CheckCircle2 className="w-3.5 h-3.5" />
        </div>
      )}

      {/* Out-of-radius badge */}
      {isLocated && !inRadius && (
        <span
          data-testid="out-of-radius-badge"
          className="absolute top-2.5 right-2.5 z-10 bg-[#fff8e6] text-[#b45309] border border-[#fde68a] text-[10px] font-bold px-2 py-0.5 rounded-md"
        >
          خارج از محدوده شما{nearestDistance ? ` · ${nearestDistance}` : ''}
        </span>
      )}

      {/* Product Top Section: Image & Title */}
      <div className="flex gap-3.5 items-start">
        <div className="w-24 h-24 shrink-0 bg-white rounded-lg overflow-hidden border border-[#f0f0f0] flex items-center justify-center p-1.5 relative">
          {product.image_url ? (
            <img
              src={product.image_url}
              alt={product.persian_title}
              className="w-full h-full object-contain group-hover:scale-105 transition-transform duration-200"
              onError={(e) => {
                e.target.style.display = 'none';
              }}
            />
          ) : (
            <div className="text-[#cccccc] text-[11px] font-bold text-center">تصویر کالا</div>
          )}
        </div>

        <div className="flex-1 min-w-0 pt-0.5">
          <div className="flex items-center gap-1.5 mb-1 flex-wrap">
            {product.brand_name && (
              <span className="bg-[#f2f3f5] text-[#555555] text-[10px] font-bold px-2 py-0.5 rounded">
                {product.brand_name}
              </span>
            )}
            {product.category_name && (
              <span className="text-[#888888] text-[10px] truncate">{product.category_name}</span>
            )}
          </div>

          <h3 className="font-bold text-[#222222] text-[13px] leading-5 line-clamp-2 group-hover:text-[#d73948] transition-colors">
            {product.persian_title}
          </h3>

          {product.specs_summary && (
            <p className="text-[11px] text-[#888888] mt-1 line-clamp-1">
              {product.specs_summary}
            </p>
          )}
        </div>
      </div>

      {/* Torob Price & Store Count Footer */}
      <div className="mt-3.5 pt-2.5 border-t border-[#f0f0f0] flex items-end justify-between gap-2 text-xs">
        <div>
          {isLocated && !inRadius && product.nearest_shop_price > 0 ? (
            <>
              <span className="text-[10px] text-[#888888] block mb-0.5">
                قیمت در نزدیک‌ترین فروشگاه{nearestDistance ? ` (${nearestDistance})` : ''}
              </span>
              <div className="flex items-baseline gap-1">
                <span className="text-[11px] text-[#555555] font-semibold">از</span>
                <span className="font-black text-sm text-[#d73948] price-display">
                  {formatPrice(product.nearest_shop_price)}
                </span>
                <span className="text-[11px] text-[#555555] font-medium">تومان</span>
              </div>
            </>
          ) : isLocated && product.min_price_nearby > 0 ? (
            <>
              <span className="text-[10px] text-[#248212] font-semibold block mb-0.5">
                ارزان‌ترین قیمت حضوری اطراف شما
              </span>
              <div className="flex items-baseline gap-1">
                <span className="text-[11px] text-[#555555] font-semibold">از</span>
                <span className="font-black text-sm text-[#d73948] price-display">
                  {formatPrice(product.min_price_nearby)}
                </span>
                <span className="text-[11px] text-[#555555] font-medium">تومان</span>
              </div>
            </>
          ) : (
            <>
              <span className="text-[10px] text-[#888888] block mb-0.5">کمترین قیمت در ترب</span>
              <div className="flex items-baseline gap-1">
                <span className="text-[11px] text-[#555555] font-semibold">از</span>
                <span className="font-black text-sm text-[#d73948] price-display">
                  {formatPrice(product.min_price)}
                </span>
                <span className="text-[11px] text-[#555555] font-medium">تومان</span>
              </div>
            </>
          )}
        </div>

        <div className="flex flex-col items-end gap-1.5">
          <span className="text-[11px] text-[#888888] font-medium flex items-center gap-1">
            <Store className="w-3 h-3 text-[#888888]" />
            {isLocated
              ? nearbyCount > 0
                ? `در ${nearbyCount.toLocaleString('fa-IR')} فروشگاه نزدیک`
                : nearestDistance
                ? `نزدیک‌ترین: ${nearestDistance}`
                : 'بدون فروشگاه نزدیک'
              : product.offer_count
              ? `در ${product.offer_count.toLocaleString('fa-IR')} فروشگاه`
              : 'موجود در ترب'}
          </span>

          <button
            onClick={(e) => {
              e.stopPropagation();
              onSelect(product);
            }}
            data-testid="find-shops-btn"
            className="flex items-center gap-1 bg-[#d73948] hover:bg-[#ae1f27] text-white text-[11px] font-bold px-3 py-1.5 rounded-lg transition-colors cursor-pointer shadow-2xs"
          >
            <span>یافتن فروشگاه</span>
            <ArrowLeft className="w-3 h-3" />
          </button>
        </div>
      </div>
    </div>
  );
}
