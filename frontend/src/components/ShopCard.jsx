import React from 'react';
import {
  MapPin,
  Clock,
  Building,
  CreditCard,
  PhoneCall,
  Repeat,
  Navigation,
  ShieldCheck,
  AlertTriangle,
  CheckCircle,
  ExternalLink,
} from 'lucide-react';

export default function ShopCard({
  shop,
  onVerify,
  onFindAlternatives,
  isVerified,
  verifiedStatus,
  isSelected,
  onSelect,
}) {
  const formatPrice = (val) => {
    if (!val || val <= 0) return 'نامشخص';
    return Number(val).toLocaleString('fa-IR');
  };

  // Freshness badge
  const freshness = shop.price_age || { label: 'نامشخص', color: 'gray' };
  const freshnessColorClass =
    freshness.color === 'green'
      ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
      : freshness.color === 'yellow'
      ? 'bg-amber-50 text-amber-700 border-amber-200'
      : 'bg-rose-50 text-rose-700 border-rose-200';

  // Hours badge
  const isOpen = shop.is_open;
  const hoursColorClass =
    isOpen === true
      ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
      : isOpen === false
      ? 'bg-rose-50 text-rose-700 border-rose-200'
      : 'bg-gray-50 text-gray-600 border-gray-200';

  return (
    <div
      onClick={() => onSelect && onSelect(shop)}
      data-testid="shop-card"
      className={`bg-white rounded-lg border p-4 transition-all duration-200 hover:shadow-card ${
        isSelected
          ? 'border-torob-red ring-2 ring-torob-red-400/20 shadow-sm'
          : 'border-torob-line hover:border-gray-300'
      }`}
    >
      {/* Top Header: Shop Name & Distance */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <h3 className="font-bold text-torob-dark text-sm hover:text-torob-red transition-colors cursor-pointer">
              {shop.name}
            </h3>

            {/* Open / Closed badge */}
            <span
              className={`inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full border ${hoursColorClass}`}
            >
              <Clock className="w-3 h-3" />
              <span>{shop.open_status || 'ساعت نامشخص'}</span>
            </span>

            {/* Verification badge if verified */}
            {isVerified && verifiedStatus === 'confirmed' && (
              <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300">
                <CheckCircle className="w-3 h-3" />
                <span>موجودی و قیمت تأیید شده</span>
              </span>
            )}
            {isVerified && verifiedStatus === 'price_changed' && (
              <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-300">
                <AlertTriangle className="w-3 h-3" />
                <span>قیمت استعلامی جدید</span>
              </span>
            )}
          </div>

          {/* Address */}
          <p className="text-xs text-gray-500 flex items-center gap-1 line-clamp-1">
            <MapPin className="w-3.5 h-3.5 text-gray-400 shrink-0" />
            <span>{shop.address || shop.location_label || 'تهران'}</span>
          </p>
        </div>

        {/* Distance Badge */}
        {shop.distance_display && (
          <div className="text-left shrink-0 bg-blue-50 text-blue-700 px-2.5 py-1 rounded-lg border border-blue-100">
            <span className="text-[10px] text-blue-500 block">فاصله</span>
            <span className="font-extrabold text-xs">{shop.distance_display}</span>
          </div>
        )}
      </div>

      {/* Mall Indoor Wayfinding Guide (Crucial Feature!) */}
      {shop.mall_guide ? (
        <div className="mt-3 bg-gradient-to-r from-purple-50 to-indigo-50/50 border border-purple-200/80 rounded-lg p-2.5 text-xs text-purple-900">
          <div className="flex items-center gap-1.5 font-bold mb-1 text-purple-800">
            <Building className="w-3.5 h-3.5 text-purple-600" />
            <span>راهنمای داخل پاساژ:</span>
          </div>
          <p className="font-medium text-[11.5px] pr-5">{shop.mall_guide}</p>
        </div>
      ) : null}

      {/* Price & Freshness Row */}
      <div className="mt-3 pt-3 border-t border-gray-100 flex items-center justify-between flex-wrap gap-2 text-xs">
        <div>
          <span className="text-[10px] text-gray-400 block">قیمت ثبت‌شده در ترب:</span>
          <div className="flex items-baseline gap-1.5">
            <span className="font-black text-sm text-torob-red price-display">
              {formatPrice(shop.price_toman)}
            </span>
            <span className="text-[10px] text-gray-400">تومان</span>
            {shop.seller_title && (
              <span className="text-[10px] text-gray-400 truncate max-w-[150px]">
                ({shop.seller_title})
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          <span
            className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${freshnessColorClass}`}
            title="تاریخ آخرین تغییر قیمت در ترب"
          >
            آخرین ثبت: {freshness.label}
          </span>
        </div>
      </div>

      {/* BNPL and Installment Badges */}
      {shop.bnpl_providers && shop.bnpl_providers.length > 0 && (
        <div className="mt-2.5 flex items-center gap-1.5 flex-wrap text-[11px]">
          <span className="text-gray-400 flex items-center gap-1">
            <CreditCard className="w-3 h-3 text-amber-500" />
            خرید اقساطی:
          </span>
          {shop.bnpl_providers.map((bnpl) => (
            <span
              key={bnpl}
              className="bg-amber-50 text-amber-800 border border-amber-200 px-2 py-0.5 rounded font-semibold text-[10px]"
            >
              {bnpl}
            </span>
          ))}
        </div>
      )}

      {/* Warranty */}
      {shop.warranty && shop.warranty !== 'null' && (
        <div className="mt-2 text-[11px] text-gray-500 flex items-center gap-1">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
          <span>گارانتی: {shop.warranty}</span>
        </div>
      )}

      {/* Action Buttons */}
      <div className="mt-3.5 pt-3 border-t border-gray-100 grid grid-cols-2 sm:grid-cols-3 gap-2">
        {/* Verify Button */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            onVerify(shop);
          }}
          data-testid="verify-shop-btn"
          className="flex items-center justify-center gap-1 bg-torob-red hover:bg-torob-red-dark text-white text-xs font-bold py-2 px-2.5 rounded-lg transition-colors cursor-pointer shadow-xs"
        >
          <PhoneCall className="w-3.5 h-3.5" />
          <span>استعلام زنده</span>
        </button>

        {/* Alternatives Button */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            onFindAlternatives(shop);
          }}
          data-testid="alternatives-btn"
          className="flex items-center justify-center gap-1 bg-torob-surface-2 hover:bg-gray-200 text-torob-ink-2 text-xs font-semibold py-2 px-2.5 rounded-lg transition-colors cursor-pointer"
        >
          <Repeat className="w-3.5 h-3.5 text-gray-500" />
          <span>فروشگاه‌های جایگزین</span>
        </button>

        {/* Navigation link */}
        {shop.lat && shop.lon ? (
          <a
            href={`https://neshan.org/maps/@${shop.lat},${shop.lon},17z`}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="col-span-2 sm:col-span-1 flex items-center justify-center gap-1 bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200 text-xs font-semibold py-2 px-2.5 rounded-lg transition-colors"
          >
            <Navigation className="w-3.5 h-3.5 text-blue-600" />
            <span>مسیریابی (نشان)</span>
          </a>
        ) : null}
      </div>
    </div>
  );
}
