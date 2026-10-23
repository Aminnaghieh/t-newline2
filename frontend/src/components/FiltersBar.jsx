import React from 'react';
import {
  Clock,
  CreditCard,
  SlidersHorizontal,
  MapPin,
  Building2,
  Check,
  Wallet,
  X,
} from 'lucide-react';

const BNPL_OPTIONS = ['اسنپ‌پی', 'تارا', 'دیجی پی', 'ازکی‌وام', 'ترب‌پی'];
const RADIUS_OPTIONS = [
  { label: '۱ کیلومتر (پیاده)', value: 1.0 },
  { label: '۳ کیلومتر (محله)', value: 3.0 },
  { label: '۵ کیلومتر (منطقه)', value: 5.0 },
  { label: '۱۰ کیلومتر (شهری)', value: 10.0 },
];
const BUDGET_OPTIONS = [
  { label: 'بدون سقف قیمت', value: 0 },
  { label: 'تا ۱ میلیون تومان', value: 1000000 },
  { label: 'تا ۳ میلیون تومان', value: 3000000 },
  { label: 'تا ۵ میلیون تومان', value: 5000000 },
  { label: 'تا ۱۰ میلیون تومان', value: 10000000 },
  { label: 'تا ۲۰ میلیون تومان', value: 20000000 },
  { label: 'تا ۵۰ میلیون تومان', value: 50000000 },
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
    <div className="bg-white rounded-xl border border-[#e6e6e6] p-3.5 shadow-[0_2px_8px_rgba(0,0,0,0.04)] space-y-2.5">
      {/* Top row: Torob Filter Header + Reset */}
      <div className="flex items-center justify-between text-xs border-b border-[#f0f0f0] pb-2">
        <div className="flex items-center gap-2 font-extrabold text-[#222222]">
          <SlidersHorizontal className="w-4 h-4 text-[#d73948]" />
          <span>فیلترهای هوشمند ترب (اطراف من)</span>
          {activeCount > 0 && (
            <span className="bg-[#d73948] text-white text-[10px] font-bold px-1.5 py-0.2 rounded-full">
              {activeCount.toLocaleString('fa-IR')}
            </span>
          )}
        </div>

        <div className="flex items-center gap-3">
          <span className="text-[11px] text-[#888888] font-medium">
            {totalResults.toLocaleString('fa-IR')} فروشنده حضوری
          </span>
          {activeCount > 0 && (
            <button
              onClick={() => {
                onFilterChange(resetFilters);
                if (onApply) onApply(resetFilters);
              }}
              className="flex items-center gap-1 text-[#d73948] hover:text-[#ae1f27] font-bold cursor-pointer text-[11px]"
            >
              <X className="w-3.5 h-3.5" />
              <span>حذف فیلترها</span>
            </button>
          )}
        </div>
      </div>

      {/* Main Torob Filter Pills */}
      <div className="flex flex-wrap items-center gap-2 text-xs">
        {/* Only Open Toggle */}
        <button
          onClick={() => update({ onlyOpen: !filters.onlyOpen })}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs transition-all cursor-pointer ${
            filters.onlyOpen
              ? 'bg-[#eefceb] text-[#248212] border-[#248212] font-bold'
              : 'bg-[#f8f9fa] text-[#555555] border-[#e6e6e6] hover:border-[#cccccc] font-medium'
          }`}
        >
          <Clock className="w-3.5 h-3.5 text-[#16a34a]" />
          <span>فقط فروشگاه‌های باز</span>
          {filters.onlyOpen && <Check className="w-3 h-3 text-[#248212]" />}
        </button>

        {/* Only Malls / Passages Toggle */}
        <button
          onClick={() => update({ onlyMalls: !filters.onlyMalls })}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs transition-all cursor-pointer ${
            filters.onlyMalls
              ? 'bg-[#fff0f2] text-[#d73948] border-[#d73948] font-bold'
              : 'bg-[#f8f9fa] text-[#555555] border-[#e6e6e6] hover:border-[#cccccc] font-medium'
          }`}
        >
          <Building2 className="w-3.5 h-3.5 text-[#d73948]" />
          <span>پاساژها و مراکز خرید</span>
          {filters.onlyMalls && <Check className="w-3 h-3 text-[#d73948]" />}
        </button>

        {/* Radius Selector */}
        <div className="flex items-center gap-1.5 bg-[#f8f9fa] border border-[#e6e6e6] hover:border-[#cccccc] rounded-lg px-2.5 py-1.5 transition-colors">
          <MapPin className="w-3.5 h-3.5 text-[#d73948]" />
          <span className="text-[#888888] text-[11px]">شعاع:</span>
          <select
            value={filters.radiusKm}
            onChange={(e) => update({ radiusKm: Number(e.target.value) })}
            className="bg-transparent text-[#333333] font-bold outline-none cursor-pointer text-xs"
          >
            {RADIUS_OPTIONS.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </select>
        </div>

        {/* Budget Selector */}
        <div className="flex items-center gap-1.5 bg-[#f8f9fa] border border-[#e6e6e6] hover:border-[#cccccc] rounded-lg px-2.5 py-1.5 transition-colors">
          <Wallet className="w-3.5 h-3.5 text-[#248212]" />
          <span className="text-[#888888] text-[11px]">بودجه:</span>
          <select
            value={filters.maxBudget}
            onChange={(e) => update({ maxBudget: Number(e.target.value) })}
            className="bg-transparent text-[#333333] font-bold outline-none cursor-pointer text-xs"
          >
            {BUDGET_OPTIONS.map((b) => (
              <option key={b.value} value={b.value}>
                {b.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* BNPL / TorobPay Provider Row */}
      <div className="flex items-center gap-1.5 flex-wrap pt-1 border-t border-[#f5f5f5]">
        <span className="text-[#888888] text-[11px] font-semibold flex items-center gap-1 ml-1">
          <CreditCard className="w-3.5 h-3.5 text-[#d73948]" />
          خرید قسطی (BNPL):
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
              className={`px-2.5 py-1 rounded-md border text-[11px] transition-all cursor-pointer ${
                isSelected
                  ? 'bg-[#fff0f2] text-[#d73948] border-[#d73948] font-extrabold shadow-2xs'
                  : 'bg-white text-[#555555] border-[#e6e6e6] hover:border-[#d73948]/50 hover:text-[#d73948] font-medium'
              }`}
            >
              {provider}
            </button>
          );
        })}
      </div>
    </div>
  );
}
