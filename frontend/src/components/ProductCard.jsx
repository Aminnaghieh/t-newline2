import React from 'react';
import { Tag, Store, ArrowLeft, CheckCircle2 } from 'lucide-react';

export default function ProductCard({ product, onSelect, isSelected }) {
  const formatPrice = (val) => {
    if (!val || val <= 0) return 'نامشخص';
    return Number(val).toLocaleString('fa-IR');
  };

  const formatDistance = (m) => {
    if (m == null || m < 0) return '';
    if (m >= 1000) return `${(m / 1000).toLocaleString('fa-IR', { maximumFractionDigits: 1 })} کیلومتر`;
    return `${Math.round(m).toLocaleString('fa-IR')} متر`;
  };

  // Nearby fields are only present on location-aware results (located search
  // or chat with a session position); classic results render exactly as before.
  const isLocated = product.nearby_shops_count != null || product.in_radius === false;
  const inRadius = product.in_radius !== false;
  const nearbyCount = product.nearby_shops_count ?? product.offer_count ?? 0;
  const nearestDistance = formatDistance(product.nearest_distance_m);

  return (
    <div
      onClick={() => onSelect(product)}
      data-testid="product-card"
      className={`group relative bg-white rounded-lg border p-3.5 transition-all duration-200 cursor-pointer hover:shadow-card flex flex-col justify-between ${
        isSelected
          ? 'border-torob-red ring-2 ring-torob-red-400/20 bg-torob-red-light/30'
          : 'border-torob-line hover:border-torob-red-400/40'
      }`}
    >
      {isSelected && (
        <div className="absolute top-2 left-2 z-10 bg-torob-red text-white p-1 rounded-full shadow-xs">
          <CheckCircle2 className="w-4 h-4" />
        </div>
      )}

      {/* Out-of-radius badge: this model has no in-person shop near the user */}
      {isLocated && !inRadius && (
        <span
          data-testid="out-of-radius-badge"
          className="absolute top-2 right-2 z-10 bg-amber-100 text-amber-800 border border-amber-300 text-[9px] font-bold px-1.5 py-0.5 rounded-full"
        >
          خارج از محدوده شما{nearestDistance ? ` · ${nearestDistance}` : ''}
        </span>
      )}

      {/* Image & Main Info */}
      <div className="flex gap-3">
        <div className="w-20 h-20 shrink-0 bg-torob-surface rounded-lg overflow-hidden border border-torob-line flex items-center justify-center p-1">
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
            <div className="text-gray-300 text-xs font-bold">بدون تصویر</div>
          )}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-1">
            {product.brand_name && (
              <span className="bg-torob-surface-2 text-torob-ink-2 text-[10px] font-semibold px-2 py-0.5 rounded">
                {product.brand_name}
              </span>
            )}
            {product.category_name && (
              <span className="text-torob-muted text-[11px] truncate">{product.category_name}</span>
            )}
          </div>

          <h3 className="font-bold text-torob-dark text-xs leading-snug line-clamp-2 group-hover:text-torob-red transition-colors">
            {product.persian_title}
          </h3>

          {product.specs_summary && (
            <p className="text-[11px] text-torob-muted mt-1 line-clamp-1">
              {product.specs_summary}
            </p>
          )}
        </div>
      </div>

      {/* Price & Action footer */}
      <div className="mt-3 pt-2.5 border-t border-gray-100 flex items-center justify-between text-xs">
        <div>
          {isLocated && !inRadius && product.nearest_shop_price > 0 ? (
            <>
              <span className="text-[10px] text-gray-400 block">
                قیمت در نزدیک‌ترین فروشگاه{nearestDistance ? ` (${nearestDistance})` : ''} –
                ثبت‌شده، تأییدنشده
              </span>
              <span className="font-bold text-gray-900 text-xs text-torob-red price-display">
                {formatPrice(product.nearest_shop_price)}
              </span>
              <span className="text-[10px] text-gray-400">تومان</span>
            </>
          ) : isLocated && product.min_price_nearby > 0 ? (
            <>
              <span className="text-[10px] text-gray-400 block">
                ارزان‌ترین قیمت نزدیک شما (ثبت‌شده – تأییدنشده)
              </span>
              <span className="font-bold text-gray-900 text-xs text-torob-red price-display">
                {formatPrice(product.min_price_nearby)}
              </span>
              <span className="text-[10px] text-gray-400">تومان</span>
            </>
          ) : (
            <>
              <span className="text-[10px] text-gray-400 block">شروع قیمت از</span>
              <span className="font-bold text-gray-900 text-xs text-torob-red price-display">
                {formatPrice(product.min_price)}
              </span>
              <span className="text-[10px] text-gray-400">تومان</span>
            </>
          )}
        </div>

        <div className="flex items-center gap-1.5">
          <span className="text-[11px] text-torob-muted flex items-center gap-1">
            <Store className="w-3.5 h-3.5 text-gray-400" />
            {isLocated
              ? nearbyCount > 0
                ? `${nearbyCount.toLocaleString('fa-IR')} فروشگاه نزدیک`
                : nearestDistance
                  ? `نزدیک‌ترین: ${nearestDistance}`
                  : 'بدون فروشگاه نزدیک'
              : product.offer_count
                ? `${product.offer_count} فروشگاه`
                : 'موجود'}
          </span>

          <button
            onClick={(e) => {
              e.stopPropagation();
              onSelect(product);
            }}
            data-testid="find-shops-btn"
            className="flex items-center gap-1 bg-torob-red hover:bg-torob-red-dark text-white text-[11px] font-bold px-2.5 py-1.5 rounded-lg transition-colors cursor-pointer"
          >
            <span>یافتن فروشگاه</span>
            <ArrowLeft className="w-3 h-3" />
          </button>
        </div>
      </div>
    </div>
  );
}
