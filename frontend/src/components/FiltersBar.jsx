import React from 'react';
import { Filter, Clock, CreditCard, SlidersHorizontal, MapPin, Building2, Check, Wallet } from 'lucide-react';

const BNPL_OPTIONS = ['اسنپ‌پی', 'تارا', 'دیجی پی', 'ازکی‌وام', 'ترب‌پی'];
const RADIUS_OPTIONS = [
  { label: '۱ کیلومتر (پیاده)', value: 1.0 },
  { label: '۳ کیلومتر (محله)', value: 3.0 },
  { label: '۵ کیلومتر (منطقه)', value: 5.0 },
  { label: '۱۰ کیلومتر (شهری)', value: 10.0 },
];
const BUDGET_OPTIONS = [
  { label: 'بدون سقف', value: 0 },
  { label: 'تا ۱ میلیون', value: 1000000 },
  { label: 'تا ۳ میلیون', value: 3000000 },
  { label: 'تا ۵ میلیون', value: 5000000 },
  { label: 'تا ۱۰ میلیون', value: 10000000 },
  { label: 'تا ۲۰ میلیون', value: 20000000 },
  { label: 'تا ۵۰ میلیون', value: 50000000 },
];

export default function FiltersBar({
  filters,
  onFilterChange,
  onApply,
  availableBnpl,
  totalResults,
}) {
  const activeCount =
    (filters.onlyOpen ? 1 : 0) +
    (filters.bnplProvider ? 1 : 0) +
    (filters.onlyMalls ? 1 : 0) +
    (filters.maxBudget > 0 ? 1 : 0);

  // Any change to a filter must be re-applied on the server (radius and BNPL
  // change the candidate set, not just the rendered list).
  const update = (patch) => {
    const next = { ...filters, ...patch };
    onFilterChange(next);
    if (onApply) onApply(next);
  };

  const resetFilters = {
    onlyOpen: false,
    bnplProvider: '',
    onlyMalls: false,
    maxBudget: 0,
    radiusKm: 5.0,
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-3 shadow-xs space-y-3">
      {/* Top row: Summary + Reset */}
      <div className="flex items-center justify-between text-xs border-b border-gray-100 pb-2">
        <div className="flex items-center gap-1.5 font-bold text-gray-800">
          <SlidersHorizontal className="w-4 h-4 text-[#E8453C]" />
          <span>فیلترها و تنظیمات جستجو</span>
          {activeCount > 0 && (
            <span className="bg-[#E8453C] text-white text-[10px] font-bold px-1.5 py-0.2 rounded-full">
              {activeCount}
            </span>
          )}
        </div>

        {activeCount > 0 && (
          <button
            onClick={() => {
              onFilterChange(resetFilters);
              if (onApply) onApply(resetFilters);
            }}
            className="text-[#E8453C] hover:underline font-semibold cursor-pointer"
          >
            پاک کردن فیلترها
          </button>
        )}
      </div>

      {/* Main Filter Chips */}
      <div className="flex flex-wrap items-center gap-2 text-xs">
        {/* Only Open Toggle */}
        <button
          onClick={() => update({ onlyOpen: !filters.onlyOpen })}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border font-medium transition-all cursor-pointer ${
            filters.onlyOpen
              ? 'bg-emerald-50 text-emerald-700 border-emerald-300 font-semibold shadow-xs'
              : 'bg-gray-50 text-gray-600 border-gray-200 hover:bg-gray-100'
          }`}
        >
          <Clock className="w-3.5 h-3.5 text-emerald-600" />
          <span>فقط فروشگاه‌های باز</span>
          {filters.onlyOpen && <Check className="w-3 h-3 text-emerald-600" />}
        </button>

        {/* Only Malls / Passages Toggle */}
        <button
          onClick={() => update({ onlyMalls: !filters.onlyMalls })}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border font-medium transition-all cursor-pointer ${
            filters.onlyMalls
              ? 'bg-purple-50 text-purple-700 border-purple-300 font-semibold shadow-xs'
              : 'bg-gray-50 text-gray-600 border-gray-200 hover:bg-gray-100'
          }`}
        >
          <Building2 className="w-3.5 h-3.5 text-purple-600" />
          <span>مراکز خرید و پاساژها</span>
          {filters.onlyMalls && <Check className="w-3 h-3 text-purple-600" />}
        </button>

        {/* Radius Selector */}
        <div className="flex items-center gap-1 bg-gray-50 border border-gray-200 rounded-lg px-2.5 py-1">
          <MapPin className="w-3.5 h-3.5 text-blue-500" />
          <span className="text-gray-500 text-[11px]">شعاع:</span>
          <select
            value={filters.radiusKm}
            onChange={(e) => update({ radiusKm: Number(e.target.value) })}
            className="bg-transparent text-gray-700 font-medium outline-none cursor-pointer text-xs"
          >
            {RADIUS_OPTIONS.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </select>
        </div>

        {/* Budget Selector */}
        <div className="flex items-center gap-1 bg-gray-50 border border-gray-200 rounded-lg px-2.5 py-1">
          <Wallet className="w-3.5 h-3.5 text-emerald-600" />
          <span className="text-gray-500 text-[11px]">سقف بودجه:</span>
          <select
            value={filters.maxBudget}
            onChange={(e) => update({ maxBudget: Number(e.target.value) })}
            className="bg-transparent text-gray-700 font-medium outline-none cursor-pointer text-xs"
          >
            {BUDGET_OPTIONS.map((b) => (
              <option key={b.value} value={b.value}>
                {b.label}
              </option>
            ))}
          </select>
        </div>

        {/* BNPL Provider Chips */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-gray-400 text-[11px] flex items-center gap-1">
            <CreditCard className="w-3.5 h-3.5 text-amber-500" />
            خرید اقساطی:
          </span>
          {BNPL_OPTIONS.map((provider) => {
            const isSelected = filters.bnplProvider === provider;
            return (
              <button
                key={provider}
                onClick={() =>
                  update({
                    bnplProvider: isSelected ? '' : provider,
                  })
                }
                className={`px-2.5 py-1 rounded-md border text-xs transition-all cursor-pointer font-medium ${
                  isSelected
                    ? 'bg-amber-500 text-white border-amber-600 shadow-xs'
                    : 'bg-gray-50 text-gray-600 border-gray-200 hover:bg-gray-100'
                }`}
              >
                {provider}
              </button>
            );
          })}
        </div>
      </div>

      {/* Result count */}
      <div className="text-[11px] text-gray-400 border-t border-gray-100 pt-2">
        {totalResults} فروشگاه با فیلترهای فعلی نمایش داده می‌شود
      </div>
    </div>
  );
}
