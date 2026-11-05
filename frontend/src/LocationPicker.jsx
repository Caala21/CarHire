import { useMemo, useRef, useState } from "react";
import { MapContainer, Marker, TileLayer, useMapEvents } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { jsonBody } from "./lib/api.js";

const defaultCenter = [-1.2864, 36.8172];
const pinIcon = L.divIcon({
  className: "",
  html: '<span class="location-pin"></span>',
  iconSize: [24, 24],
  iconAnchor: [12, 12],
});

function MapClickHandler({ onChange }) {
  useMapEvents({
    click(event) {
      onChange(event.latlng.lat, event.latlng.lng);
    },
  });
  return null;
}

function DraggablePin({ latitude, longitude, onChange }) {
  const markerRef = useRef(null);
  const eventHandlers = useMemo(
    () => ({
      dragend() {
        const marker = markerRef.current;
        if (!marker) return;
        const position = marker.getLatLng();
        onChange(position.lat, position.lng);
      },
    }),
    [onChange],
  );
  return (
    <Marker
      draggable
      eventHandlers={eventHandlers}
      position={[latitude, longitude]}
      ref={markerRef}
      icon={pinIcon}
    />
  );
}

export default function LocationPicker({
  request,
  latitude,
  longitude,
  areaName,
  onAreaNameChange,
  onCoordinatesChange,
}) {
  const center =
    latitude != null && longitude != null ? [latitude, longitude] : defaultCenter;
  const [lookupError, setLookupError] = useState("");
  const updatePosition = async (nextLatitude, nextLongitude) => {
    onCoordinatesChange(nextLatitude, nextLongitude);
    try {
      const result = await request("/api/vehicles/reverse-geocode", {
        method: "POST",
        body: jsonBody({
          latitude: nextLatitude,
          longitude: nextLongitude,
        }),
      });
      onAreaNameChange(result.area_name);
    } catch (error) {
      setLookupError(error.message || "We couldn't identify this area. Enter it manually.");
    }
  };

  function useCurrentLocation() {
    setLookupError("");
    if (!navigator.geolocation) {
      setLookupError("Location is unavailable in this browser. Enter the area name manually.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => void updatePosition(coords.latitude, coords.longitude),
      (error) => {
        const message =
          error.code === error.PERMISSION_DENIED
            ? "Location access was denied. Enter the area name manually."
            : "Your location couldn't be determined. Enter the area name manually.";
        setLookupError(message);
      },
      { enableHighAccuracy: false, timeout: 10000 },
    );
  }

  return (
    <div className="sm:col-span-2">
      <label className="block text-xs font-bold text-ink" htmlFor="vehicle-area-name">
        Pick-up area
      </label>
      <input
        id="vehicle-area-name"
        name="area_name"
        required
        maxLength={160}
        value={areaName}
        onChange={(event) => {
          setLookupError("");
          onAreaNameChange(event.target.value);
        }}
        className="field mt-2"
        placeholder="Westlands, Nairobi"
      />
      <input type="hidden" name="location" value={areaName} />
      <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-muted">The public listing shows this area, never the exact pin.</p>
        <button type="button" className="btn-secondary !py-2" onClick={useCurrentLocation}>
          Use my current location
        </button>
      </div>
      {lookupError && <p role="alert" className="mt-2 text-xs text-red-700">{lookupError}</p>}
      <div className="mt-3 h-64 overflow-hidden rounded-2xl border border-line">
        <MapContainer
          key={`${center[0]}-${center[1]}`}
          center={center}
          zoom={latitude != null ? 15 : 11}
          scrollWheelZoom
          className="h-full w-full"
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <MapClickHandler onChange={updatePosition} />
          {latitude != null && longitude != null && (
            <DraggablePin
              latitude={latitude}
              longitude={longitude}
              onChange={updatePosition}
            />
          )}
        </MapContainer>
      </div>
      <p className="mt-2 text-xs text-muted">Click the map to place a pin, then drag it to adjust.</p>
    </div>
  );
}
