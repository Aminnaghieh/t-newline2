import React, { useEffect, useRef } from 'react';
import L from 'leaflet';

export default function MapView({ shops, userLocation, selectedShop, onSelectShop }) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersLayerRef = useRef(null);

  useEffect(() => {
    if (!mapContainerRef.current) return;

    // Default center: Tehran (35.695, 51.406 - Jomhouri / Charsou)
    const initialLat = userLocation?.lat || 35.695;
    const initialLon = userLocation?.lon || 51.406;

    if (!mapInstanceRef.current) {
      const map = L.map(mapContainerRef.current, {
        center: [initialLat, initialLon],
        zoom: 13,
        zoomControl: true,
      });

      // CartoDB Positron tiles for a modern, clean, high-performance look
      L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
        maxZoom: 19,
      }).addTo(map);

      markersLayerRef.current = L.layerGroup().addTo(map);
      mapInstanceRef.current = map;
    }

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  // Update center when user location changes
  useEffect(() => {
    if (mapInstanceRef.current && userLocation?.lat && userLocation?.lon) {
      mapInstanceRef.current.setView([userLocation.lat, userLocation.lon], 13);
    }
  }, [userLocation]);

  // Update markers when shops or selectedShop change
  useEffect(() => {
    const map = mapInstanceRef.current;
    const layer = markersLayerRef.current;
    if (!map || !layer) return;

    layer.clearLayers();

    // Add user marker
    if (userLocation?.lat && userLocation?.lon) {
      const userIcon = L.divIcon({
        className: 'custom-user-marker',
        html: `
          <div style="position:relative;display:flex;align-items:center;justify-content:center;width:24px;height:24px;">
            <div style="position:absolute;width:24px;height:24px;border-radius:50%;background:#3B82F6;opacity:0.25;animation:ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite;"></div>
            <div style="width:14px;height:14px;border-radius:50%;background:#2563EB;border:2px solid white;box-shadow:0 2px 4px rgba(0,0,0,0.3);"></div>
          </div>
        `,
        iconSize: [24, 24],
        iconAnchor: [12, 12],
      });

      L.marker([userLocation.lat, userLocation.lon], { icon: userIcon })
        .addTo(layer)
        .bindPopup('<div style="font-family:Vazirmatn,sans-serif;font-size:12px;font-weight:bold;text-align:center;">📍 موقعیت شما</div>');
    }

    // Add shop markers
    const bounds = L.latLngBounds();
    if (userLocation?.lat && userLocation?.lon) {
      bounds.extend([userLocation.lat, userLocation.lon]);
    }

    shops.forEach((shop) => {
      if (!shop.lat || !shop.lon) return;

      bounds.extend([shop.lat, shop.lon]);

      const isSelected = selectedShop?.shop_id === shop.shop_id;
      const isOpen = shop.is_open;
      const bg = isSelected ? '#E8453C' : isOpen === false ? '#EF4444' : '#10B981';
      const priceText = shop.price_toman
        ? (shop.price_toman / 1000000).toFixed(1) + 'M'
        : '';
      const closedLabel = isOpen === false ? ' بسته' : '';

      const markerHtml = `
        <div style="
          background: ${bg};
          color: white;
          padding: 4px 8px;
          border-radius: 12px;
          font-family: 'Vazirmatn', sans-serif;
          font-size: 11px;
          font-weight: bold;
          white-space: nowrap;
          box-shadow: 0 4px 6px -1px rgba(0,0,0,0.25);
          border: 2px solid white;
          transform: ${isSelected ? 'scale(1.15)' : 'scale(1)'};
          transition: transform 0.2s;
          display: flex;
          align-items: center;
          gap: 4px;
        ">
          <span>🏪</span>
          <span>${priceText}</span>
          ${closedLabel ? `<span style="font-size:9px;opacity:.9">${closedLabel}</span>` : ''}
        </div>
      `;

      const icon = L.divIcon({
        className: 'custom-shop-pin',
        html: markerHtml,
        iconSize: [60, 28],
        iconAnchor: [30, 14],
      });

      const marker = L.marker([shop.lat, shop.lon], { icon }).addTo(layer);

      marker.on('click', () => {
        if (onSelectShop) onSelectShop(shop);
      });

      const popupContent = `
        <div style="font-family:'Vazirmatn',sans-serif;direction:rtl;min-width:180px;text-align:right;">
          <div style="font-weight:bold;font-size:13px;color:#111;margin-bottom:4px;">${shop.name}</div>
          <div style="font-size:11px;color:#666;margin-bottom:6px;">📍 ${shop.address || shop.location_label || ''}</div>
          ${shop.mall_guide ? `<div style="font-size:11px;color:#6B21A8;background:#F3E8FF;padding:3px 6px;border-radius:4px;margin-bottom:6px;">${shop.mall_guide}</div>` : ''}
          <div style="display:flex;justify-content:space-between;align-items:center;border-top:1px solid #eee;padding-top:6px;">
            <span style="font-size:11px;color:#888;">قیمت:</span>
            <span style="font-weight:bold;color:#E8453C;font-size:12px;">${shop.price_display || ''}</span>
          </div>
          <div style="font-size:11px;margin-top:4px;color:${shop.is_open ? '#059669' : '#DC2626'}">${shop.open_status || ''}</div>
        </div>
      `;

      marker.bindPopup(popupContent);
    });

    if (shops.length > 0 && map && bounds.isValid()) {
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 15 });
    }
  }, [shops, userLocation, selectedShop]);

  return (
    <div className="w-full h-full min-h-[300px] rounded-xl overflow-hidden border border-gray-200 relative">
      <div ref={mapContainerRef} className="w-full h-full min-h-[300px]" />
      {/* Map Legend */}
      <div className="absolute bottom-3 right-3 z-[1000] bg-white/95 backdrop-blur-xs rounded-lg shadow-md border border-gray-200 p-2 text-[10px] space-y-1 font-medium">
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
          <span>فروشگاه باز</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-rose-500" />
          <span>فروشگاه بسته</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-blue-500" />
          <span>موقعیت شما</span>
        </div>
      </div>
    </div>
  );
}
