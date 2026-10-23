import React from 'react';
import { MapPin, Compass, ShieldCheck, Sparkles, CreditCard, Store, Check } from 'lucide-react';

const TEHRAN_AREAS = [
  { key: 'jomhouri', name: 'جمهوری / چارسو / علاءالدین', lat: 35.695, lon: 51.406 },
  { key: 'valiasr', name: 'میدان ولیعصر', lat: 35.7144, lon: 51.4103 },
  { key: 'saadatabad', name: 'سعادت‌آباد / شهرک غرب', lat: 35.7789, lon: 51.3767 },
  { key: 'vanak', name: 'میدان ونک', lat: 35.7589, lon: 51.4011 },
  { key: 'tajrish', name: 'تجریش / ارگ', lat: 35.8033, lon: 51.4268 },
  { key: 'haftir', name: 'هفت‌تیر', lat: 35.7143, lon: 51.4229 },
  { key: 'bazargharb', name: 'بازار بزرگ تهران', lat: 35.674, lon: 51.42 },
];

/* Official-style Torob Radish SVG Emblem */
function TorobLogo({ className = 'w-9 h-9' }) {
  return (
    <svg
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      {/* Green radish leaves */}
      <path
        d="M24 13C24 8.5 28.5 4.5 33 5.5C32.5 10 28.5 13 24 13Z"
        fill="#2EA836"
      />
      <path
        d="M24 13C24 8.5 19.5 4.5 15 5.5C15.5 10 19.5 13 24 13Z"
        fill="#248212"
      />
      <path
        d="M24 14C21.5 9 22.5 3.5 24 2C25.5 3.5 26.5 9 24 14Z"
        fill="#39B54A"
      />
      {/* Red radish body */}
      <path
        d="M36 24.5C36 31.8 27.5 38.5 24 44.5C20.5 38.5 12 31.8 12 24.5C12 17.6 17.4 12.5 24 12.5C30.6 12.5 36 17.6 36 24.5Z"
        fill="#D73948"
      />
      {/* Subtle highlight on radish */}
      <path
        d="M17.5 20.5C16.5 23.5 17 27.5 19.5 31"
        stroke="#FF8A96"
        strokeWidth="2.2"
        strokeLinecap="round"
      />
    </svg>
  );
}

