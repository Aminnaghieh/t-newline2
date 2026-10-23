import React, { useState } from 'react';
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
  Star,
  Map as MapIcon,
  ChevronDown,
  ChevronUp,
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
  const [showNeshanMap, setShowNeshanMap] = useState(false);

  const formatPrice = (val) => {
    if (!val || val <= 0) return 'نامشخص';
    return Number(val).toLocaleString('fa-IR');
  };

  // Freshness badge
  const freshness = shop.price_age || { label: 'بروزرسانی امروز', color: 'green' };
  const freshnessColorClass =
    freshness.color === 'green'
      ? 'bg-[#eefceb] text-[#248212] border-[#b7ebae]'
      : freshness.color === 'yellow'
      ? 'bg-[#fff8e6] text-[#b45309] border-[#fde68a]'
      : 'bg-[#fff0f2] text-[#d73948] border-[#f5c2c7]';

  // Hours badge
  const isOpen = shop.is_open;
  const hoursColorClass =
    isOpen === true
      ? 'bg-[#eefceb] text-[#248212] border-[#b7ebae]'
      : isOpen === false
      ? 'bg-[#fff0f2] text-[#d73948] border-[#f5c2c7]'
      : 'bg-[#f8f9fa] text-[#555555] border-[#e6e6e6]';

  return (
    <div
      onClick={() => onSelect && onSelect(shop)}
      data-testid="shop-card"
      className={`bg-white rounded-xl border p-4 transition-all duration-200 cursor-pointer ${
        isSelected
          ? 'border-[#d73948] ring-2 ring-[#d73948]/15 shadow-[0_4px_14px_rgba(215,57,72,0.12)]'
          : 'border-[#e6e6e6] hover:border-[#cccccc] hover:shadow-[0_4px_14px_rgba(0,0,0,0.06)]'
      }`}
    >
      {/* Top Header: Seller Name, Torob Guarantee Badge, Status & Distance */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1.5">
            <h3 className="font-extrabold text-[#222222] text-sm hover:text-[#d73948] transition-colors">
              {shop.name}
            </h3>

            {/* Torob Guarantee Badge */}
            <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-md bg-[#eff6ff] text-[#3468cc] border border-[#bfdbfe]">
              <ShieldCheck className="w-3 h-3" />
              <span>ضمانت ترب</span>
            </span>

            {/* Seller Score */}
            <span className="inline-flex items-center gap-0.5 text-[10px] font-bold px-1.5 py-0.5 rounded-md bg-[#f8f9fa] text-[#555555] border border-[#e6e6e6]">
              <Star className="w-2.5 h-2.5 fill-[#f59e0b] text-[#f59e0b]" />
              <span>{shop.rating || '۴.۸'} (فروشنده حضوری)</span>
            </span>

            {/* Open / Closed badge */}
            <span
              className={`inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full border ${hoursColorClass}`}
            >
              <Clock className="w-3 h-3" />
              <span>{shop.open_status || 'ساعت کاری ثبت‌شده'}</span>
            </span>

            {/* Verification badge if verified */}
            {isVerified && verifiedStatus === 'confirmed' && (
              <span className="inline-flex items-center gap-1 text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-[#eefceb] text-[#248212] border border-[#248212]">
                <CheckCircle className="w-3 h-3" />
                <span>موجودی و قیمت تأیید شده</span>
              </span>
            )}
            {isVerified && verifiedStatus === 'price_changed' && (
              <span className="inline-flex items-center gap-1 text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-[#fff8e6] text-[#b45309] border border-[#f59e0b]">
                <AlertTriangle className="w-3 h-3" />
                <span>قیمت استعلامی جدید</span>
              </span>
            )}
          </div>

          {/* Address */}
          <p className="text-xs text-[#555555] flex items-center gap-1 line-clamp-1">
            <MapPin className="w-3.5 h-3.5 text-[#d73948] shrink-0" />
            <span>{shop.address || shop.location_label || 'تهران'}</span>
          </p>
        </div>

        {/* Distance Badge */}
        {shop.distance_display && (
          <div className="text-left shrink-0 bg-[#f8f9fa] text-[#333333] px-2.5 py-1 rounded-lg border border-[#e6e6e6]">
            <span className="text-[10px] text-[#888888] block">فاصله از شما</span>
            <span className="font-extrabold text-xs text-[#d73948]">{shop.distance_display}</span>
          </div>
        )}
      </div>

      {/* Mall Indoor Wayfinding Guide */}
      {shop.mall_guide ? (
        <div className="mt-3 bg-[#fff0f2]/60 border border-[#f5c2c7] rounded-lg p-2.5 text-xs text-[#333333]">
          <div className="flex items-center gap-1.5 font-extrabold mb-0.5 text-[#d73948]">
            <Building className="w-3.5 h-3.5 text-[#d73948]" />
            <span>راهنمای تردد داخل پاساژ (طبقه و پلاک):</span>
          </div>
          <p className="font-semibold text-[11.5px] text-[#333333] pr-5">{shop.mall_guide}</p>
        </div>
      ) : null}

      {/* Warranty & BNPL Row */}
      <div className="mt-2.5 flex flex-wrap items-center justify-between gap-2">
        {shop.warranty && shop.warranty !== 'null' ? (
          <div className="text-[11px] text-[#555555] flex items-center gap-1 font-medium">
            <ShieldCheck className="w-3.5 h-3.5 text-[#248212] shrink-0" />
            <span>گارانتی: {shop.warranty}</span>
          </div>
        ) : (
          <div className="text-[11px] text-[#555555] flex items-center gap-1 font-medium">
            <ShieldCheck className="w-3.5 h-3.5 text-[#248212] shrink-0" />
            <span>ضمانت اصالت و سلامت فیزیکی در حضور مشتری</span>
          </div>
        )}

        {shop.bnpl_providers && shop.bnpl_providers.length > 0 && (
          <div className="flex items-center gap-1 flex-wrap text-[11px]">
            <span className="text-[#888888] flex items-center gap-1 font-medium">
              <CreditCard className="w-3 h-3 text-[#d73948]" />
              امکان خرید قسطی:
            </span>
            {shop.bnpl_providers.map((bnpl) => (
              <span
                key={bnpl}
                className="bg-[#fff8e6] text-[#b45309] border border-[#fde68a] px-2 py-0.5 rounded font-bold text-[10px]"
              >
                {bnpl}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Torob Seller Price & Freshness Bar */}
      <div className="mt-3 pt-3 border-t border-[#f0f0f0] flex items-center justify-between flex-wrap gap-2 text-xs">
        <div>
          <span className="text-[10px] text-[#888888] block">قیمت ثبت‌شده فروشنده در ترب:</span>
          <div className="flex items-baseline gap-1.5 mt-0.5">
            <span className="font-black text-base text-[#d73948] price-display">
              {formatPrice(shop.price_toman)}
            </span>
            <span className="text-[11px] text-[#555555] font-bold">تومان</span>
            {shop.seller_title && (
              <span className="text-[11px] text-[#888888] truncate max-w-[180px]">
                • {shop.seller_title}
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          <span
            className={`text-[10px] font-bold px-2 py-0.5 rounded-md border ${freshnessColorClass}`}
            title="تاریخ آخرین تغییر قیمت در ترب"
          >
            آخرین بروزرسانی: {freshness.label}
          </span>
        </div>
      </div>

      {/* Neshan Static Map Live Preview */}
      {showNeshanMap && shop.lat && shop.lon && (
        <div className="mt-3 rounded-lg overflow-hidden border border-blue-200 shadow-xs relative animate-fade-in bg-gray-50">
          <img
            src={`https://api.neshan.org/v4/static?key=service.fda262acb42b406d8742d7b6b1d48697&type=neshan&zoom=16&center=${shop.lat},${shop.lon}&width=600&height=220&marker=red`}
            alt={`نقشه نشان - ${shop.name}`}
            className="w-full h-40 object-cover block"
            loading="lazy"
          />
          <div className="absolute bottom-2 right-2 bg-white/95 backdrop-blur-xs text-[10px] text-gray-800 px-2 py-0.5 rounded font-bold shadow-xs border border-gray-200 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-red-600 animate-pulse" />
            <span>نقشه رسمی نشان · {shop.name}</span>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="mt-3 pt-2.5 border-t border-[#f0f0f0] grid grid-cols-2 sm:grid-cols-4 gap-2">
        {/* Verify Button */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            onVerify(shop);
          }}
          data-testid="verify-shop-btn"
          className="flex items-center justify-center gap-1 bg-[#d73948] hover:bg-[#ae1f27] text-white text-xs font-bold py-2 px-2.5 rounded-lg transition-colors cursor-pointer shadow-2xs"
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
          className="flex items-center justify-center gap-1 bg-[#f8f9fa] hover:bg-[#f2f3f5] text-[#333333] border border-[#e6e6e6] text-xs font-bold py-2 px-2.5 rounded-lg transition-colors cursor-pointer"
        >
          <Repeat className="w-3.5 h-3.5 text-[#555555]" />
          <span>جایگزین‌ها</span>
        </button>

        {/* Neshan Static Map Preview Toggle */}
        {shop.lat && shop.lon ? (
          <button
            onClick={(e) => {
              e.stopPropagation();
              setShowNeshanMap(!showNeshanMap);
            }}
            type="button"
            className={`flex items-center justify-center gap-1 text-xs font-bold py-2 px-2.5 rounded-lg border transition-colors cursor-pointer ${
              showNeshanMap
                ? 'bg-blue-100 text-blue-800 border-blue-300'
                : 'bg-white text-blue-700 border-blue-200 hover:bg-blue-50'
            }`}
          >
            <MapIcon className="w-3.5 h-3.5 text-blue-600" />
            <span>{showNeshanMap ? 'بستن نقشه' : 'نقشه نشان'}</span>
            {showNeshanMap ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>
        ) : null}

        {/* Navigation link */}
        {shop.lat && shop.lon ? (
          <a
            href={`https://neshan.org/maps/@${shop.lat},${shop.lon},17z`}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="flex items-center justify-center gap-1 bg-[#eff6ff] hover:bg-[#dbeafe] text-[#3468cc] border border-[#bfdbfe] text-xs font-bold py-2 px-2.5 rounded-lg transition-colors"
          >
            <Navigation className="w-3.5 h-3.5 text-[#3468cc]" />
            <span>مسیریابی اپ</span>
          </a>
        ) : null}
      </div>
    </div>
  );
}
