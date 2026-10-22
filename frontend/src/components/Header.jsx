import React from 'react';
import { ShoppingBag, MapPin, Compass, ShieldCheck, Layers } from 'lucide-react';

const TEHRAN_AREAS = [
  { key: 'jomhouri', name: 'جمهوری / چارسو / علاءالدین', lat: 35.695, lon: 51.406 },
  { key: 'valiasr', name: 'میدان ولیعصر', lat: 35.7144, lon: 51.4103 },
  { key: 'saadatabad', name: 'سعادت‌آباد / شهرک غرب', lat: 35.7789, lon: 51.3767 },
  { key: 'vanak', name: 'میدان ونک', lat: 35.7589, lon: 51.4011 },
  { key: 'tajrish', name: 'تجریش / ارگ', lat: 35.8033, lon: 51.4268 },
  { key: 'haftir', name: 'هفت‌تیر', lat: 35.7143, lon: 51.4229 },
  { key: 'bazargharb', name: 'بازار بزرگ تهران', lat: 35.674, lon: 51.42 },
];

export default function Header({ currentStep, userLocation, onLocationSelect, onDetectLocation, isDetectingLocation }) {
  const steps = [
    { id: 'discovery', label: '۱. انتخاب کالا' },
    { id: 'location', label: '۲. موقعیت مکانی' },
    { id: 'comparison', label: '۳. مقایسه فروشگاه‌ها' },
    { id: 'verification', label: '۴. استعلام و خرید' },
  ];

  // Resolve the select value: match the current location against the known
  // areas, otherwise treat it as a GPS/custom position.
  const matchedArea = TEHRAN_AREAS.find(
    (a) =>
      userLocation &&
      Math.abs(a.lat - userLocation.lat) < 0.001 &&
      Math.abs(a.lon - userLocation.lon) < 0.001
  );
  const isGps = !matchedArea;
  const selectedAreaKey = matchedArea ? matchedArea.key : 'gps';

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-30 shadow-xs">
      {/* Top Banner */}
      <div className="max-w-7xl mx-auto px-4 py-2.5 flex items-center justify-between gap-4">
        {/* Brand */}
        <div className="flex items-center gap-2.5">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-[#E8453C] to-[#ff6b62] flex items-center justify-center text-white shadow-md shadow-red-200">
            <ShoppingBag className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-xl text-gray-900 tracking-tight">تُرب‌گرد</span>
              <span className="bg-red-50 text-[#E8453C] text-xs font-bold px-2 py-0.5 rounded-full border border-red-200">
                خرید حضوری
              </span>
            </div>
            <p className="text-xs text-gray-500 hidden sm:block">دستیار هوشمند ایجنتیک خرید از پاساژها و بازارهای تهران</p>
          </div>
        </div>

        {/* Location Selector */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-lg px-2.5 py-1.5 transition-colors">
            <MapPin className="w-4 h-4 text-[#E8453C] shrink-0" />
            <select
              aria-label="انتخاب محله"
              className="bg-transparent text-xs font-medium text-gray-700 outline-none cursor-pointer max-w-[130px] sm:max-w-[200px]"
              value={selectedAreaKey}
              onChange={(e) => {
                const key = e.target.value;
                if (key === 'gps') return;
                const area = TEHRAN_AREAS.find((a) => a.key === key);
                if (area) onLocationSelect(area.lat, area.lon, area.name);
              }}
            >
              {/* The GPS position is not part of TEHRAN_AREAS – render it
                  as an explicit option so the select never shows blank. */}
              {isGps && (
                <option value="gps">📡 موقعیت فعلی شما (GPS)</option>
              )}
              {TEHRAN_AREAS.map((a) => (
                <option key={a.key} value={a.key}>
                  📍 {a.name}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={onDetectLocation}
            disabled={isDetectingLocation}
            title="موقعیت فعلی من (GPS)"
            className="flex items-center gap-1 bg-[#E8453C]/10 hover:bg-[#E8453C]/20 text-[#E8453C] text-xs font-semibold px-2.5 py-1.5 rounded-lg border border-red-200 transition-colors cursor-pointer disabled:opacity-50"
          >
            <Compass className={`w-3.5 h-3.5 ${isDetectingLocation ? 'animate-spin' : ''}`} />
            <span className="hidden md:inline">موقعیت من</span>
          </button>
        </div>
      </div>

      {/* Stepper bar */}
      <div className="bg-gray-50/80 border-t border-gray-100 px-4 py-1.5 overflow-x-auto">
        <div className="max-w-7xl mx-auto flex items-center justify-between sm:justify-center gap-2 sm:gap-6 min-w-max text-xs">
          {steps.map((st, idx) => {
            const stepOrder = ['greeting', 'discovery', 'location', 'comparison', 'verification', 'fallback'];
            const currentIndex = stepOrder.indexOf(currentStep);
            const thisIndex = stepOrder.indexOf(st.id);
            const isCompleted = currentIndex > thisIndex;
            const isCurrent = currentStep === st.id || (st.id === 'comparison' && currentStep === 'fallback');

            return (
              <div key={st.id} className="flex items-center gap-2">
                <div
                  className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full font-medium transition-all ${
                    isCurrent
                      ? 'bg-[#E8453C] text-white shadow-xs'
                      : isCompleted
                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                      : 'text-gray-400 bg-white border border-gray-200'
                  }`}
                >
                  {isCompleted ? <ShieldCheck className="w-3.5 h-3.5" /> : null}
                  <span>{st.label}</span>
                </div>
                {idx < steps.length - 1 && <span className="text-gray-300">←</span>}
              </div>
            );
          })}
        </div>
      </div>
    </header>
  );
}