export default function Header({
  currentStep,
  userLocation,
  onLocationSelect,
  onDetectLocation,
  isDetectingLocation,
}) {
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
    <header className="bg-white border-b border-[#e6e6e6] sticky top-0 z-30 shadow-[0_1px_4px_rgba(0,0,0,0.04)]">
      {/* Main Torob Header Row */}
      <div className="max-w-7xl mx-auto px-3 sm:px-6 h-16 flex items-center justify-between gap-3">
        {/* Right: Torob Brand Identity + Nav Links */}
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2.5">
            <div className="w-10 h-10 rounded-xl bg-[#fff0f2] border border-[#ffd6db] flex items-center justify-center shrink-0">
              <TorobLogo className="w-8 h-8" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-black text-2xl text-[#d73948] tracking-tight leading-none">
                  ترب
                </span>
                <span className="text-xs font-extrabold text-[#333333] hidden xs:inline">
                  | تُرب‌گرد
                </span>
                <span className="bg-[#fff0f2] text-[#d73948] text-[11px] font-bold px-2 py-0.5 rounded-md border border-[#f5c2c7] flex items-center gap-1">
                  <Sparkles className="w-3 h-3" />
                  <span>دستیار خرید حضوری</span>
                </span>
              </div>
              <p className="text-[11px] text-[#888888] mt-0.5 hidden sm:block">
                مقایسه قیمت، موجودی لحظه‌ای و راهنمای خرید حضوری در پاساژهای تهران
              </p>
            </div>
          </div>

          {/* Torob.com Navigation Links (Desktop) */}
          <nav className="hidden lg:flex items-center gap-1 text-xs font-semibold text-[#555555] border-r border-[#e6e6e6] pr-5">
            <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#fff0f2] text-[#d73948] font-bold">
              <Store className="w-3.5 h-3.5" />
              <span>اطراف من (حضوری)</span>
            </span>
            <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[#555555] hover:text-[#d73948] hover:bg-[#f8f9fa] transition-colors">
              <CreditCard className="w-3.5 h-3.5 text-[#16a34a]" />
              <span>ترب‌پی (قسطی)</span>
            </span>
            <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[#555555] hover:text-[#d73948] hover:bg-[#f8f9fa] transition-colors">
              <ShieldCheck className="w-3.5 h-3.5 text-[#3468cc]" />
              <span>ضمانت ترب</span>
            </span>
          </nav>
        </div>

        {/* Left: Torob City / Neighborhood Selector */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 bg-[#f8f9fa] hover:bg-[#f2f3f5] border border-[#e6e6e6] rounded-lg px-2.5 py-1.5 transition-colors">
            <MapPin className="w-4 h-4 text-[#d73948] shrink-0" />
            <span className="text-[11px] text-[#888888] hidden md:inline">محدوده شما:</span>
            <select
              aria-label="انتخاب محله"
              className="bg-transparent text-xs font-bold text-[#333333] outline-none cursor-pointer max-w-[135px] sm:max-w-[200px]"
              value={selectedAreaKey}
              onChange={(e) => {
                const key = e.target.value;
                if (key === 'gps') return;
                const area = TEHRAN_AREAS.find((a) => a.key === key);
                if (area) onLocationSelect(area.lat, area.lon, area.name);
              }}
            >
              {isGps && <option value="gps">📡 موقعیت فعلی شما (GPS)</option>}
              {TEHRAN_AREAS.map((a) => (
                <option key={a.key} value={a.key}>
                  تهران - {a.name}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={onDetectLocation}
            disabled={isDetectingLocation}
            title="موقعیت فعلی من (GPS)"
            className="flex items-center gap-1.5 bg-[#fff0f2] hover:bg-[#ffe0e5] text-[#d73948] text-xs font-bold px-3 py-1.5 rounded-lg border border-[#f5c2c7] transition-colors cursor-pointer disabled:opacity-50"
          >
            <Compass className={`w-3.5 h-3.5 ${isDetectingLocation ? 'animate-spin' : ''}`} />
            <span className="hidden md:inline">اطراف من (GPS)</span>
          </button>
        </div>
      </div>

      {/* Torob Sub-header Stepper Bar */}
      <div className="bg-[#f8f9fa] border-t border-[#e6e6e6] px-4 py-1.5 overflow-x-auto">
        <div className="max-w-7xl mx-auto flex items-center justify-between sm:justify-center gap-2 sm:gap-5 min-w-max text-xs">
          {steps.map((st, idx) => {
            const stepOrder = [
              'greeting',
              'discovery',
              'location',
              'comparison',
              'verification',
              'fallback',
            ];
            const currentIndex = stepOrder.indexOf(currentStep);
            const thisIndex = stepOrder.indexOf(st.id);
            const isCompleted = currentIndex > thisIndex;
            const isCurrent =
              currentStep === st.id || (st.id === 'comparison' && currentStep === 'fallback');

            return (
              <div key={st.id} className="flex items-center gap-2">
                <div
                  className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold transition-all ${
                    isCurrent
                      ? 'bg-[#d73948] text-white shadow-2xs'
                      : isCompleted
                      ? 'bg-[#eefceb] text-[#248212] border border-[#b7ebae]'
                      : 'text-[#888888] bg-white border border-[#e6e6e6]'
                  }`}
                >
                  {isCompleted ? <Check className="w-3 h-3 stroke-[2.5]" /> : null}
                  <span>{st.label}</span>
                </div>
                {idx < steps.length - 1 && <span className="text-[#cccccc] font-bold">‹</span>}
              </div>
            );
          })}
        </div>
      </div>
    </header>
  );
}
