import { useEffect, useRef, useState } from "react";
import {
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  BadgeCheck,
  CalendarDays,
  CarFront,
  Check,
  ChevronDown,
  CircleCheck,
  Clock3,
  Fuel,
  Heart,
  Eye,
  EyeOff,
  MapPin,
  Menu,
  ShieldCheck,
  Sparkles,
  UsersRound,
  WalletCards,
  X,
} from "lucide-react";
import {
  Link,
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";
import { useAuth } from "./auth.jsx";
import { apiUrl, jsonBody } from "./lib/api.js";
import { AdminRoute, DemoPage } from "./admin.jsx";

const fallbackPhoto =
  "https://images.unsplash.com/photo-1503376780353-7e6692767b70?auto=format&fit=crop&w=1200&q=85";
const samplePhotos = [
  "https://images.unsplash.com/photo-1503376780353-7e6692767b70?auto=format&fit=crop&w=1400&q=85",
  "https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?auto=format&fit=crop&w=1400&q=85",
  "https://images.unsplash.com/photo-1507136566006-cfc505b114fc?auto=format&fit=crop&w=1400&q=85",
];
const formatPrice = (amount) =>
  new Intl.NumberFormat("en-KE", { maximumFractionDigits: 0 }).format(Number(amount || 0));
const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;

function GoogleSignInButton({ onCredential, disabled }) {
  const buttonRef = useRef(null);
  const onCredentialRef = useRef(onCredential);
  const [scriptError, setScriptError] = useState("");
  onCredentialRef.current = onCredential;

  useEffect(() => {
    if (!googleClientId) return undefined;
    let active = true;
    const script = document.getElementById("google-identity-services");
    const renderButton = () => {
      if (!active || !buttonRef.current || !window.google?.accounts?.id) return;
      window.google.accounts.id.initialize({
        client_id: googleClientId,
        callback: ({ credential }) => {
          if (credential) void onCredentialRef.current(credential);
        },
      });
      window.google.accounts.id.renderButton(buttonRef.current, {
        theme: "outline",
        size: "large",
        text: "continue_with",
        shape: "rectangular",
        width: 400,
      });
    };
    const handleScriptError = () => {
      if (active) setScriptError("Google sign-in couldn't load. Please try again later.");
    };

    if (window.google?.accounts?.id) {
      renderButton();
    } else {
      script?.addEventListener("load", renderButton);
      script?.addEventListener("error", handleScriptError);
    }

    return () => {
      active = false;
      script?.removeEventListener("load", renderButton);
      script?.removeEventListener("error", handleScriptError);
    };
  }, []);

  return (
    <div>
      {googleClientId ? (
        <div
          ref={buttonRef}
          aria-busy={disabled}
          className={`flex min-h-10 justify-center ${disabled ? "pointer-events-none opacity-50" : ""}`}
        />
      ) : (
        <p role="status" className="text-center text-xs text-muted">
          Google sign-in isn't configured yet.
        </p>
      )}
      {scriptError && <p role="alert" className="mt-2 text-center text-xs text-red-700">{scriptError}</p>}
    </div>
  );
}

function Logo({ light = false }) {
  return (
    <Link to="/" className={`inline-flex items-center gap-2.5 ${light ? "text-white" : "text-ink"}`}>
      <span className="grid h-10 w-10 place-items-center rounded-2xl bg-accent text-white">
        <CarFront size={22} strokeWidth={2.2} />
      </span>
      <span className="text-[19px] font-extrabold tracking-tight">carhire<span className="text-accent">.</span></span>
    </Link>
  );
}

function SiteHeader() {
  const { isSignedIn, user, signOut } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  function handleSignOut() {
    signOut();
    setMenuOpen(false);
    navigate("/");
  }

  return (
    <header className="relative z-20 border-b border-line/80 bg-white/90 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4 sm:px-8">
        <Logo />
        <nav className="hidden items-center gap-8 text-sm font-semibold text-muted md:flex">
          <a href="/#cars" className="transition hover:text-ink">Explore cars</a>
          <a href="/#how-it-works" className="transition hover:text-ink">How it works</a>
          <Link to="/signup?intent=list" className="transition hover:text-ink">List your car</Link>
          {user?.role === "admin" && <Link to="/admin" className="transition hover:text-ink">Admin</Link>}
        </nav>
        <div className="hidden items-center gap-3 md:flex">
          {isSignedIn ? (
            <div className="relative">
              <button
                type="button"
                aria-expanded={menuOpen}
                aria-haspopup="menu"
                onClick={() => setMenuOpen((open) => !open)}
                className="inline-flex max-w-56 items-center gap-2 rounded-xl px-3 py-2 text-sm font-bold text-ink hover:bg-canvas"
              >
                <span className="truncate">{user?.full_name}</span>
                <ChevronDown size={16} className="shrink-0 text-muted" />
              </button>
              {menuOpen && (
                <div role="menu" className="absolute right-0 top-full z-30 mt-2 grid min-w-48 gap-1 rounded-2xl border border-line bg-white p-2 shadow-card">
                  <Link role="menuitem" to="/owner" onClick={() => setMenuOpen(false)} className="rounded-xl px-3 py-2.5 text-sm font-semibold hover:bg-canvas">My cars</Link>
                  {user?.role === "admin" && <Link role="menuitem" to="/admin" onClick={() => setMenuOpen(false)} className="rounded-xl px-3 py-2.5 text-sm font-semibold hover:bg-canvas">Admin</Link>}
                  <button role="menuitem" onClick={handleSignOut} className="rounded-xl px-3 py-2.5 text-left text-sm font-semibold text-red-700 hover:bg-red-50">Sign out</button>
                </div>
              )}
            </div>
          ) : (
            <>
              <Link to="/signin" className="px-3 py-2 text-sm font-bold text-ink transition hover:text-accent">Sign in</Link>
              <Link to="/signup" className="px-3 py-2 text-sm font-bold text-ink transition hover:text-accent">Sign up</Link>
              <Link to="/signup?intent=list" className="btn-primary !py-2.5">List your car</Link>
            </>
          )}
        </div>
        <button
          className="grid h-10 w-10 place-items-center rounded-xl border border-line text-ink md:hidden"
          aria-label={menuOpen ? "Close menu" : "Open menu"}
          onClick={() => setMenuOpen(!menuOpen)}
        >
          {menuOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>
      {menuOpen && (
        <nav className="absolute left-0 right-0 top-full grid gap-1 border-b border-line bg-white p-4 shadow-soft md:hidden">
          <a href="/#cars" onClick={() => setMenuOpen(false)} className="rounded-xl px-3 py-3 text-sm font-semibold">Explore cars</a>
          <a href="/#how-it-works" onClick={() => setMenuOpen(false)} className="rounded-xl px-3 py-3 text-sm font-semibold">How it works</a>
          <Link to="/signup?intent=list" onClick={() => setMenuOpen(false)} className="rounded-xl px-3 py-3 text-sm font-semibold text-accent">List your car</Link>
          {isSignedIn ? (
            <>
              <p className="px-3 pt-2 text-xs font-bold uppercase tracking-wider text-muted">{user?.full_name}</p>
              <Link to="/owner" onClick={() => setMenuOpen(false)} className="rounded-xl px-3 py-3 text-sm font-semibold">My cars</Link>
              {user?.role === "admin" && <Link to="/admin" onClick={() => setMenuOpen(false)} className="rounded-xl px-3 py-3 text-sm font-semibold">Admin</Link>}
              <button onClick={handleSignOut} className="rounded-xl px-3 py-3 text-left text-sm font-semibold text-red-700">Sign out</button>
            </>
          ) : (
            <>
              <Link to="/signin" onClick={() => setMenuOpen(false)} className="rounded-xl px-3 py-3 text-sm font-semibold">Sign in</Link>
              <Link to="/signup" onClick={() => setMenuOpen(false)} className="rounded-xl px-3 py-3 text-sm font-semibold">Sign up</Link>
            </>
          )}
        </nav>
      )}
    </header>
  );
}

function Footer() {
  return (
    <footer className="mt-20 border-t border-line bg-white">
      <div className="mx-auto flex max-w-7xl flex-col gap-5 px-5 py-8 text-sm text-muted sm:flex-row sm:items-center sm:justify-between sm:px-8">
        <Logo />
        <p>Made for the way Kenya moves.</p>
        <p>© {new Date().getFullYear()} CarHire Kenya</p>
      </div>
    </footer>
  );
}

function Alert({ children, onRetry }) {
  return (
    <div role="alert" className="flex flex-col gap-3 rounded-2xl border border-red-200 bg-red-50 px-4 py-4 text-sm text-red-800 sm:flex-row sm:items-center sm:justify-between">
      <span>{children}</span>
      {onRetry && <button className="self-start font-bold underline underline-offset-2 sm:self-auto" onClick={onRetry}>Try again</button>}
    </div>
  );
}

function LoadingCard() {
  return (
    <div className="overflow-hidden rounded-3xl border border-line bg-white">
      <div className="skeleton h-52" />
      <div className="space-y-3 p-5">
        <div className="skeleton h-5 w-2/3 rounded-full" />
        <div className="skeleton h-4 w-1/3 rounded-full" />
        <div className="skeleton h-9 w-full rounded-xl" />
      </div>
    </div>
  );
}

function VehicleCard({ vehicle, index = 0 }) {
  const photo = vehicle.photos?.[0] ? apiUrl(vehicle.photos[0]) : samplePhotos[index % samplePhotos.length];
  return (
    <Link to={`/vehicles/${vehicle.id}`} className="group overflow-hidden rounded-3xl border border-line bg-white shadow-soft transition duration-300 hover:-translate-y-1 hover:shadow-card">
      <div className="relative h-52 overflow-hidden bg-[#edf1ed]">
        <img src={photo} alt={`${vehicle.year} ${vehicle.make} ${vehicle.model}`} className="h-full w-full object-cover transition duration-500 group-hover:scale-105" onError={(event) => { event.currentTarget.src = fallbackPhoto; }} />
        <span className="absolute left-4 top-4 inline-flex items-center gap-1.5 rounded-full bg-white/95 px-3 py-1.5 text-xs font-bold text-accent shadow-sm">
          <BadgeCheck size={14} /> Verified
        </span>
        <button
          className="absolute right-4 top-4 grid h-9 w-9 place-items-center rounded-full bg-white/90 text-ink transition hover:text-accent"
          aria-label="Save vehicle"
          onClick={(event) => event.preventDefault()}
        >
          <Heart size={17} />
        </button>
      </div>
      <div className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 className="text-lg font-extrabold tracking-tight text-ink">{vehicle.year} {vehicle.make} {vehicle.model}</h3>
            <p className="mt-1 flex items-center gap-1.5 text-sm text-muted"><MapPin size={14} /> {vehicle.location || "Kenya"}</p>
          </div>
          <p className="shrink-0 text-right text-sm font-extrabold text-ink">KES {formatPrice(vehicle.daily_rate)}<span className="block text-xs font-medium text-muted">per day</span></p>
        </div>
        <div className="mt-4 flex items-center gap-4 border-t border-line pt-4 text-xs font-semibold text-muted">
          <span className="flex items-center gap-1.5"><UsersRound size={14} /> {vehicle.seats} seats</span>
          <span>{vehicle.transmission}</span>
          <span>{vehicle.fuel_type}</span>
        </div>
      </div>
    </Link>
  );
}

function LandingPage() {
  const { request } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [vehicles, setVehicles] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [location, setLocation] = useState(searchParams.get("location") || "");
  const [filters, setFilters] = useState(searchParams.get("location") || "");
  const [assistantQuery, setAssistantQuery] = useState("");
  const [assistantMessage, setAssistantMessage] = useState("");
  const [assistantResult, setAssistantResult] = useState(null);
  const [assistantLoading, setAssistantLoading] = useState(false);
  const [assistantError, setAssistantError] = useState("");

  async function loadVehicles() {
    setLoading(true);
    setError("");
    try {
      const query = new URLSearchParams({ limit: "12" });
      if (filters.trim()) query.set("location", filters.trim());
      const page = await request(`/api/vehicles?${query.toString()}`);
      setVehicles(page.items);
      setTotal(page.total);
    } catch (loadError) {
      setError(loadError.message || "We couldn't load cars right now.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadVehicles();
  }, [filters]);

  function search(event) {
    event.preventDefault();
    const value = location.trim();
    setFilters(value);
    setSearchParams(value ? { location: value } : {});
    document.getElementById("cars")?.scrollIntoView({ behavior: "smooth" });
  }

  async function searchWithAssistant(message) {
    const query = message.trim();
    if (!query) return;
    setAssistantMessage(query);
    setAssistantLoading(true);
    setAssistantError("");
    setAssistantResult(null);
    try {
      const result = await request("/api/assistant/search", {
        method: "POST",
        body: jsonBody({ message: query }),
      });
      setAssistantResult(result);
    } catch (searchError) {
      setAssistantError(searchError.message || "We couldn't search for cars right now.");
    } finally {
      setAssistantLoading(false);
    }
  }

  return (
    <>
      <main>
        <section className="relative overflow-hidden bg-[#f0f5f0]">
          <div className="absolute -right-32 -top-32 h-[28rem] w-[28rem] rounded-full bg-[#dceade] blur-3xl" />
          <div className="relative mx-auto grid max-w-7xl items-center gap-9 px-5 pb-14 pt-12 sm:px-8 sm:pb-20 sm:pt-16 lg:grid-cols-[1.03fr_.97fr] lg:gap-8 lg:py-20">
            <div className="max-w-xl">
              <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-[#d6e4d7] bg-white/75 px-3.5 py-2 text-xs font-bold text-accent">
                <Sparkles size={14} /> Your next journey starts here
              </div>
              <h1 className="text-[2.8rem] font-black leading-[1.06] tracking-[-0.055em] text-ink sm:text-6xl">
                Rent or list a car <span className="text-accent">in Kenya.</span>
              </h1>
              <p className="mt-5 max-w-lg text-base leading-7 text-muted sm:text-lg">
                Find a ride for the weekend, or turn the car you love into a little extra income. Easy, trusted, and all in one place.
              </p>
              <form onSubmit={search} className="mt-8 flex flex-col gap-3 rounded-[1.35rem] bg-white p-3 shadow-card sm:flex-row sm:items-center">
                <label className="flex min-w-0 flex-1 items-center gap-3 px-2">
                  <MapPin className="shrink-0 text-accent" size={20} />
                  <span className="min-w-0 flex-1">
                    <span className="block text-[11px] font-bold uppercase tracking-[.12em] text-muted">Pick-up location</span>
                    <input value={location} onChange={(event) => setLocation(event.target.value)} placeholder="Where are you headed?" className="w-full border-0 bg-transparent py-1 text-sm font-semibold text-ink outline-none placeholder:font-normal placeholder:text-[#a3ada6]" />
                  </span>
                  <ChevronDown size={16} className="text-muted" />
                </label>
                <button className="btn-primary min-h-12 sm:min-w-36" type="submit">Find a car <ArrowRight size={17} /></button>
              </form>
              <div className="mt-5 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs font-semibold text-muted">
                <span className="flex items-center gap-1.5"><ShieldCheck size={15} className="text-accent" /> Trusted local owners</span>
                <span className="flex items-center gap-1.5"><CircleCheck size={15} className="text-accent" /> No hidden fees</span>
              </div>
            </div>
            <div className="relative mx-auto w-full max-w-xl">
              <div className="absolute -left-3 top-12 z-10 rounded-2xl bg-white p-3.5 shadow-card sm:-left-5 sm:p-4">
                <div className="flex items-center gap-3">
                  <span className="grid h-10 w-10 place-items-center rounded-xl bg-[#e6f4eb] text-accent"><ShieldCheck size={21} /></span>
                  <span><span className="block text-xs font-bold text-ink">Your trip, covered</span><span className="mt-0.5 block text-[11px] text-muted">Reliable from start to finish</span></span>
                </div>
              </div>
              <div className="relative h-[18rem] overflow-hidden rounded-[2rem] shadow-card sm:h-[24rem] lg:h-[29rem]">
                <img src="https://images.unsplash.com/photo-1549317661-bd32c8ce0db2?auto=format&fit=crop&w=1400&q=85" alt="A car ready for a road trip" className="h-full w-full object-cover" />
                <div className="absolute inset-0 bg-gradient-to-t from-[#101d17]/50 via-transparent to-transparent" />
                <div className="absolute bottom-5 left-5 right-5 flex items-end justify-between text-white sm:bottom-7 sm:left-7 sm:right-7">
                  <div><p className="text-xs font-semibold text-white/75">A better way to get around</p><p className="mt-1 text-xl font-extrabold">The road is yours.</p></div>
                  <span className="grid h-11 w-11 place-items-center rounded-full bg-white/20 backdrop-blur"><ArrowDown size={19} /></span>
                </div>
              </div>
              <div className="absolute -bottom-4 right-3 rounded-2xl bg-white px-4 py-3 shadow-card sm:-right-4 sm:px-5 sm:py-4">
                <p className="text-[11px] font-bold uppercase tracking-wider text-muted">Made for Kenya</p>
                <p className="mt-1 text-sm font-extrabold text-ink">KES · M-Pesa · Karibu</p>
              </div>
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-5 py-12 sm:px-8 sm:py-16" aria-labelledby="assistant-search-title">
          <div className="mx-auto max-w-4xl">
            <div className="mb-6 text-center">
              <p className="eyebrow">Search with a little help</p>
              <h2 id="assistant-search-title" className="section-title mt-3">Tell us what you need.</h2>
              <p className="mt-2 text-sm text-muted">Describe your ideal car, and we’ll find matching listings.</p>
            </div>
            <div className="rounded-3xl border border-line bg-white p-4 shadow-soft sm:p-6">
              <form
                onSubmit={(event) => {
                  event.preventDefault();
                  searchWithAssistant(assistantQuery);
                }}
                className="flex flex-col gap-3 sm:flex-row"
              >
                <label className="flex min-h-12 min-w-0 flex-1 items-center gap-3 rounded-xl border border-line px-4">
                  <Sparkles className="shrink-0 text-accent" size={18} />
                  <input
                    value={assistantQuery}
                    onChange={(event) => setAssistantQuery(event.target.value)}
                    placeholder="Try: automatic SUV in Nakuru under 8000"
                    maxLength={2000}
                    className="w-full border-0 bg-transparent py-3 text-sm text-ink outline-none placeholder:text-[#a3ada6]"
                    aria-label="Describe the car you are looking for"
                  />
                </label>
                <button className="btn-primary sm:min-w-36" type="submit" disabled={assistantLoading || !assistantQuery.trim()}>
                  {assistantLoading ? <><Spinner /> Searching</> : <>Find a car <ArrowRight size={17} /></>}
                </button>
              </form>

              {assistantMessage && (
                <div className="mt-5 space-y-3" aria-live="polite">
                  <p className="ml-auto w-fit max-w-[90%] rounded-2xl rounded-br-sm bg-[#e7f4eb] px-4 py-3 text-sm font-semibold text-ink">
                    {assistantMessage}
                  </p>
                  {assistantLoading && (
                    <p className="flex w-fit items-center gap-2 rounded-2xl rounded-bl-sm bg-canvas px-4 py-3 text-sm text-muted">
                      <Spinner /> Looking through available cars…
                    </p>
                  )}
                  {assistantError && (
                    <div className="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-800" role="alert">
                      <p>{assistantError}</p>
                      <button className="mt-2 font-bold underline underline-offset-2" onClick={() => searchWithAssistant(assistantMessage)}>
                        Try again
                      </button>
                    </div>
                  )}
                  {assistantResult && (
                    <>
                      <p className="w-fit max-w-[90%] rounded-2xl rounded-bl-sm bg-canvas px-4 py-3 text-sm leading-6 text-ink">
                        {assistantResult.reply}
                      </p>
                      {assistantResult.vehicles.length ? (
                        <div className="grid gap-5 pt-2 sm:grid-cols-2 lg:grid-cols-3">
                          {assistantResult.vehicles.map((vehicle, index) => (
                            <VehicleCard key={vehicle.id} vehicle={vehicle} index={index} />
                          ))}
                        </div>
                      ) : (
                        <p className="rounded-2xl border border-dashed border-line px-4 py-5 text-center text-sm text-muted">
                          No matching cars yet. Try another make, model, or location.
                        </p>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        </section>

        <section id="how-it-works" className="mx-auto max-w-7xl px-5 py-14 sm:px-8 sm:py-20">
          <div className="mb-8 max-w-xl">
            <p className="eyebrow">Good journeys, all around</p>
            <h2 className="section-title mt-3">Car hire that feels <span className="text-accent">easy.</span></h2>
            <p className="mt-3 leading-7 text-muted">We keep the important things clear, so you can focus on where you’re going.</p>
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            <BenefitCard icon={<BadgeCheck size={21} />} title="Verified owners" text="Every listing is reviewed, so you know who you’re meeting." color="green" />
            <BenefitCard icon={<WalletCards size={21} />} title="M-Pesa payments" text="Simple, familiar payments that work for the way you travel." color="sand" />
            <BenefitCard icon={<ShieldCheck size={21} />} title="Insured cars" text="Browse vehicles with current insurance and inspection details." color="lavender" />
          </div>
        </section>

        <section id="cars" className="bg-white">
          <div className="mx-auto max-w-7xl px-5 py-14 sm:px-8 sm:py-20">
            <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="eyebrow">Handpicked for you</p>
                <h2 className="section-title mt-3">Find your next <span className="text-accent">ride.</span></h2>
                <p className="mt-2 text-sm text-muted">{filters ? `Showing cars near “${filters}”` : "A few good reasons to get out and go."}</p>
              </div>
              <Link to="/signup?intent=list" className="btn-secondary w-fit">List your car <ArrowRight size={16} /></Link>
            </div>
            {error && <Alert onRetry={loadVehicles}>{error}</Alert>}
            {loading ? (
              <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">{[0, 1, 2].map((item) => <LoadingCard key={item} />)}</div>
            ) : !error && vehicles.length ? (
              <>
                <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">{vehicles.map((vehicle, index) => <VehicleCard key={vehicle.id} vehicle={vehicle} index={index} />)}</div>
                {total > vehicles.length && <p className="mt-6 text-center text-sm text-muted">Showing {vehicles.length} of {total} available cars.</p>}
              </>
            ) : !error ? (
              <div className="rounded-3xl border border-dashed border-line bg-canvas px-6 py-12 text-center">
                <span className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-white text-accent shadow-soft"><CarFront size={25} /></span>
                <h3 className="mt-4 text-lg font-extrabold text-ink">No cars found just yet</h3>
                <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted">{filters ? "Try another location, or clear your search to see all available cars." : "We’re getting the keys ready. Check back soon, or be the first to list a car."}</p>
                {filters ? <button className="btn-secondary mx-auto mt-5" onClick={() => { setLocation(""); setFilters(""); setSearchParams({}); }}>Clear search</button> : <Link to="/signup?intent=list" className="btn-primary mx-auto mt-5">List your car <ArrowRight size={16} /></Link>}
              </div>
            ) : null}
          </div>
        </section>
        <section className="mx-auto max-w-7xl px-5 py-14 sm:px-8 sm:py-20">
          <div className="overflow-hidden rounded-[2rem] bg-[#123d2e] px-6 py-10 text-white sm:px-10 sm:py-12 lg:flex lg:items-center lg:justify-between">
            <div className="max-w-xl">
              <p className="text-xs font-bold uppercase tracking-[.16em] text-[#98d6b3]">Got a car sitting idle?</p>
              <h2 className="mt-3 text-3xl font-black tracking-tight sm:text-4xl">Let it take someone somewhere.</h2>
              <p className="mt-3 max-w-lg text-sm leading-6 text-white/70">Apply in a few simple steps. We’ll review your details and help you get your car ready to rent.</p>
            </div>
            <Link to="/signup?intent=list" className="mt-7 inline-flex min-h-12 items-center justify-center gap-2 rounded-xl bg-white px-5 text-sm font-extrabold text-[#123d2e] transition hover:bg-[#eaf5ee] lg:mt-0">List your car <ArrowRight size={16} /></Link>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}

function BenefitCard({ icon, title, text, color }) {
  const colors = {
    green: "bg-[#e7f4eb] text-accent",
    sand: "bg-[#fbf0dc] text-[#b77b13]",
    lavender: "bg-[#f0ebfb] text-[#7459b4]",
  };
  return (
    <article className="rounded-3xl border border-line bg-white p-6 transition hover:shadow-soft sm:p-7">
      <span className={`grid h-12 w-12 place-items-center rounded-2xl ${colors[color]}`}>{icon}</span>
      <h3 className="mt-5 text-lg font-extrabold text-ink">{title}</h3>
      <p className="mt-2 text-sm leading-6 text-muted">{text}</p>
    </article>
  );
}

function VehicleDetailPage() {
  const { id } = useParams();
  const { request } = useAuth();
  const [vehicle, setVehicle] = useState(null);
  const [selected, setSelected] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const photos = vehicle?.photos?.map(apiUrl) || [];

  async function loadVehicle() {
    setLoading(true);
    setError("");
    try {
      setVehicle(await request(`/api/vehicles/${id}`));
      setSelected(0);
    } catch (loadError) {
      setError(loadError.message || "This car is unavailable right now.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadVehicle(); }, [id]);

  if (loading) {
    return <><main className="mx-auto min-h-[65vh] max-w-7xl px-5 py-10 sm:px-8"><div className="skeleton h-[24rem] rounded-3xl" /><div className="skeleton mt-6 h-10 w-1/2 rounded-full" /></main><Footer /></>;
  }
  if (error || !vehicle) {
    return <><main className="mx-auto min-h-[65vh] max-w-3xl px-5 py-16 sm:px-8"><Link to="/" className="inline-flex items-center gap-2 text-sm font-bold text-accent"><ArrowLeft size={16} /> Back to cars</Link><div className="mt-8"><Alert onRetry={loadVehicle}>{error || "Vehicle not found."}</Alert></div></main><Footer /></>;
  }

  const detailItems = [
    { icon: <UsersRound size={19} />, label: "Seats", value: `${vehicle.seats} passengers` },
    { icon: <CarFront size={19} />, label: "Transmission", value: vehicle.transmission },
    { icon: <Fuel size={19} />, label: "Fuel", value: vehicle.fuel_type },
    { icon: <MapPin size={19} />, label: "Pick-up", value: vehicle.location || "Kenya" },
    { icon: <CalendarDays size={19} />, label: "Year", value: vehicle.year },
  ];

  return (
    <>
      <main className="mx-auto max-w-7xl px-5 py-8 sm:px-8 sm:py-12">
        <Link to="/" className="mb-6 inline-flex items-center gap-2 text-sm font-bold text-muted transition hover:text-accent"><ArrowLeft size={16} /> All cars</Link>
        <div className="grid gap-8 lg:grid-cols-[1.35fr_.65fr]">
          <div>
            {photos.length ? (
              <div className="overflow-hidden rounded-3xl bg-[#edf1ed]">
                <img src={photos[selected] || fallbackPhoto} alt={`${vehicle.make} ${vehicle.model}`} className="h-[18rem] w-full object-cover sm:h-[27rem]" onError={(event) => { event.currentTarget.src = fallbackPhoto; }} />
              </div>
            ) : (
              <div className="flex h-[18rem] flex-col items-center justify-center rounded-3xl border border-dashed border-line bg-canvas text-center sm:h-[27rem]">
                <span className="grid h-14 w-14 place-items-center rounded-2xl bg-white text-accent shadow-soft"><CarFront size={27} /></span>
                <p className="mt-4 font-extrabold text-ink">Photos coming soon</p>
                <p className="mt-1 text-sm text-muted">This vehicle doesn’t have photos yet.</p>
              </div>
            )}
            {photos.length > 1 && <div className="mt-3 grid grid-cols-3 gap-3">{photos.slice(0, 3).map((photo, index) => <button key={photo} onClick={() => setSelected(index)} className={`overflow-hidden rounded-2xl ${selected === index ? "ring-2 ring-accent ring-offset-2" : ""}`}><img src={photo} alt={`View ${index + 1}`} className="h-24 w-full object-cover sm:h-32" onError={(event) => { event.currentTarget.src = fallbackPhoto; }} /></button>)}</div>}
            <div className="mt-8">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-[#e7f4eb] px-3 py-1.5 text-xs font-bold text-accent"><BadgeCheck size={14} /> Verified listing</span>
              <h1 className="mt-4 text-3xl font-black tracking-tight text-ink sm:text-4xl">{vehicle.year} {vehicle.make} {vehicle.model}</h1>
              <p className="mt-2 flex items-center gap-1.5 text-sm text-muted"><MapPin size={16} /> {vehicle.location || "Kenya"}</p>
              <div className="mt-7 grid grid-cols-2 gap-3 sm:grid-cols-3">{detailItems.map((item) => <div key={item.label} className="rounded-2xl border border-line p-4"><span className="text-accent">{item.icon}</span><p className="mt-3 text-xs font-semibold text-muted">{item.label}</p><p className="mt-1 font-bold capitalize text-ink">{item.value}</p></div>)}</div>
            </div>
          </div>
          <aside className="h-fit rounded-3xl border border-line bg-white p-6 shadow-soft sm:sticky sm:top-6 sm:p-7">
            <p className="text-sm font-semibold text-muted">Daily rate</p>
            <p className="mt-1 text-3xl font-black tracking-tight text-ink">KES {formatPrice(vehicle.daily_rate)}<span className="text-sm font-semibold text-muted"> / day</span></p>
            <div className="my-6 border-t border-line" />
            <div className="flex justify-between text-sm"><span className="text-muted">Refundable deposit</span><span className="font-bold text-ink">KES {formatPrice(vehicle.deposit_amount)}</span></div>
            <button disabled className="mt-6 inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-[#e6ece8] px-5 text-sm font-extrabold text-[#77827b]">Book this car <ArrowRight size={16} /></button>
            <p className="mt-3 flex items-center justify-center gap-1.5 text-xs text-muted"><Clock3 size={14} /> Booking is coming soon</p>
            <div className="mt-6 rounded-2xl bg-canvas p-4 text-sm leading-6 text-muted"><ShieldCheck size={17} className="mb-2 text-accent" />Every public listing has current insurance and vehicle inspection details.</div>
          </aside>
        </div>
      </main>
      <Footer />
    </>
  );
}

const signupSteps = ["Account", "Verify", "Your plan", "Owner details", "Your car"];

function SignupFlow() {
  const { request, signIn, user } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [step, setStep] = useState(user?.phone_verified_at ? 3 : 1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [account, setAccount] = useState({ full_name: "", email: "", phone: "254", password: "" });
  const [loginAfterRegister, setLoginAfterRegister] = useState(false);
  const [intent, setIntent] = useState(searchParams.get("intent") === "list" ? "list" : "");
  const [verifyCode, setVerifyCode] = useState("");
  const [resendSeconds, setResendSeconds] = useState(30);
  const [verificationRequested, setVerificationRequested] = useState(false);
  const [ownerApplication, setOwnerApplication] = useState(null);
  const [ownerDocuments, setOwnerDocuments] = useState({ id: null, selfie: null });
  const [uploadedOwnerDocuments, setUploadedOwnerDocuments] = useState([]);
  const [vehicle, setVehicle] = useState(null);
  const [vehicleDocuments, setVehicleDocuments] = useState({ logbook: null, insurance: null });
  const [vehiclePhotos, setVehiclePhotos] = useState([]);
  const [uploadedVehicleDocuments, setUploadedVehicleDocuments] = useState([]);
  const [uploadedPhotoCount, setUploadedPhotoCount] = useState(0);
  const [applicationStatus, setApplicationStatus] = useState(null);
  const [statusLoading, setStatusLoading] = useState(false);

  useEffect(() => {
    if (step !== 2 || verificationRequested) return;
    let active = true;
    setBusy(true);
    request("/api/auth/verify/request", { method: "POST", body: jsonBody({ channel: "phone" }) })
      .then(() => {
        if (active) {
          setVerificationRequested(true);
          setResendSeconds(30);
        }
      })
      .catch((requestError) => { if (active) setError(requestError.message); })
      .finally(() => { if (active) setBusy(false); });
    return () => { active = false; };
  }, [step, verificationRequested, request]);

  useEffect(() => {
    if (step !== 2 || resendSeconds <= 0) return undefined;
    const timer = window.setTimeout(() => setResendSeconds((seconds) => seconds - 1), 1000);
    return () => window.clearTimeout(timer);
  }, [step, resendSeconds]);

  useEffect(() => {
    if (step === 6) loadReviewStatus();
  }, [step]);

  async function loadReviewStatus() {
    setError("");
    setStatusLoading(true);
    try {
      const [owner, cars] = await Promise.all([
        request("/api/owners/me"),
        request("/api/owners/me/vehicles"),
      ]);
      setApplicationStatus({ owner, cars });
    } catch (loadError) {
      setError(loadError.message || "We couldn't refresh your application status.");
    } finally {
      setStatusLoading(false);
    }
  }

  async function submitRegistration(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await request("/api/auth/register", { method: "POST", body: jsonBody(account) });
      try {
        const tokens = await request("/api/auth/login", {
          method: "POST",
          body: jsonBody({ email: account.email, password: account.password }),
        });
        signIn(tokens);
        setStep(2);
      } catch (loginError) {
        setLoginAfterRegister(true);
        throw new Error(`Your account was created, but we couldn't sign you in: ${loginError.message}`);
      }
    } catch (submitError) {
      setError(submitError.message);
    } finally {
      setBusy(false);
    }
  }

  async function signInWithGoogle(credential) {
    setBusy(true);
    setError("");
    try {
      const response = await fetch(apiUrl("/api/auth/google"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: jsonBody({ credential }),
      });
      const payload = await readResponse(response);
      signIn(payload);
      if (!payload.user.phone_verified_at) {
        const from = intent ? `/signup?intent=${intent}` : "/signup";
        navigate("/verify-phone", { replace: true, state: { from } });
      } else {
        navigate(getPostSignInPath(payload.user, location.state?.from), { replace: true });
      }
    } catch (loginError) {
      setError(loginError.message || "We couldn't sign you in with Google. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  async function loginExistingAccount() {
    setBusy(true);
    setError("");
    try {
      const tokens = await request("/api/auth/login", {
        method: "POST",
        body: jsonBody({ email: account.email, password: account.password }),
      });
      signIn(tokens);
      setLoginAfterRegister(false);
      setStep(2);
    } catch (loginError) {
      setError(loginError.message);
    } finally {
      setBusy(false);
    }
  }

  async function requestCode() {
    setBusy(true);
    setError("");
    try {
      await request("/api/auth/verify/request", { method: "POST", body: jsonBody({ channel: "phone" }) });
      setVerificationRequested(true);
      setResendSeconds(30);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  async function confirmCode(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await request("/api/auth/verify/confirm", {
        method: "POST",
        body: jsonBody({ channel: "phone", code: verifyCode }),
      });
      setStep(3);
    } catch (verifyError) {
      setError(verifyError.message);
    } finally {
      setBusy(false);
    }
  }

  async function submitOwnerApplication(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      for (const documentType of ["id", "selfie"]) {
        if (!uploadedOwnerDocuments.includes(documentType) && !ownerDocuments[documentType]) {
          throw new Error(`Please choose your ${documentType === "id" ? "ID photo" : "selfie"} file.`);
        }
      }
      let application = ownerApplication;
      if (!application) {
        application = await request("/api/owners/apply", {
          method: "POST",
          body: jsonBody({
            national_id: event.currentTarget.elements.national_id.value.trim(),
            kra_pin: event.currentTarget.elements.kra_pin.value.trim(),
            payout_phone: event.currentTarget.elements.payout_phone.value.trim(),
          }),
        });
        setOwnerApplication(application);
      }
      for (const documentType of ["id", "selfie"]) {
        if (uploadedOwnerDocuments.includes(documentType)) continue;
        const file = ownerDocuments[documentType];
        if (!file) throw new Error(`Please choose your ${documentType === "id" ? "ID photo" : "selfie"} file.`);
        const body = new FormData();
        body.append("document_type", documentType);
        body.append("file", file);
        await request("/api/owners/me/documents", { method: "POST", body });
        setUploadedOwnerDocuments((current) => [...current, documentType]);
      }
      setStep(5);
    } catch (submitError) {
      setError(submitError.message);
    } finally {
      setBusy(false);
    }
  }

  async function submitVehicle(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      let created = vehicle;
      if (!created) {
        const form = new FormData(event.currentTarget);
        const payload = {
          make: form.get("make").trim(),
          model: form.get("model").trim(),
          year: Number(form.get("year")),
          plate: form.get("plate").trim().toUpperCase(),
          chassis_number: form.get("chassis_number").trim(),
          seats: Number(form.get("seats")),
          transmission: form.get("transmission"),
          fuel_type: form.get("fuel_type"),
          daily_rate: Number(form.get("daily_rate")),
          deposit_amount: Number(form.get("deposit_amount")),
          insurance_expiry: form.get("insurance_expiry"),
          inspection_expiry: form.get("inspection_expiry"),
          location: form.get("location").trim(),
        };
        created = await request("/api/vehicles", { method: "POST", body: jsonBody(payload) });
        setVehicle(created);
      }

      for (const documentType of ["logbook", "insurance"]) {
        if (uploadedVehicleDocuments.includes(documentType)) continue;
        const file = vehicleDocuments[documentType];
        if (!file) throw new Error(`Please choose your ${documentType} file.`);
        const body = new FormData();
        body.append("document_type", documentType);
        body.append("file", file);
        await request(`/api/vehicles/${created.id}/documents`, { method: "POST", body });
        setUploadedVehicleDocuments((current) => [...current, documentType]);
      }

      for (let index = uploadedPhotoCount; index < vehiclePhotos.length; index += 1) {
        const body = new FormData();
        body.append("file", vehiclePhotos[index]);
        await request(`/api/vehicles/${created.id}/photos`, { method: "POST", body });
        setUploadedPhotoCount(index + 1);
      }
      setStep(6);
    } catch (submitError) {
      setError(submitError.message);
    } finally {
      setBusy(false);
    }
  }

  if (step === 6) {
    const ownerStatus = applicationStatus?.owner.verification_status || ownerApplication?.verification_status || "pending";
    const carStatus = applicationStatus?.cars.find((item) => item.id === vehicle?.id)?.approval_status || vehicle?.approval_status || "pending";
    const isApproved = ownerStatus === "approved" && carStatus === "approved";
    return (
      <>
        <main className="mx-auto max-w-4xl px-5 py-10 sm:px-8 sm:py-16">
          <Link to="/" className="inline-flex items-center gap-2 text-sm font-bold text-muted hover:text-accent"><ArrowLeft size={16} /> Back to CarHire</Link>
          <div className="mt-8 rounded-[2rem] border border-line bg-white px-5 py-8 shadow-card sm:px-10 sm:py-10">
            <div className="mx-auto max-w-2xl text-center">
              <span className="mx-auto grid h-16 w-16 place-items-center rounded-3xl bg-[#e7f4eb] text-accent"><Clock3 size={29} /></span>
              <p className="eyebrow mt-6">You’ve done your part</p>
              <h1 className="mt-2 text-3xl font-black tracking-tight text-ink sm:text-4xl">{isApproved ? "You’re approved!" : "Under review"}</h1>
              <p className="mx-auto mt-3 max-w-lg text-sm leading-6 text-muted">
                {isApproved ? "Your owner account and car listing are approved. You’re ready for your first booking." : "Thanks for sending everything in. Our team is checking your details and documents. We’ll keep you posted."}
              </p>
            </div>
            <div className="mx-auto mt-10 max-w-xl">
              <ol className="relative">
                <div className="absolute bottom-7 left-[15px] top-7 w-px bg-line" />
                {[
                  { label: "Submitted", text: "Your details and documents are with us.", done: true },
                  { label: "Under review", text: "Our team is checking your owner application.", done: ownerStatus !== "pending", current: ownerStatus === "pending" },
                  { label: "Approved", text: "Your profile is ready to rent out your car.", done: ownerStatus === "approved" },
                ].map((item) => (
                  <li key={item.label} className="relative flex gap-4 pb-7 last:pb-0">
                    <span className={`relative z-10 grid h-8 w-8 shrink-0 place-items-center rounded-full ${item.done ? "bg-accent text-white" : item.current ? "border-2 border-accent bg-white text-accent" : "border border-line bg-white text-[#a3ada6]"}`}>{item.done ? <Check size={16} /> : <span className="h-2 w-2 rounded-full bg-current" />}</span>
                    <div className="pt-0.5"><p className={`text-sm font-extrabold ${item.done || item.current ? "text-ink" : "text-muted"}`}>{item.label}</p><p className="mt-1 text-xs leading-5 text-muted">{item.text}</p></div>
                  </li>
                ))}
              </ol>
              <div className="mt-7 rounded-2xl bg-canvas p-4">
                <div className="flex items-start justify-between gap-3">
                  <div><p className="text-xs font-semibold text-muted">Your car listing</p><p className="mt-1 font-bold text-ink">{vehicle?.year} {vehicle?.make} {vehicle?.model}</p></div>
                  <StatusPill status={carStatus} />
                </div>
              </div>
            </div>
            {error && <div className="mt-6"><Alert>{error}</Alert></div>}
            <div className="mt-7 flex flex-col justify-center gap-3 sm:flex-row">
              <button className="btn-secondary" disabled={statusLoading} onClick={loadReviewStatus}>{statusLoading ? <Spinner /> : <Sparkles size={16} />} Refresh status</button>
              <Link to="/" className="btn-primary">Explore CarHire <ArrowRight size={16} /></Link>
            </div>
          </div>
        </main>
        <Footer />
      </>
    );
  }

  if (step === 7) {
    return (
      <>
        <main className="min-h-[72vh] bg-canvas px-5 py-8 sm:px-8 sm:py-12">
          <div className="mx-auto max-w-2xl rounded-[2rem] border border-line bg-white p-5 shadow-soft sm:p-9">
            <RentReady user={user} onBrowse={() => navigate("/#cars")} />
          </div>
        </main>
        <Footer />
      </>
    );
  }

  const progress = (step / signupSteps.length) * 100;
  return (
    <>
      <main className="min-h-[72vh] bg-canvas px-5 py-8 sm:px-8 sm:py-12">
        <div className="mx-auto max-w-2xl">
          <Link to="/" className="inline-flex items-center gap-2 text-sm font-bold text-muted transition hover:text-accent"><ArrowLeft size={16} /> Back to home</Link>
          <div className="mt-7 rounded-[2rem] border border-line bg-white p-5 shadow-soft sm:p-9">
            <div className="flex items-center justify-between gap-4">
              <div><p className="eyebrow">Let’s get you moving</p><p className="mt-1 text-sm font-semibold text-ink">Step {step} of 5</p></div>
              <span className="rounded-full bg-[#e7f4eb] px-3 py-1.5 text-xs font-bold text-accent">About 3 minutes</span>
            </div>
            <div className="mt-5 h-2 overflow-hidden rounded-full bg-[#edf1ed]"><div className="h-full rounded-full bg-accent transition-all duration-500" style={{ width: `${progress}%` }} /></div>
            <div className="mt-3 hidden grid-cols-5 text-center sm:grid">{signupSteps.map((label, index) => <span key={label} className={`text-[10px] font-semibold ${index + 1 <= step ? "text-accent" : "text-[#a3ada6]"}`}>{label}</span>)}</div>
            {error && <div className="mt-6"><Alert>{error}</Alert>{loginAfterRegister && <button onClick={loginExistingAccount} disabled={busy} className="mt-3 text-sm font-bold text-accent underline underline-offset-2">{busy ? "Signing you in…" : "Try signing in again"}</button>}</div>}

            {step === 1 && <AccountStep account={account} onChange={setAccount} busy={busy} onSubmit={submitRegistration} onGoogleCredential={signInWithGoogle} />}
            {step === 2 && <VerifyStep phone={account.phone} code={verifyCode} setCode={setVerifyCode} busy={busy} requested={verificationRequested} seconds={resendSeconds} onSubmit={confirmCode} onResend={requestCode} />}
            {step === 3 && (
              <section className="mt-8">
                <p className="eyebrow">First things first</p><h1 className="mt-2 text-2xl font-black tracking-tight text-ink sm:text-3xl">What brings you here?</h1><p className="mt-2 text-sm leading-6 text-muted">You can always do both. Pick what you’d like to start with.</p>
                <div className="mt-6 grid gap-3 sm:grid-cols-2">
                  <PathCard selected={intent === "rent"} icon={<CarFront size={23} />} title="I want to rent" text="Find a great car for your next trip." onClick={() => setIntent("rent")} />
                  <PathCard selected={intent === "list"} icon={<WalletCards size={23} />} title="I want to list my car" text="Earn from your car when it’s not in use." onClick={() => setIntent("list")} />
                </div>
                <button disabled={!intent || busy} onClick={() => { setError(""); setStep(intent === "rent" ? 7 : 4); }} className="btn-primary mt-7 w-full">{busy ? <Spinner /> : "Continue"} <ArrowRight size={16} /></button>
              </section>
            )}
            {step === 4 && <OwnerStep busy={busy} ownerApplication={ownerApplication} documents={ownerDocuments} setDocuments={setOwnerDocuments} uploaded={uploadedOwnerDocuments} onSubmit={submitOwnerApplication} onError={setError} />}
            {step === 5 && <VehicleStep busy={busy} vehicle={vehicle} documents={vehicleDocuments} setDocuments={setVehicleDocuments} photos={vehiclePhotos} setPhotos={setVehiclePhotos} uploaded={uploadedVehicleDocuments} onSubmit={submitVehicle} onError={setError} />}
            {step === 7 && <RentReady user={user} onBrowse={() => navigate("/#cars")} />}
          </div>
        </div>
      </main>
      <Footer />
    </>
  );
}

function AccountStep({ account, onChange, busy, onSubmit, onGoogleCredential }) {
  const update = (key) => (event) => onChange((current) => ({ ...current, [key]: event.target.value }));
  return (
    <form onSubmit={onSubmit} className="mt-8">
      <p className="eyebrow">A good start</p><h1 className="mt-2 text-2xl font-black tracking-tight text-ink sm:text-3xl">Create your account</h1><p className="mt-2 text-sm leading-6 text-muted">Just the basics. Your information stays safe with us.</p>
      <div className="mt-6">
        <GoogleSignInButton onCredential={onGoogleCredential} disabled={busy} />
        <div className="my-5 flex items-center gap-3 text-xs text-muted"><span className="h-px flex-1 bg-line" />or create an account with email<span className="h-px flex-1 bg-line" /></div>
      </div>
      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <FormField label="Full name"><input required minLength="2" maxLength="160" autoComplete="name" value={account.full_name} onChange={update("full_name")} placeholder="e.g. Amina Wanjiku" className="field" /></FormField>
        <FormField label="Email address"><input required type="email" autoComplete="email" value={account.email} onChange={update("email")} placeholder="you@example.com" className="field" /></FormField>
        <FormField label="Phone number" hint="Use your Kenyan number in 254 format"><input required inputMode="numeric" pattern="254[17][0-9]{8}" maxLength="12" autoComplete="tel" value={account.phone} onChange={update("phone")} placeholder="254712345678" className="field" /></FormField>
        <FormField label="Password"><input required type="password" minLength="8" maxLength="128" autoComplete="new-password" value={account.password} onChange={update("password")} placeholder="At least 8 characters" className="field" /></FormField>
      </div>
      <button disabled={busy} className="btn-primary mt-7 w-full">{busy ? <Spinner /> : "Create account"} <ArrowRight size={16} /></button>
      <p className="mt-4 text-center text-xs leading-5 text-muted">By continuing, you agree to our terms and privacy policy.</p>
      <p className="mt-4 text-center text-sm text-muted">Already have an account? <Link to="/signin" className="font-bold text-accent">Sign in</Link></p>
    </form>
  );
}

function VerifyStep({ phone, code, setCode, busy, requested, seconds, onSubmit, onResend }) {
  return (
    <form onSubmit={onSubmit} className="mt-8">
      <span className="grid h-12 w-12 place-items-center rounded-2xl bg-[#e7f4eb] text-accent"><ShieldCheck size={22} /></span>
      <p className="eyebrow mt-5">One quick check</p><h1 className="mt-2 text-2xl font-black tracking-tight text-ink sm:text-3xl">Verify your phone</h1>
      <p className="mt-2 text-sm leading-6 text-muted">We sent a six-digit code to <span className="font-bold text-ink">{phone}</span>. It helps keep the community safe.</p>
      <p className="mt-4 rounded-xl bg-[#f8f6ed] px-4 py-3 text-xs leading-5 text-[#796b47]">In demo mode the code appears in the server log.</p>
      <label className="mt-6 block text-xs font-bold text-ink">Verification code</label>
      <input required inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength="6" value={code} onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))} placeholder="000000" className="field mt-2 text-center text-2xl font-bold tracking-[.45em]" />
      <button disabled={busy || code.length !== 6} className="btn-primary mt-5 w-full">{busy ? <Spinner /> : "Verify phone"} <ArrowRight size={16} /></button>
      <div className="mt-4 text-center text-sm text-muted">{requested ? "Didn’t get a code?" : "Requesting your code…"}{" "}<button type="button" disabled={busy || seconds > 0} onClick={onResend} className="font-bold text-accent disabled:cursor-not-allowed disabled:text-[#a3ada6]">{seconds > 0 ? `Resend in 0:${String(seconds).padStart(2, "0")}` : "Resend code"}</button></div>
    </form>
  );
}

function PathCard({ selected, icon, title, text, onClick }) {
  return (
    <button type="button" onClick={onClick} className={`rounded-2xl border p-5 text-left transition ${selected ? "border-accent bg-[#f1f8f3] ring-2 ring-accent/10" : "border-line hover:border-[#b8d5c1]"}`}>
      <span className={`grid h-11 w-11 place-items-center rounded-xl ${selected ? "bg-accent text-white" : "bg-canvas text-accent"}`}>{icon}</span>
      <span className="mt-4 block font-extrabold text-ink">{title}</span>
      <span className="mt-1 block text-sm leading-5 text-muted">{text}</span>
    </button>
  );
}

function OwnerStep({ busy, ownerApplication, documents, setDocuments, uploaded, onSubmit, onError }) {
  const updateFile = (type) => (file) => {
    const validation = validateUpload(file);
    if (validation) {
      onError(validation);
      return;
    }
    onError("");
    setDocuments((current) => ({ ...current, [type]: file }));
  };
  return (
    <form onSubmit={onSubmit} className="mt-8">
      <p className="eyebrow">A few owner details</p><h1 className="mt-2 text-2xl font-black tracking-tight text-ink sm:text-3xl">Let’s get you ready to list</h1>
      <p className="mt-2 text-sm leading-6 text-muted">We review every owner application. Your ID documents are kept private and secure.</p>
      {ownerApplication && <p className="mt-4 rounded-xl bg-[#f8f6ed] px-4 py-3 text-xs leading-5 text-[#796b47]">Your application is saved. Add any missing documents to continue.</p>}
      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <FormField label="National ID number"><input required name="national_id" minLength="5" maxLength="32" className="field" placeholder="Your ID number" /></FormField>
        <FormField label="KRA PIN"><input required name="kra_pin" minLength="5" maxLength="16" className="field uppercase" placeholder="e.g. A001234567Z" /></FormField>
        <div className="sm:col-span-2"><FormField label="Payout M-Pesa number" hint="Use the 254 format"><input required name="payout_phone" pattern="254[17][0-9]{8}" maxLength="12" defaultValue="254" inputMode="numeric" className="field" placeholder="254712345678" /></FormField></div>
      </div>
      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <UploadField label="ID photo" help="A clear photo of your national ID." value={documents.id} onChange={updateFile("id")} accept="image/jpeg,image/png,application/pdf" uploaded={uploaded.includes("id")} />
        <UploadField label="Selfie" help="A recent photo of you." value={documents.selfie} onChange={updateFile("selfie")} accept="image/jpeg,image/png,application/pdf" uploaded={uploaded.includes("selfie")} />
      </div>
      <p className="mt-4 text-xs text-muted">JPG, PNG or PDF · Up to 5 MB each</p>
      <button disabled={busy} className="btn-primary mt-7 w-full">{busy ? <Spinner /> : ownerApplication ? "Upload documents & continue" : "Submit owner application"} <ArrowRight size={16} /></button>
      <p className="mt-3 text-center text-xs text-muted">You can add your car details while your application is reviewed.</p>
    </form>
  );
}

function VehicleStep({ busy, vehicle, documents, setDocuments, photos, setPhotos, uploaded, onSubmit, onError }) {
  const update = (key) => (event) => {
    const file = event.target.files?.[0] || null;
    const validation = validateUpload(file);
    if (validation) {
      onError(validation);
      event.target.value = "";
      return;
    }
    onError("");
    setDocuments((current) => ({ ...current, [key]: file }));
  };
  const updatePhotos = (event) => {
    const selected = Array.from(event.target.files || []);
    if (selected.length > 8) {
      onError("Choose up to 8 car photos.");
      event.target.value = "";
      return;
    }
    const invalidPhoto = selected.find((file) => {
      const error = validateUpload(file, true);
      return Boolean(error);
    });
    if (invalidPhoto) {
      onError(validateUpload(invalidPhoto, true));
      event.target.value = "";
      return;
    }
    onError("");
    setPhotos(selected);
  };
  const minDate = new Date().toISOString().slice(0, 10);
  const nextYear = new Date();
  nextYear.setFullYear(nextYear.getFullYear() + 1);
  const defaultExpiry = nextYear.toISOString().slice(0, 10);
  return (
    <form onSubmit={onSubmit} className="mt-8">
      <p className="eyebrow">Your first listing</p><h1 className="mt-2 text-2xl font-black tracking-tight text-ink sm:text-3xl">Tell us about your car</h1>
      <p className="mt-2 text-sm leading-6 text-muted">A few details help renters find the right ride. You can update your listing later.</p>
      {vehicle && <p className="mt-4 rounded-xl bg-[#f8f6ed] px-4 py-3 text-xs leading-5 text-[#796b47]">Your car details are saved. Complete any document uploads to submit it for review.</p>}
      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <FormField label="Make"><input required name="make" maxLength="80" className="field" placeholder="Toyota" /></FormField>
        <FormField label="Model"><input required name="model" maxLength="80" className="field" placeholder="RAV4" /></FormField>
        <FormField label="Year"><input required name="year" type="number" min="1886" max="2100" defaultValue="2022" className="field" /></FormField>
        <FormField label="Number plate"><input required name="plate" maxLength="16" className="field uppercase" placeholder="KDA 123A" /></FormField>
        <FormField label="Chassis number"><input required name="chassis_number" maxLength="64" className="field" placeholder="Vehicle chassis number" /></FormField>
        <FormField label="Seats"><input required name="seats" type="number" min="1" max="100" defaultValue="5" className="field" /></FormField>
        <FormField label="Transmission"><select required name="transmission" className="field"><option value="">Choose one</option><option>Automatic</option><option>Manual</option></select></FormField>
        <FormField label="Fuel type"><select required name="fuel_type" className="field"><option value="">Choose one</option><option>Petrol</option><option>Diesel</option><option>Hybrid</option><option>Electric</option></select></FormField>
        <FormField label="Daily rate (KES)"><input required name="daily_rate" type="number" min="1" step="0.01" className="field" placeholder="4500" /></FormField>
        <FormField label="Refundable deposit (KES)"><input required name="deposit_amount" type="number" min="0" step="0.01" className="field" placeholder="10000" /></FormField>
        <FormField label="Insurance expiry"><input required name="insurance_expiry" type="date" min={minDate} defaultValue={defaultExpiry} className="field" /></FormField>
        <FormField label="Inspection expiry"><input required name="inspection_expiry" type="date" min={minDate} defaultValue={defaultExpiry} className="field" /></FormField>
        <div className="sm:col-span-2"><FormField label="Pick-up location"><input required name="location" maxLength="500" className="field" placeholder="Westlands, Nairobi" /></FormField></div>
      </div>
      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <label className="block"><span className="mb-2 block text-xs font-bold text-ink">Logbook</span><input required={!uploaded.includes("logbook")} type="file" accept=".jpg,.jpeg,.png,.pdf,image/jpeg,image/png,application/pdf" onChange={update("logbook")} className="file-field" />{documents.logbook && !uploaded.includes("logbook") ? <UploadPreview file={documents.logbook} /> : uploaded.includes("logbook") ? <span className="mt-2 block text-xs font-semibold text-accent">Uploaded ✓</span> : <span className="mt-2 block text-xs text-muted">JPG, PNG or PDF · Up to 5 MB</span>}</label>
        <label className="block"><span className="mb-2 block text-xs font-bold text-ink">Insurance certificate</span><input required={!uploaded.includes("insurance")} type="file" accept=".jpg,.jpeg,.png,.pdf,image/jpeg,image/png,application/pdf" onChange={update("insurance")} className="file-field" />{documents.insurance && !uploaded.includes("insurance") ? <UploadPreview file={documents.insurance} /> : uploaded.includes("insurance") ? <span className="mt-2 block text-xs font-semibold text-accent">Uploaded ✓</span> : <span className="mt-2 block text-xs text-muted">JPG, PNG or PDF · Up to 5 MB</span>}</label>
      </div>
      <div className="mt-6">
        <label className="block text-xs font-bold text-ink">Car photos <span className="font-medium text-muted">(up to 8)</span></label>
        <input type="file" multiple accept=".jpg,.jpeg,.png,image/jpeg,image/png" onChange={updatePhotos} className="file-field mt-2" />
        <p className="mt-2 text-xs text-muted">JPG or PNG · Up to 5 MB each</p>
        {photos.length > 0 && <div className="mt-3 grid grid-cols-3 gap-2 sm:grid-cols-4">{photos.map((photo) => <UploadPreview key={`${photo.name}-${photo.lastModified}`} file={photo} compact />)}</div>}
      </div>
      <button disabled={busy} className="btn-primary mt-7 w-full">{busy ? <Spinner /> : vehicle ? "Finish uploading & submit" : "Submit car for review"} <ArrowRight size={16} /></button>
      <p className="mt-3 text-center text-xs text-muted">Your listing will stay private until it’s approved.</p>
    </form>
  );
}

function FormField({ label, hint, children }) {
  return <label className="block"><span className="mb-2 block text-xs font-bold text-ink">{label}</span>{children}{hint && <span className="mt-1.5 block text-[11px] text-muted">{hint}</span>}</label>;
}

function validateUpload(file, photo = false) {
  if (!file) return "";
  const acceptedTypes = photo
    ? ["image/jpeg", "image/png"]
    : ["image/jpeg", "image/png", "application/pdf"];
  if (!acceptedTypes.includes(file.type)) {
    return photo ? "Car photos must be JPG or PNG." : "Choose a JPG, PNG or PDF file.";
  }
  if (file.size > 5 * 1024 * 1024) return "Each file must be 5 MB or smaller.";
  if (!file.size) return "Choose a file that isn’t empty.";
  return "";
}

function UploadField({ label, help, value, onChange, accept, uploaded }) {
  return (
    <div className="rounded-2xl border border-line p-4">
      <span className="block text-xs font-bold text-ink">{label}</span>
      <span className="mt-1 block text-xs leading-5 text-muted">{help}</span>
      {value ? <UploadPreview file={value} /> : <label className="mt-3 flex cursor-pointer items-center justify-center gap-2 rounded-xl border border-dashed border-[#cbd8ce] bg-canvas px-3 py-3 text-xs font-bold text-accent transition hover:border-accent"><input type="file" accept={accept} onChange={(event) => { onChange(event.target.files?.[0] || null); event.target.value = ""; }} className="sr-only" />Choose file</label>}
      {uploaded && <span className="mt-2 block text-xs font-semibold text-accent">Uploaded ✓</span>}
    </div>
  );
}

function UploadPreview({ file, compact = false }) {
  const [url, setUrl] = useState("");
  useEffect(() => {
    const nextUrl = URL.createObjectURL(file);
    setUrl(nextUrl);
    return () => URL.revokeObjectURL(nextUrl);
  }, [file]);
  const isImage = file.type.startsWith("image/");
  return (
    <div className={`mt-3 flex items-center gap-3 rounded-xl bg-canvas p-2.5 ${compact ? "mt-0 block p-1" : ""}`}>
      {isImage && url ? <img src={url} alt={`${file.name} preview`} className={`${compact ? "h-20" : "h-14"} w-full rounded-lg object-cover`} /> : <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-white text-accent"><ShieldCheck size={18} /></span>}
      {!compact && <span className="min-w-0 flex-1 truncate text-xs font-semibold text-ink">{file.name}</span>}
    </div>
  );
}

function getPostSignInPath(user, from) {
  let destination = null;
  if (typeof from === "string" && from.startsWith("/") && !from.startsWith("//")) {
    destination = from;
  } else if (from?.pathname?.startsWith("/") && !from.pathname.startsWith("//")) {
    destination = `${from.pathname}${from.search || ""}${from.hash || ""}`;
  }
  if (destination && !destination.startsWith("/signin") && !destination.startsWith("/verify-phone")) {
    return destination;
  }
  if (user?.role === "admin") return "/admin";
  if (user?.role === "owner") return "/owner";
  return "/";
}

function SignInPage() {
  const { signIn } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function signInWithGoogle(credential) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const response = await fetch(apiUrl("/api/auth/google"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: jsonBody({ credential }),
      });
      const payload = await readResponse(response);
      signIn(payload);
      const destination = getPostSignInPath(payload.user, location.state?.from);
      if (!payload.user.phone_verified_at) {
        navigate("/verify-phone", { replace: true, state: { from: destination } });
      } else {
        navigate(destination, { replace: true });
      }
    } catch (loginError) {
      setError(loginError.message || "We couldn't sign you in with Google. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  async function submit(event) {
    event.preventDefault();
    setError("");
    setNotice("");
    const normalizedEmail = email.trim();
    if (!normalizedEmail || !password || password.length > 128) {
      setError("Enter a valid email address and password.");
      return;
    }

    setBusy(true);
    try {
      const response = await fetch(apiUrl("/api/auth/login"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: jsonBody({ email: normalizedEmail, password }),
      });
      const payload = await readResponse(response);
      signIn(payload);
      const destination = getPostSignInPath(payload.user, location.state?.from);
      if (!payload.user.phone_verified_at) {
        navigate("/verify-phone", { replace: true, state: { from: destination } });
      } else {
        navigate(destination, { replace: true });
      }
    } catch (loginError) {
      setError(loginError.message || "We couldn't sign you in. Check your details and try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <main className="grid min-h-[72vh] place-items-center bg-canvas px-5 py-12">
        <div className="w-full max-w-md rounded-[2rem] border border-line bg-white p-6 shadow-card sm:p-9">
          <Logo />
          <p className="eyebrow mt-8">Welcome back</p>
          <h1 className="mt-2 text-2xl font-black tracking-tight text-ink">Sign in to CarHire</h1>
          <p className="mt-2 text-sm leading-6 text-muted">Pick up right where you left off.</p>
          {error && <p role="alert" className="mt-5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</p>}
          {notice && <p role="status" className="mt-5 rounded-xl border border-[#d8e9dc] bg-[#f1f8f3] px-4 py-3 text-sm text-accent">{notice}</p>}
          <div className="mt-6">
            <GoogleSignInButton onCredential={signInWithGoogle} disabled={busy} />
            <div className="my-5 flex items-center gap-3 text-xs text-muted"><span className="h-px flex-1 bg-line" />or sign in with email<span className="h-px flex-1 bg-line" /></div>
          </div>
          <form onSubmit={submit} className="mt-6 space-y-4">
            <label className="block">
              <span className="mb-2 block text-xs font-bold text-ink">Email address</span>
              <input
                required
                type="email"
                autoComplete="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className="field"
                placeholder="you@example.com"
              />
            </label>
            <label className="block">
              <span className="mb-2 block text-xs font-bold text-ink">Password</span>
              <span className="relative block">
                <input
                  required
                  minLength="1"
                  maxLength="128"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  className="field pr-12"
                  placeholder="Your password"
                />
                <button
                  type="button"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  onClick={() => setShowPassword((shown) => !shown)}
                  className="absolute inset-y-0 right-0 grid w-12 place-items-center text-muted hover:text-ink"
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </span>
            </label>
            <div className="text-right">
              <button type="button" onClick={() => { setError(""); setNotice("Coming soon"); }} className="text-xs font-bold text-accent hover:underline">
                Forgot password?
              </button>
            </div>
            <button disabled={busy} className="btn-primary w-full">
              {busy ? <Spinner /> : "Sign in"} <ArrowRight size={16} />
            </button>
          </form>
          <p className="mt-5 text-center text-sm text-muted">
            New to CarHire? <Link to="/signup" className="font-bold text-accent">Create account</Link>
          </p>
        </div>
      </main>
      <Footer />
    </>
  );
}

function PhoneVerificationPage() {
  const { isSignedIn, request, signIn, tokens, user } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [requested, setRequested] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [phone, setPhone] = useState(user?.phone || "254");

  useEffect(() => {
    if (!isSignedIn || user?.phone_verified_at || !user?.phone) return;
    let active = true;
    setBusy(true);
    request("/api/auth/verify/request", { method: "POST", body: jsonBody({ channel: "phone" }) })
      .then(() => {
        if (active) {
          setRequested(true);
          setSeconds(30);
        }
      })
      .catch((requestError) => { if (active) setError(requestError.message); })
      .finally(() => { if (active) setBusy(false); });
    return () => { active = false; };
  }, [isSignedIn, user?.phone, user?.phone_verified_at, request]);

  useEffect(() => {
    if (seconds <= 0) return undefined;
    const timer = window.setTimeout(() => setSeconds((value) => value - 1), 1000);
    return () => window.clearTimeout(timer);
  }, [seconds]);

  if (!isSignedIn) return <Navigate to="/signin" replace />;
  if (user?.phone_verified_at) return <Navigate to={getPostSignInPath(user, location.state?.from)} replace />;

  async function requestCode() {
    setBusy(true);
    setError("");
    try {
      await request("/api/auth/verify/request", { method: "POST", body: jsonBody({ channel: "phone" }) });
      setRequested(true);
      setSeconds(30);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  async function savePhone(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const updatedUser = await request("/api/auth/phone", {
        method: "POST",
        body: jsonBody({ phone }),
      });
      signIn({ ...tokens, user: updatedUser });
    } catch (phoneError) {
      setError(phoneError.message || "We couldn't save your phone number. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  async function confirmCode(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await request("/api/auth/verify/confirm", {
        method: "POST",
        body: jsonBody({ channel: "phone", code }),
      });
      const refreshed = await request("/api/auth/refresh", {
        method: "POST",
        body: jsonBody({ refresh_token: tokens.refresh_token }),
      });
      signIn(refreshed);
      navigate(getPostSignInPath(refreshed.user, location.state?.from), { replace: true });
    } catch (verificationError) {
      setError(verificationError.message || "We couldn't verify your phone. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <main className="grid min-h-[72vh] place-items-center bg-canvas px-5 py-12">
        <div className="w-full max-w-md rounded-[2rem] border border-line bg-white p-6 shadow-card sm:p-9">
          <Logo />
          {error && <p role="alert" className="mt-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</p>}
          <div className="mt-8">
            <span className="grid h-12 w-12 place-items-center rounded-2xl bg-[#e7f4eb] text-accent"><ShieldCheck size={22} /></span>
            <p className="eyebrow mt-5">One quick check</p>
            <h1 className="mt-2 text-2xl font-black tracking-tight text-ink">Verify your phone</h1>
            {!user?.phone ? (
              <form onSubmit={savePhone} className="mt-6">
                <p className="text-sm leading-6 text-muted">Add your phone number before we send a verification code.</p>
                <label className="mt-5 block text-xs font-bold text-ink" htmlFor="phone-number">Phone number</label>
                <input id="phone-number" required inputMode="numeric" autoComplete="tel" pattern="254[17][0-9]{8}" maxLength="12" value={phone} onChange={(event) => setPhone(event.target.value.replace(/\D/g, "").slice(0, 12))} placeholder="254712345678" className="field mt-2" />
                <button disabled={busy || !/^254[17]\d{8}$/.test(phone)} className="btn-primary mt-5 w-full">{busy ? <Spinner /> : "Continue"} <ArrowRight size={16} /></button>
              </form>
            ) : (
              <form onSubmit={confirmCode} className="mt-6">
                <p className="mt-2 text-sm leading-6 text-muted">We sent a six-digit code to <span className="font-bold text-ink">{user.phone}</span>.</p>
                <p className="mt-4 rounded-xl bg-[#f8f6ed] px-4 py-3 text-xs leading-5 text-[#796b47]">In demo mode the code appears in the server log.</p>
                <label className="mt-6 block text-xs font-bold text-ink" htmlFor="phone-code">Verification code</label>
                <input id="phone-code" required inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength="6" value={code} onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))} placeholder="000000" className="field mt-2 text-center text-2xl font-bold tracking-[.45em]" />
                <button disabled={busy || code.length !== 6} className="btn-primary mt-5 w-full">{busy ? <Spinner /> : "Verify phone"} <ArrowRight size={16} /></button>
                <div className="mt-4 text-center text-sm text-muted">
                  {requested ? "Didn't get a code?" : "Requesting your code…"}{" "}
                  <button type="button" disabled={busy || seconds > 0} onClick={requestCode} className="font-bold text-accent disabled:cursor-not-allowed disabled:text-[#a3ada6]">
                    {seconds > 0 ? `Resend in 0:${String(seconds).padStart(2, "0")}` : "Resend code"}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      </main>
      <Footer />
    </>
  );
}

function OwnerDashboardPage() {
  const { isSignedIn, request, user } = useAuth();
  const location = useLocation();
  const [application, setApplication] = useState(null);
  const [cars, setCars] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!isSignedIn) return;
    if (user?.role !== "owner") {
      setLoading(false);
      return;
    }
    let active = true;
    Promise.all([request("/api/owners/me"), request("/api/owners/me/vehicles")])
      .then(([owner, vehicles]) => {
        if (active) {
          setApplication(owner);
          setCars(vehicles);
        }
      })
      .catch((loadError) => { if (active) setError(loadError.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [isSignedIn, request, user?.role]);

  if (!isSignedIn) return <Navigate to="/signin" replace state={{ from: location }} />;

  return (
    <>
      <main className="mx-auto min-h-[65vh] max-w-5xl px-5 py-10 sm:px-8 sm:py-14">
        <p className="eyebrow">Owner dashboard</p>
        <h1 className="mt-2 text-3xl font-black tracking-tight text-ink">My cars</h1>
        <p className="mt-2 text-sm text-muted">Welcome back, {user?.full_name}.</p>
        {loading && <div className="mt-8 rounded-2xl border border-line bg-white p-6 text-sm text-muted"><Spinner /> <span className="ml-2">Loading your cars…</span></div>}
        {!loading && user?.role !== "owner" && (
          <div className="mt-8 rounded-2xl border border-line bg-white p-6 text-sm leading-6 text-muted">
            Your account doesn't have an owner dashboard yet.
          </div>
        )}
        {error && <div className="mt-8"><Alert>{error}</Alert></div>}
        {!loading && !error && user?.role === "owner" && (
          <>
            <div className="mt-8 grid gap-4 sm:grid-cols-2">
              <div className="rounded-2xl border border-line bg-white p-5">
                <p className="text-xs font-bold uppercase tracking-wider text-muted">Owner application</p>
                <p className="mt-3 text-lg font-extrabold capitalize text-ink">{application?.verification_status?.replaceAll("_", " ") || "Not submitted"}</p>
              </div>
              <div className="rounded-2xl border border-line bg-white p-5">
                <p className="text-xs font-bold uppercase tracking-wider text-muted">Your cars</p>
                <p className="mt-3 text-lg font-extrabold text-ink">{cars.length}</p>
              </div>
            </div>
            <section className="mt-9">
              <h2 className="text-xl font-black text-ink">Listings</h2>
              {cars.length ? (
                <div className="mt-4 grid gap-3">
                  {cars.map((car) => (
                    <article key={car.id} className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-line bg-white p-5">
                      <div>
                        <h3 className="font-extrabold text-ink">{car.year} {car.make} {car.model}</h3>
                        <p className="mt-1 text-sm text-muted">{car.plate} · KES {formatPrice(car.daily_rate)} / day</p>
                      </div>
                      <StatusPill status={car.approval_status} />
                    </article>
                  ))}
                </div>
              ) : (
                <p className="mt-4 rounded-2xl border border-line bg-white p-5 text-sm text-muted">You haven't submitted any cars yet.</p>
              )}
            </section>
          </>
        )}
      </main>
      <Footer />
    </>
  );
}

function SessionExpiredNotice() {
  const { sessionExpired, clearSessionExpired } = useAuth();
  if (!sessionExpired) return null;
  return (
    <div role="alert" className="flex flex-wrap items-center justify-between gap-3 border-b border-[#e9dfc8] bg-[#fbf7ed] px-5 py-3 text-sm text-[#796b47] sm:px-8">
      <span>Your session has expired. Please sign in again.</span>
      <div className="flex items-center gap-4">
        <Link to="/signin" onClick={clearSessionExpired} className="font-bold text-accent underline underline-offset-2">Sign in</Link>
        <button type="button" aria-label="Dismiss session notice" onClick={clearSessionExpired}><X size={16} /></button>
      </div>
    </div>
  );
}

function StatusPill({ status }) {
  const style = status === "approved" ? "bg-[#e7f4eb] text-accent" : status === "rejected" ? "bg-red-50 text-red-700" : "bg-[#fbf0dc] text-[#94630f]";
  return <span className={`shrink-0 rounded-full px-3 py-1.5 text-[11px] font-bold capitalize ${style}`}>{status?.replaceAll("_", " ") || "pending"}</span>;
}

function RentReady({ user, onBrowse }) {
  return (
    <section className="mt-8 text-center">
      <span className="mx-auto grid h-16 w-16 place-items-center rounded-3xl bg-[#e7f4eb] text-accent"><CircleCheck size={30} /></span>
      <p className="eyebrow mt-6">You’re all set</p><h1 className="mt-2 text-2xl font-black tracking-tight text-ink sm:text-3xl">Welcome to the ride, {user?.full_name?.split(" ")[0]}.</h1>
      <p className="mx-auto mt-3 max-w-md text-sm leading-6 text-muted">Your account is ready. Browse verified cars and find the one that fits your next trip.</p>
      <Link to="/#cars" onClick={onBrowse} className="btn-primary mt-7 w-full">Browse available cars <ArrowRight size={16} /></Link>
    </section>
  );
}

function Spinner() {
  return <span aria-label="Loading" className="h-4 w-4 animate-spin rounded-full border-2 border-current border-r-transparent" />;
}

function NotFound() {
  return <main className="grid min-h-[65vh] place-items-center px-5 text-center"><div><span className="text-sm font-bold text-accent">404</span><h1 className="mt-2 text-3xl font-black text-ink">Looks like a wrong turn.</h1><Link to="/" className="btn-primary mt-5">Back to home <ArrowRight size={16} /></Link></div></main>;
}

export default function App() {
  return (
    <div className="min-h-screen bg-canvas text-ink">
      <SiteHeader />
      <SessionExpiredNotice />
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/vehicles/:id" element={<VehicleDetailPage />} />
        <Route path="/signup" element={<SignupFlow />} />
        <Route path="/signin" element={<SignInPage />} />
        <Route path="/login" element={<Navigate to="/signin" replace />} />
        <Route path="/verify-phone" element={<PhoneVerificationPage />} />
        <Route path="/owner" element={<OwnerDashboardPage />} />
        <Route path="/admin/*" element={<AdminRoute />} />
        <Route path="/demo" element={<DemoPage />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </div>
  );
}
