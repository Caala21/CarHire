import { useEffect, useMemo, useState } from "react";
import { CalendarDays, ChevronLeft, ChevronRight, Clock3 } from "lucide-react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "./auth.jsx";
import { jsonBody } from "./lib/api.js";

function dateKey(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function dayNumber(value) {
  return Date.parse(`${value}T00:00:00Z`) / 86400000;
}

function todayKey() {
  return dateKey(new Date());
}

function formatDate(value) {
  return new Date(`${value}T00:00:00`).toLocaleDateString("en-KE", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function calendarCells(month) {
  const firstDay = new Date(month.getFullYear(), month.getMonth(), 1);
  const gridStart = new Date(firstDay);
  gridStart.setDate(firstDay.getDate() - firstDay.getDay());
  return Array.from({ length: 42 }, (_, index) => {
    const day = new Date(gridStart);
    day.setDate(gridStart.getDate() + index);
    return day;
  });
}

function rangeOverlaps(blockedRanges, startDate, endDate) {
  return blockedRanges.some(
    (range) => range.start_date < endDate && range.end_date > startDate,
  );
}

function BookingCalendar({ blockedRanges, startDate, endDate, onSelect }) {
  const [month, setMonth] = useState(() => {
    const current = new Date();
    return new Date(current.getFullYear(), current.getMonth(), 1);
  });
  const cells = useMemo(() => calendarCells(month), [month]);
  const today = todayKey();

  function isDisabled(day) {
    const key = dateKey(day);
    if (key < today) return true;
    if (!startDate || endDate) {
      return blockedRanges.some(
        (range) => range.start_date <= key && key < range.end_date,
      );
    }
    return key <= startDate || rangeOverlaps(blockedRanges, startDate, key);
  }

  return (
    <div className="mt-4 rounded-2xl border border-line p-4">
      <div className="flex items-center justify-between">
        <button
          type="button"
          aria-label="Previous month"
          onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() - 1, 1))}
          className="grid h-9 w-9 place-items-center rounded-lg text-muted hover:bg-canvas"
        >
          <ChevronLeft size={18} />
        </button>
        <h3 className="text-sm font-extrabold text-ink">
          {month.toLocaleDateString("en-KE", { month: "long", year: "numeric" })}
        </h3>
        <button
          type="button"
          aria-label="Next month"
          onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() + 1, 1))}
          className="grid h-9 w-9 place-items-center rounded-lg text-muted hover:bg-canvas"
        >
          <ChevronRight size={18} />
        </button>
      </div>
      <div className="mt-3 grid grid-cols-7 text-center text-[11px] font-bold text-muted">
        {["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"].map((day) => (
          <span key={day} className="py-2">{day}</span>
        ))}
      </div>
      <div className="grid grid-cols-7 gap-y-1">
        {cells.map((day) => {
          const key = dateKey(day);
          const inMonth = day.getMonth() === month.getMonth();
          const selected = key === startDate || key === endDate;
          const inRange = startDate && endDate && key > startDate && key < endDate;
          return (
            <button
              key={key}
              type="button"
              disabled={isDisabled(day)}
              aria-label={day.toLocaleDateString("en-KE", {
                day: "numeric",
                month: "long",
                year: "numeric",
              })}
              aria-pressed={selected}
              onClick={() => onSelect(key)}
              className={`mx-auto grid h-9 w-9 place-items-center rounded-full text-xs font-semibold transition ${
                selected
                  ? "bg-accent text-white"
                  : isDisabled(day)
                    ? "cursor-not-allowed text-[#c2c9c4] line-through"
                    : inRange
                      ? "bg-[#e7f4eb] text-accent"
                      : inMonth
                        ? "text-ink hover:bg-[#e7f4eb]"
                        : "text-[#aab3ad] hover:bg-[#e7f4eb]"
              }`}
            >
              {day.getDate()}
            </button>
          );
        })}
      </div>
      <p className="mt-3 text-xs text-muted">
        {startDate && !endDate
          ? "Choose your checkout date."
          : "Choose a start date, then a checkout date. Unavailable days are crossed out."}
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
    const end = new Date(`${from}T00:00:00`);
    end.setDate(end.getDate() + 366);
    request(
      `/api/vehicles/${vehicle.id}/availability?from=${from}&to=${dateKey(end)}`,
    )
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

  function selectDate(value) {
    setError("");
    if (!startDate || endDate || value <= startDate) {
      setStartDate(value);
      setEndDate("");
    } else {
      setEndDate(value);
    }
  }

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
          onSelect={selectDate}
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
        <Link
          to="/signin"
          state={{ from: location }}
          className="btn-primary mt-5 w-full"
        >
          Book this car
        </Link>
      ) : !user?.phone_verified_at ? (
        <Link
          to="/verify-phone"
          state={{ from: location }}
          className="btn-primary mt-5 w-full"
        >
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
                      <Link
                        to={`/vehicles/${booking.vehicle.id}`}
                        className="text-lg font-extrabold text-ink hover:text-accent"
                      >
                        {booking.vehicle.year} {booking.vehicle.make} {booking.vehicle.model}
                      </Link>
                      <p className="mt-1 text-sm text-muted">
                        {formatDate(booking.start_date)} – {formatDate(booking.end_date)}
                      </p>
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
