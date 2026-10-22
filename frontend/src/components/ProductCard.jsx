import React from 'react';
import { Tag, Store, ArrowLeft, CheckCircle2 } from 'lucide-react';

export default function ProductCard({ product, onSelect, isSelected }) {
  const formatPrice = (val) => {
    if (!val || val <= 0) return 'نامشخص';
    return Number(val).toLocaleString('fa-IR');
  };

  return (
    <div
      onClick={() => onSelect(product)}
      data-testid="product-card"
      className={`group relative bg-white rounded-xl border p-3.5 transition-all duration-200 cursor-pointer hover:shadow-md flex flex-col justify-between ${
        isSelected
          ? 'border-[#E8453C] ring-2 ring-red-100 bg-red-50/20'
          : 'border-gray-200 hover:border-red-200'
      }`}
    >
      {isSelected && (
        <div className="absolute top-2 left-2 z-10 bg-[#E8453C] text-white p-1 rounded-full shadow-xs">
          <CheckCircle2 className="w-4 h-4" />
        </div>
      )}

      {/* Image & Main Info */}
      <div className="flex gap-3">
        <div className="w-20 h-20 shrink-0 bg-gray-50 rounded-lg overflow-hidden border border-gray-100 flex items-center justify-center p-1">
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
              <span className="bg-gray-100 text-gray-700 text-[10px] font-semibold px-2 py-0.5 rounded">
                {product.brand_name}
              </span>
            )}
            {product.category_name && (
              <span className="text-gray-400 text-[11px] truncate">{product.category_name}</span>
            )}
          </div>

          <h3 className="font-bold text-gray-900 text-xs leading-snug line-clamp-2 group-hover:text-[#E8453C] transition-colors">
            {product.persian_title}
          </h3>

          {product.specs_summary && (
            <p className="text-[11px] text-gray-500 mt-1 line-clamp-1">
              {product.specs_summary}
            </p>
          )}
        </div>
      </div>

      {/* Price & Action footer */}
      <div className="mt-3 pt-2.5 border-t border-gray-100 flex items-center justify-between text-xs">
        <div>
          <span className="text-[10px] text-gray-400 block">شروع قیمت از</span>
          <span className="font-bold text-gray-900 text-xs text-[#E8453C] price-display">
            {formatPrice(product.min_price)}
          </span>
          <span className="text-[10px] text-gray-400">تومان</span>
        </div>

        <div className="flex items-center gap-1.5">
          <span className="text-[11px] text-gray-500 flex items-center gap-1">
            <Store className="w-3.5 h-3.5 text-gray-400" />
            {product.offer_count ? `${product.offer_count} فروشگاه` : 'موجود'}
          </span>

          <button
            onClick={(e) => {
              e.stopPropagation();
              onSelect(product);
            }}
            data-testid="find-shops-btn"
            className="flex items-center gap-1 bg-[#E8453C] hover:bg-[#d03a31] text-white text-[11px] font-bold px-2.5 py-1.5 rounded-lg transition-colors cursor-pointer"
          >
            <span>یافتن فروشگاه</span>
            <ArrowLeft className="w-3 h-3" />
          </button>
        </div>
      </div>
    </div>
  );
}
