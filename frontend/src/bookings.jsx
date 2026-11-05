import { useEffect, useMemo, useState } from "react";
import { CalendarDays, Clock3, Trash2 } from "lucide-react";
import { DayPicker } from "react-day-picker";
import "react-day-picker/style.css";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "./auth.jsx";
import { jsonBody } from "./lib/api.js";
import LocationPicker from "./LocationPicker.jsx";

function dateKey(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function localDate(value) {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function todayKey() {
  return dateKey(new Date());
}

function formatDate(value) {
  return localDate(value).toLocaleDateString("en-KE", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function dayNumber(value) {
  return Date.parse(`${value}T00:00:00Z`) / 86400000;
}

function blockedDays(ranges) {
  return ranges.flatMap((range) => {
    const days = [];
    for (
      let day = localDate(range.start_date);
      dateKey(day) < range.end_date;
      day.setDate(day.getDate() + 1)
    ) {
      days.push(new Date(day));
    }
    return days;
  });
}

function BookingCalendar({ blockedRanges, startDate, endDate, onSelect }) {
  const blocked = useMemo(() => blockedDays(blockedRanges), [blockedRanges]);
  const selected = startDate
    ? { from: localDate(startDate), to: endDate ? localDate(endDate) : undefined }
    : undefined;

  return (
    <div className="mt-4 rounded-2xl border border-line p-3 sm:p-4">
      <DayPicker
        mode="range"
        selected={selected}
        onSelect={onSelect}
        disabled={[{ before: localDate(todayKey()) }, ...blocked]}
        modifiers={{ unavailable: blocked }}
        modifiersClassNames={{ unavailable: "rdp-unavailable" }}
        excludeDisabled
        showOutsideDays
        className="mx-auto w-fit"
        classNames={{
          month_caption: "mb-3 flex h-9 items-center justify-center font-extrabold text-ink",
          nav: "absolute right-0 top-0 flex h-9 items-center gap-1",
          button_previous: "grid h-8 w-8 place-items-center rounded-lg text-muted hover:bg-canvas",
          button_next: "grid h-8 w-8 place-items-center rounded-lg text-muted hover:bg-canvas",
          month_grid: "border-collapse",
          weekdays: "text-[11px] font-bold text-muted",
          weekday: "h-9 w-9 text-center",
          week: "",
          day: "p-0 text-center",
          day_button: "mx-auto grid h-9 w-9 place-items-center rounded-full text-xs font-semibold transition hover:bg-[#e7f4eb]",
          selected: "rdp-selected bg-accent text-white hover:bg-accent",
          range_start: "rdp-range_start rounded-full bg-accent text-white",
          range_end: "rdp-range_end rounded-full bg-accent text-white",
          range_middle: "rdp-range_middle bg-[#e7f4eb] text-accent",
          disabled: "rdp-disabled cursor-not-allowed text-[#c2c9c4] line-through hover:bg-transparent",
          outside: "rdp-outside text-[#aab3ad]",
          today: "font-black underline decoration-accent decoration-2 underline-offset-4",
        }}
      />
      <div className="mt-2 flex flex-wrap items-center justify-center gap-4 text-xs text-muted">
        <span className="flex items-center gap-1.5"><i className="h-3 w-3 rounded-full bg-[#e7f4eb]" /> Selected range</span>
        <span className="flex items-center gap-1.5"><i className="h-3 w-3 rounded-full bg-[#e3e7e4]" /> Unavailable</span>
      </div>
      <p className="mt-3 text-center text-xs text-muted">
        {startDate && !endDate
          ? "Choose your return date."
          : "Choose your pick-up and return dates. Unavailable days cannot be selected."}
      </p>
    </div>
  );
}

export function BookingWidget({ vehicle }) {
  const { isSignedIn, request, user } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [blockedRanges, setBlockedRanges] = useState([]);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [loading, setLoading] = useState(true);
  const [availabilityLoaded, setAvailabilityLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    const from = todayKey();
    const to = new Date(`${from}T00:00:00`);
    to.setDate(to.getDate() + 366);
    request(`/api/vehicles/${vehicle.id}/availability?from=${from}&to=${dateKey(to)}`)
      .then((response) => {
        if (active) {
          setBlockedRanges(response.blocked_ranges);
          setAvailabilityLoaded(true);
        }
      })
      .catch((loadError) => {
        if (active) setError(loadError.message || "Availability could not be loaded.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [request, vehicle.id]);

  const days = startDate && endDate ? dayNumber(endDate) - dayNumber(startDate) : 0;
  const rentalTotal = days * Number(vehicle.daily_rate || 0);
  const total = rentalTotal + Number(vehicle.deposit_amount || 0);

  async function submitBooking() {
    if (!isSignedIn) {
      navigate("/signin", { state: { from: location } });
      return;
    }
    if (!user?.phone_verified_at) {
      navigate("/verify-phone", { state: { from: location } });
      return;
    }
    setBusy(true);
    setError("");
    try {
      await request("/api/bookings", {
        method: "POST",
        body: jsonBody({
          vehicle_id: vehicle.id,
          start_date: startDate,
          end_date: endDate,
        }),
      });
      navigate("/bookings", { state: { bookingCreated: true } });
    } catch (bookingError) {
      setError(bookingError.message || "We couldn't create your booking.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mt-6">
      <div className="flex items-center gap-2 text-sm font-bold text-ink">
        <CalendarDays size={17} className="text-accent" />
        Select your dates
      </div>
      {loading ? (
        <div className="mt-4 rounded-2xl bg-canvas p-4 text-sm text-muted">Loading availability…</div>
      ) : (
        <BookingCalendar
          blockedRanges={blockedRanges}
          startDate={startDate}
          endDate={endDate}
          onSelect={(range) => {
            setError("");
            setStartDate(range?.from ? dateKey(range.from) : "");
            setEndDate(range?.to ? dateKey(range.to) : "");
          }}
        />
      )}
      {days > 0 && (
        <div className="mt-4 rounded-2xl bg-canvas p-4">
          <div className="flex justify-between text-xs text-muted">
            <span>{formatDate(startDate)} – {formatDate(endDate)}</span>
            <span>{days} {days === 1 ? "day" : "days"}</span>
          </div>
          <div className="mt-3 flex justify-between text-sm text-muted">
            <span>{days} × KES {Number(vehicle.daily_rate).toLocaleString("en-KE")}</span>
            <span>KES {rentalTotal.toLocaleString("en-KE")}</span>
          </div>
          <div className="mt-2 flex justify-between text-sm text-muted">
            <span>Refundable deposit</span>
            <span>KES {Number(vehicle.deposit_amount).toLocaleString("en-KE")}</span>
          </div>
          <div className="mt-3 flex justify-between border-t border-line pt-3 text-sm font-extrabold text-ink">
            <span>Total</span>
            <span>KES {total.toLocaleString("en-KE")}</span>
          </div>
        </div>
      )}
      {error && <p role="alert" className="mt-3 text-sm text-red-700">{error}</p>}
      {!isSignedIn ? (
        <Link to="/signin" state={{ from: location }} className="btn-primary mt-5 w-full">
          Book this car
        </Link>
      ) : !user?.phone_verified_at ? (
        <Link to="/verify-phone" state={{ from: location }} className="btn-primary mt-5 w-full">
          Verify phone to book
        </Link>
      ) : (
        <button
          type="button"
          disabled={!startDate || !endDate || loading || !availabilityLoaded || busy}
          onClick={submitBooking}
          className="btn-primary mt-5 w-full"
        >
          {busy ? "Creating booking…" : "Book this car"}
        </button>
      )}
      <p className="mt-3 flex items-center justify-center gap-1.5 text-xs text-muted">
        <Clock3 size={14} /> Unpaid bookings hold your dates for 30 minutes.
      </p>
    </div>
  );
}

export function MyBookingsPage() {
  const { isSignedIn, request, user } = useAuth();
  const location = useLocation();
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState(null);
  const [error, setError] = useState("");

  async function loadBookings() {
    setLoading(true);
    setError("");
    try {
      setBookings(await request("/api/bookings/me"));
    } catch (loadError) {
      setError(loadError.message || "Your bookings could not be loaded.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (isSignedIn) void loadBookings();
  }, [isSignedIn, user?.role]);

  if (!isSignedIn) return <Navigate to="/signin" replace state={{ from: location }} />;

  async function cancelBooking(bookingId) {
    setBusyId(bookingId);
    setError("");
    try {
      await request(`/api/bookings/${bookingId}/cancel`, { method: "POST" });
      await loadBookings();
    } catch (cancelError) {
      setError(cancelError.message || "This booking could not be cancelled.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <>
      <main className="mx-auto min-h-[65vh] max-w-5xl px-5 py-10 sm:px-8 sm:py-14">
        <p className="eyebrow">Your trips</p>
        <h1 className="mt-2 text-3xl font-black tracking-tight text-ink">My bookings</h1>
        <p className="mt-2 text-sm text-muted">Review your reservations and booking details.</p>
        {location.state?.bookingCreated && (
          <p role="status" className="mt-6 rounded-xl bg-[#e7f4eb] px-4 py-3 text-sm font-semibold text-accent">
            Booking created. Your dates are held for 30 minutes while payment is pending.
          </p>
        )}
        {error && <p role="alert" className="mt-6 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-800">{error}</p>}
        {loading ? (
          <div className="mt-8 rounded-2xl border border-line bg-white p-6 text-sm text-muted">Loading your bookings…</div>
        ) : bookings.length ? (
          <div className="mt-8 grid gap-4">
            {bookings.map((booking) => {
              const canCancel =
                booking.customer_id === user?.id &&
                ["pending", "confirmed"].includes(booking.status) &&
                booking.start_date > todayKey();
              return (
                <article key={booking.id} className="rounded-3xl border border-line bg-white p-5 shadow-soft sm:p-6">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <Link to={`/vehicles/${booking.vehicle.id}`} className="text-lg font-extrabold text-ink hover:text-accent">
                        {booking.vehicle.year} {booking.vehicle.make} {booking.vehicle.model}
                      </Link>
                      <p className="mt-1 text-sm text-muted">{formatDate(booking.start_date)} – {formatDate(booking.end_date)}</p>
                    </div>
                    <span className="rounded-full bg-[#fbf0dc] px-3 py-1.5 text-xs font-bold capitalize text-[#94630f]">
                      {booking.status}
                    </span>
                  </div>
                  <div className="mt-5 grid gap-2 border-t border-line pt-4 text-sm sm:grid-cols-3">
                    <p className="text-muted">Total <span className="ml-1 font-bold text-ink">KES {Number(booking.total_price).toLocaleString("en-KE")}</span></p>
                    <p className="text-muted">Deposit <span className="ml-1 font-bold text-ink">KES {Number(booking.deposit_amount).toLocaleString("en-KE")}</span></p>
                    <p className="text-muted">Payment <span className="ml-1 font-bold capitalize text-ink">{booking.deposit_paid ? "Paid" : "Unpaid"}</span></p>
                  </div>
                  {booking.status === "pending" && booking.expires_at && (
                    <p className="mt-3 flex items-center gap-1.5 text-xs text-muted">
                      <Clock3 size={14} /> Payment is due within 30 minutes of booking.
                    </p>
                  )}
                  {canCancel && (
                    <button
                      type="button"
                      disabled={busyId === booking.id}
                      onClick={() => cancelBooking(booking.id)}
                      className="btn-secondary mt-4 text-red-700"
                    >
                      {busyId === booking.id ? "Cancelling…" : "Cancel booking"}
                    </button>
                  )}
                </article>
              );
            })}
          </div>
        ) : (
          <div className="mt-8 rounded-3xl border border-dashed border-line bg-white px-6 py-12 text-center">
            <h2 className="text-lg font-extrabold text-ink">No bookings yet</h2>
            <p className="mt-2 text-sm text-muted">Once you reserve a car, it will appear here.</p>
            <Link to="/#cars" className="btn-primary mt-5">Explore cars</Link>
          </div>
        )}
      </main>
      <footer className="mt-20 border-t border-line bg-white">
        <div className="mx-auto max-w-7xl px-5 py-8 text-sm text-muted sm:px-8">CarHire Kenya</div>
      </footer>
    </>
  );
}

export function OwnerAvailabilityPage() {
  const { isSignedIn, request, user } = useAuth();
  const location = useLocation();
  const [vehicles, setVehicles] = useState([]);
  const [vehicleId, setVehicleId] = useState("");
  const [blocks, setBlocks] = useState([]);
  const [dates, setDates] = useState({ start_date: "", end_date: "", reason: "" });
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const selectedVehicle = vehicles.find((vehicle) => String(vehicle.id) === vehicleId);

  async function loadBlocks(selectedVehicleId) {
    if (!selectedVehicleId) {
      setBlocks([]);
      return;
    }
    setBlocks(await request(`/api/vehicles/${selectedVehicleId}/blocks`));
  }

  useEffect(() => {
    if (!isSignedIn || user?.role !== "owner") {
      setLoading(false);
      return;
    }
    let active = true;
    request("/api/owners/me/vehicles")
      .then((result) => {
        if (!active) return;
        setVehicles(result);
        if (result.length) setVehicleId(String(result[0].id));
      })
      .catch((loadError) => {
        if (active) setError(loadError.message || "Your vehicles could not be loaded.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [isSignedIn, request, user?.role]);

  useEffect(() => {
    let active = true;
    if (vehicleId) {
      request(`/api/vehicles/${vehicleId}/blocks`)
        .then((result) => {
          if (active) setBlocks(result);
        })
        .catch((loadError) => {
          if (active) setError(loadError.message || "Availability blocks could not be loaded.");
        });
    } else {
      setBlocks([]);
    }
    return () => {
      active = false;
    };
  }, [request, vehicleId]);

  if (!isSignedIn) return <Navigate to="/signin" replace state={{ from: location }} />;

  async function addBlock(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await request(`/api/vehicles/${vehicleId}/blocks`, {
        method: "POST",
        body: jsonBody(dates),
      });
      setDates({ start_date: "", end_date: "", reason: "" });
      await loadBlocks(vehicleId);
    } catch (blockError) {
      setError(blockError.message || "Those dates could not be blocked.");
    } finally {
      setBusy(false);
    }
  }

  async function removeBlock(blockId) {
    setBusy(true);
    setError("");
    try {
      await request(`/api/vehicles/${vehicleId}/blocks/${blockId}`, { method: "DELETE" });
      await loadBlocks(vehicleId);
    } catch (deleteError) {
      setError(deleteError.message || "This availability block could not be removed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <main className="mx-auto min-h-[65vh] max-w-5xl px-5 py-10 sm:px-8 sm:py-14">
        <p className="eyebrow">Manage your calendar</p>
        <h1 className="mt-2 text-3xl font-black tracking-tight text-ink">Block unavailable dates</h1>
        <p className="mt-2 text-sm leading-6 text-muted">
          Keep your calendar accurate when a vehicle is unavailable for personal use or maintenance.
        </p>
        {user?.role !== "owner" && (
          <div className="mt-8 rounded-2xl border border-line bg-white p-6 text-sm text-muted">
            This screen is available to vehicle owners.
          </div>
        )}
        {error && <p role="alert" className="mt-6 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-800">{error}</p>}
        {user?.role === "owner" && loading && (
          <div className="mt-8 rounded-2xl border border-line bg-white p-6 text-sm text-muted">Loading your vehicles…</div>
        )}
        {user?.role === "owner" && !loading && vehicles.length === 0 && (
          <div className="mt-8 rounded-2xl border border-line bg-white p-6 text-sm text-muted">You have no vehicles to manage yet.</div>
        )}
        {user?.role === "owner" && !loading && vehicles.length > 0 && (
          <>
            <label className="mt-8 block text-xs font-bold text-ink" htmlFor="availability-vehicle">Vehicle</label>
            <select
              id="availability-vehicle"
              className="field mt-2 max-w-xl"
              value={vehicleId}
              onChange={(event) => setVehicleId(event.target.value)}
            >
              {vehicles.map((vehicle) => (
                <option key={vehicle.id} value={vehicle.id}>
                  {vehicle.year} {vehicle.make} {vehicle.model} · {vehicle.plate}
                </option>
              ))}
            </select>
            <section className="mt-6 grid gap-6 lg:grid-cols-[.8fr_1.2fr]">
              <form onSubmit={addBlock} className="h-fit rounded-3xl border border-line bg-white p-5 shadow-soft">
                <h2 className="text-lg font-extrabold text-ink">Add unavailable dates</h2>
                <label className="mt-5 block text-xs font-bold text-ink" htmlFor="block-start-date">Start date</label>
                <input
                  id="block-start-date"
                  required
                  type="date"
                  min={todayKey()}
                  className="field mt-2"
                  value={dates.start_date}
                  onChange={(event) => setDates({ ...dates, start_date: event.target.value })}
                />
                <label className="mt-4 block text-xs font-bold text-ink" htmlFor="block-end-date">End date (exclusive)</label>
                <input
                  id="block-end-date"
                  required
                  type="date"
                  min={dates.start_date || todayKey()}
                  className="field mt-2"
                  value={dates.end_date}
                  onChange={(event) => setDates({ ...dates, end_date: event.target.value })}
                />
                <label className="mt-4 block text-xs font-bold text-ink" htmlFor="block-reason">Reason (optional)</label>
                <input
                  id="block-reason"
                  maxLength={500}
                  className="field mt-2"
                  placeholder="Maintenance or personal use"
                  value={dates.reason}
                  onChange={(event) => setDates({ ...dates, reason: event.target.value })}
                />
                <button
                  type="submit"
                  disabled={busy || !dates.start_date || !dates.end_date || dates.end_date <= dates.start_date}
                  className="btn-primary mt-5 w-full"
                >
                  {busy ? "Saving…" : "Block dates"}
                </button>
              </form>
              <section className="rounded-3xl border border-line bg-white p-5 shadow-soft">
                <h2 className="text-lg font-extrabold text-ink">Current blocks</h2>
                {blocks.length ? (
                  <ul className="mt-4 grid gap-3">
                    {blocks.map((block) => (
                      <li key={block.id} className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-canvas p-4">
                        <div>
                          <p className="text-sm font-bold text-ink">
                            {formatDate(block.start_date)} – {formatDate(block.end_date)}
                          </p>
                          {block.reason && <p className="mt-1 text-xs text-muted">{block.reason}</p>}
                        </div>
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => removeBlock(block.id)}
                          className="inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-bold text-red-700 hover:bg-red-50"
                        >
                          <Trash2 size={14} /> Unblock
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-4 rounded-2xl bg-canvas p-5 text-sm text-muted">No dates are blocked for this vehicle.</p>
                )}
              </section>
            </section>
            {selectedVehicle && (
              <OwnerLocationEditor
                key={selectedVehicle.id}
                vehicle={selectedVehicle}
                request={request}
                onSave={(updatedLocation) => {
                  setVehicles((current) =>
                    current.map((vehicle) =>
                      vehicle.id === selectedVehicle.id
                        ? { ...vehicle, ...updatedLocation }
                        : vehicle,
                    ),
                  );
                }}
              />
            )}
          </>
        )}
      </main>
      <footer className="mt-20 border-t border-line bg-white">
        <div className="mx-auto max-w-7xl px-5 py-8 text-sm text-muted sm:px-8">CarHire Kenya</div>
      </footer>
    </>
  );
}

function OwnerLocationEditor({ vehicle, request, onSave }) {
  const [location, setLocation] = useState({
    areaName: vehicle.area_name || "",
    latitude: vehicle.latitude,
    longitude: vehicle.longitude,
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function saveLocation(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await request(`/api/vehicles/${vehicle.id}`, {
        method: "PATCH",
        body: jsonBody({
          area_name: location.areaName,
          location: location.areaName,
          latitude: location.latitude,
          longitude: location.longitude,
        }),
      });
      onSave({
        area_name: location.areaName,
        location: location.areaName,
        latitude: location.latitude,
        longitude: location.longitude,
      });
    } catch (saveError) {
      setError(saveError.message || "Your pickup location could not be saved.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={saveLocation} className="mt-8 rounded-3xl border border-line bg-white p-5 shadow-soft">
      <h2 className="text-lg font-extrabold text-ink">Edit pickup location</h2>
      <p className="mt-1 text-sm text-muted">The area is public; your exact coordinates remain private.</p>
      <div className="mt-5">
        <LocationPicker
          request={request}
          areaName={location.areaName}
          latitude={location.latitude}
          longitude={location.longitude}
          onAreaNameChange={(areaName) => setLocation((current) => ({ ...current, areaName }))}
          onCoordinatesChange={(latitude, longitude) =>
            setLocation((current) => ({ ...current, latitude, longitude }))
          }
        />
      </div>
      {error && <p role="alert" className="mt-3 text-sm text-red-700">{error}</p>}
      <button type="submit" disabled={busy || !location.areaName.trim()} className="btn-primary mt-5">
        {busy ? "Saving…" : "Save pickup location"}
      </button>
    </form>
  );
}
