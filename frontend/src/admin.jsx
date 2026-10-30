import { useEffect, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  BadgeCheck,
  Check,
  CheckCircle2,
  Clock3,
  FileCheck2,
  FileText,
  Gauge,
  Image,
  LayoutDashboard,
  LogOut,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  UsersRound,
  X,
} from "lucide-react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "./auth.jsx";
import { apiUrl, jsonBody } from "./lib/api.js";

const api = "/api/admin";

function Logo() {
  return (
    <Link to="/" className="inline-flex items-center gap-2.5 text-ink">
      <span className="grid h-10 w-10 place-items-center rounded-2xl bg-accent text-white"><Gauge size={21} /></span>
      <span className="text-[19px] font-extrabold tracking-tight">carhire<span className="text-accent">.</span></span>
    </Link>
  );
}

export function LoginPage({ adminOnly = false }) {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await fetch(apiUrl("/api/auth/login"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: jsonBody({ email, password }),
      });
      const payload = await result.json();
      if (!result.ok) throw new Error(payload?.error?.message || "We couldn't sign you in.");
      if (adminOnly && payload.user.role !== "admin") {
        throw new Error("This sign-in is for administrators. Your account does not have admin access.");
      }
      signIn(payload);
      navigate(adminOnly ? "/admin" : payload.user.role === "admin" ? "/admin" : "/");
    } catch (loginError) {
      setError(loginError.message || "We couldn't sign you in.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="grid min-h-[72vh] place-items-center bg-canvas px-5 py-12">
      <div className="w-full max-w-md rounded-[2rem] border border-line bg-white p-6 shadow-card sm:p-9">
        <Logo />
        <p className="eyebrow mt-8">{adminOnly ? "CarHire operations" : "Welcome back"}</p>
        <h1 className="mt-2 text-2xl font-black tracking-tight text-ink">{adminOnly ? "Admin sign in" : "Sign in to CarHire"}</h1>
        <p className="mt-2 text-sm leading-6 text-muted">{adminOnly ? "Use your provisioned administrator account to open the review desk." : "Pick up right where you left off."}</p>
        {error && <p role="alert" className="mt-5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</p>}
        <form onSubmit={submit} className="mt-6 space-y-4">
          <label className="block"><span className="mb-2 block text-xs font-bold text-ink">Email address</span><input required type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} className="field" placeholder="you@example.com" /></label>
          <label className="block"><span className="mb-2 block text-xs font-bold text-ink">Password</span><input required type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} className="field" placeholder="Your password" /></label>
          <button disabled={busy} className="btn-primary w-full">{busy ? <Spinner /> : "Sign in"} <ArrowRight size={16} /></button>
        </form>
        <p className="mt-5 text-center text-sm text-muted">{adminOnly ? <>Not an admin? <Link to="/login" className="font-bold text-accent">Go to sign in</Link></> : <>New to CarHire? <Link to="/signup" className="font-bold text-accent">Create an account</Link></>}</p>
      </div>
    </main>
  );
}

export function AdminRoute() {
  const { isSignedIn, user } = useAuth();
  if (!isSignedIn) return <LoginPage adminOnly />;
  if (user?.role !== "admin") {
    return (
      <main className="grid min-h-[70vh] place-items-center px-5 py-12">
        <div className="max-w-md rounded-3xl border border-line bg-white p-8 text-center shadow-soft">
          <span className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-red-50 text-red-700"><ShieldAlert size={24} /></span>
          <h1 className="mt-5 text-2xl font-black text-ink">Admin access only</h1>
          <p className="mt-2 text-sm leading-6 text-muted">This area is only available to CarHire administrators.</p>
          <Link to="/" className="btn-primary mt-6">Back to CarHire <ArrowRight size={16} /></Link>
        </div>
      </main>
    );
  }
  return <AdminArea />;
}

export function DemoPage() {
  return (
    <main className="mx-auto max-w-4xl px-5 py-10 sm:px-8 sm:py-16">
      <Link to="/" className="inline-flex items-center gap-2 text-sm font-bold text-muted hover:text-accent"><ArrowLeft size={16} /> Back to CarHire</Link>
      <div className="mt-7 rounded-[2rem] border border-line bg-white p-6 shadow-card sm:p-10">
        <p className="eyebrow">The pitch, in a few clicks</p>
        <h1 className="mt-2 text-3xl font-black tracking-tight text-ink sm:text-4xl">CarHire demo</h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-muted">Walk through a local owner application and approve a first vehicle in the admin review desk. No demo passwords are hard-coded into the app.</p>
        <div className="mt-8 grid gap-4 sm:grid-cols-2">
          <DemoAccount title="Administrator · demo.admin@example.com" icon={<ShieldCheck size={19} />} detail="Provision this local account with the backend seed command. Enter its password interactively and share it only with your demo team." />
          <DemoAccount title="Owner · demo.owner@example.com" icon={<UsersRound size={19} />} detail="Create this account at signup with phone 254700000002. Choose its password during signup, verify with the server-log code, then submit the application and car." />
        </div>
        <div className="mt-7 rounded-2xl border border-[#e9dfc8] bg-[#fbf7ed] p-5">
          <h2 className="font-extrabold text-ink">Reset demo data</h2>
          <p className="mt-2 text-sm leading-6 text-muted">There is no reset button or built-in demo dataset. Before a fresh pitch, reset only your local development database using your normal development workflow, then create a new applicant and car. Never run a demo reset against production data.</p>
        </div>
        <div className="mt-8">
          <h2 className="text-lg font-extrabold text-ink">Exact click path</h2>
          <ol className="mt-4 space-y-3">
            {[
              "On the landing page, choose “List your car” and complete account creation.",
              "Enter the 6-digit phone code from the API server log, then choose “I want to list my car”.",
              "Submit the owner details, ID and selfie; add the vehicle, photos, logbook and insurance.",
              "Open /admin and sign in with the provisioned admin account.",
              "Open Owners → select the applicant → review ID and selfie side by side → Approve.",
              "Open Vehicles → select the car → tick the three review checks → Approve.",
              "Show the updated dashboard and Audit trail to close the pitch.",
            ].map((text, index) => <li key={text} className="flex gap-3 text-sm leading-6 text-muted"><span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-[#e7f4eb] text-xs font-extrabold text-accent">{index + 1}</span><span>{text}</span></li>)}
          </ol>
        </div>
        <Link to="/admin" className="btn-primary mt-8">Open admin area <ArrowRight size={16} /></Link>
      </div>
    </main>
  );
}

function DemoAccount({ title, icon, detail }) {
  return <div className="rounded-2xl border border-line p-5"><span className="grid h-10 w-10 place-items-center rounded-xl bg-[#e7f4eb] text-accent">{icon}</span><h2 className="mt-4 font-extrabold text-ink">{title}</h2><p className="mt-2 text-sm leading-6 text-muted">{detail}</p></div>;
}

function AdminArea() {
  const { request, requestFile, signOut, user } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [toast, setToast] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [dashboardError, setDashboardError] = useState("");
  const [dashboardLoading, setDashboardLoading] = useState(true);
  const [owners, setOwners] = useState([]);
  const [vehicles, setVehicles] = useState([]);
  const [audits, setAudits] = useState([]);
  const [pageError, setPageError] = useState("");
  const [pageLoading, setPageLoading] = useState(false);
  const [selectedOwner, setSelectedOwner] = useState(null);
  const [selectedVehicle, setSelectedVehicle] = useState(null);
  const [confirm, setConfirm] = useState(null);
  const [actionBusy, setActionBusy] = useState(false);
  const [vehicleChecks, setVehicleChecks] = useState({});
  const [searchParams] = useSearchParams();
  const isExpiring = searchParams.get("view") === "expiring";
  const activeSection = location.pathname.split("/")[2] || "dashboard";

  function notify(message, type = "success") {
    setToast({ message, type, id: Date.now() });
  }

  useEffect(() => {
    if (!toast) return undefined;
    const timer = window.setTimeout(() => setToast(null), 4200);
    return () => window.clearTimeout(timer);
  }, [toast]);

  async function loadDashboard() {
    setDashboardLoading(true);
    setDashboardError("");
    try {
      setDashboard(await request(`${api}/dashboard`));
    } catch (error) {
      setDashboardError(error.message);
    } finally {
      setDashboardLoading(false);
    }
  }

  async function loadSection() {
    if (activeSection === "dashboard") return;
    setPageLoading(true);
    setPageError("");
    try {
      if (activeSection === "owners") setOwners(await request(`${api}/owners?status=pending`));
      if (activeSection === "vehicles") {
        setVehicles(await request(isExpiring ? `${api}/vehicles/expiring` : `${api}/vehicles?status=pending`));
      }
      if (activeSection === "audit") setAudits(await request(`${api}/audit?limit=50`));
    } catch (error) {
      setPageError(error.message);
    } finally {
      setPageLoading(false);
    }
  }

  useEffect(() => { loadDashboard(); }, []);
  useEffect(() => { loadSection(); }, [activeSection, isExpiring]);

  async function runAction(path, body, successMessage, updateList) {
    setActionBusy(true);
    updateList?.();
    try {
      await request(path, {
        method: "POST",
        ...(body ? { body: jsonBody(body) } : {}),
      });
      setSelectedOwner(null);
      setSelectedVehicle(null);
      setConfirm(null);
      notify(successMessage);
      void loadDashboard();
      if (activeSection === "audit") {
        setAudits(await request(`${api}/audit?limit=50`));
      }
    } catch (error) {
      notify(error.message || "That action didn’t go through. Please try again.", "error");
      void loadSection();
    } finally {
      setActionBusy(false);
    }
  }

  async function approveOwner(owner) {
    await runAction(
      `${api}/owners/${owner.user_id}/approve`,
      null,
      `${owner.full_name} is approved as an owner.`,
      () => setOwners((current) => current.filter((item) => item.user_id !== owner.user_id)),
    );
  }

  async function rejectOwner(owner, reason) {
    await runAction(
      `${api}/owners/${owner.user_id}/reject`,
      { reason },
      `${owner.full_name}’s application was rejected.`,
      () => setOwners((current) => current.filter((item) => item.user_id !== owner.user_id)),
    );
  }

  async function approveVehicle(vehicle) {
    await runAction(
      `${api}/vehicles/${vehicle.id}/approve`,
      null,
      `${vehicle.make} ${vehicle.model} is approved and ready to list.`,
      () => setVehicles((current) => current.filter((item) => item.id !== vehicle.id)),
    );
  }

  async function rejectVehicle(vehicle, reason) {
    await runAction(
      `${api}/vehicles/${vehicle.id}/reject`,
      { reason },
      `${vehicle.make} ${vehicle.model}’s listing was rejected.`,
      () => setVehicles((current) => current.filter((item) => item.id !== vehicle.id)),
    );
  }

  async function suspendVehicle(vehicle) {
    await runAction(
      `${api}/vehicles/${vehicle.id}/suspend`,
      null,
      `${vehicle.make} ${vehicle.model} has been suspended.`,
      () => setVehicles((current) => current.filter((item) => item.id !== vehicle.id)),
    );
  }

  const sectionName = activeSection === "dashboard" ? "Dashboard" : activeSection === "owners" ? "Owner review" : activeSection === "vehicles" ? isExpiring ? "Expiring documents" : "Vehicle review" : "Audit trail";
  const navItems = [
    { path: "/admin", label: "Dashboard", icon: <LayoutDashboard size={18} />, key: "dashboard" },
    { path: "/admin/owners", label: "Owners", icon: <UsersRound size={18} />, key: "owners", count: dashboard?.pending_owners },
    { path: "/admin/vehicles", label: "Vehicles", icon: <FileCheck2 size={18} />, key: "vehicles", count: dashboard?.pending_vehicles },
    { path: "/admin/audit", label: "Audit trail", icon: <Clock3 size={18} />, key: "audit" },
  ];

  return (
    <div className="min-h-[calc(100vh-73px)] bg-[#f5f7f5]">
      <div className="mx-auto grid max-w-[1440px] gap-6 px-4 py-5 sm:px-7 sm:py-8 lg:grid-cols-[230px_minmax(0,1fr)]">
        <aside className="h-fit rounded-3xl border border-line bg-white p-4 shadow-soft lg:sticky lg:top-5">
          <div className="hidden px-2 py-2 lg:block"><Logo /><p className="mt-3 text-[10px] font-extrabold uppercase tracking-[.15em] text-muted">Operations desk</p></div>
          <nav className="flex gap-2 overflow-x-auto lg:mt-5 lg:grid lg:gap-1">
            {navItems.map((item) => (
              <Link key={item.path} to={item.path} className={`flex shrink-0 items-center gap-3 rounded-xl px-3 py-3 text-sm font-bold transition ${activeSection === item.key ? "bg-[#eaf5ed] text-accent" : "text-muted hover:bg-canvas hover:text-ink"}`}>
                {item.icon}<span>{item.label}</span>{item.count > 0 && <span className="ml-auto rounded-full bg-white px-2 py-0.5 text-[10px] font-extrabold text-accent">{item.count}</span>}
              </Link>
            ))}
          </nav>
          <div className="mt-5 hidden border-t border-line pt-4 lg:block">
            <p className="truncate px-3 text-xs font-bold text-ink">{user?.full_name}</p><p className="truncate px-3 pt-1 text-[11px] text-muted">{user?.email}</p>
            <button onClick={signOut} className="mt-3 inline-flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-xs font-bold text-muted hover:bg-canvas hover:text-ink"><LogOut size={16} /> Sign out</button>
          </div>
        </aside>
        <section className="min-w-0">
          <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
            <div><p className="eyebrow">CarHire admin</p><h1 className="mt-1 text-2xl font-black tracking-tight text-ink">{sectionName}</h1></div>
            <div className="flex gap-2">
              <Link to="/demo" className="btn-secondary !min-h-10 !px-3 !py-2 text-xs">Demo guide</Link>
              <button onClick={() => { loadDashboard(); loadSection(); }} className="btn-secondary !min-h-10 !px-3 !py-2 text-xs" aria-label="Refresh admin data"><RefreshCw size={15} /> Refresh</button>
            </div>
          </div>
          {activeSection === "dashboard" && <DashboardView data={dashboard} loading={dashboardLoading} error={dashboardError} onRetry={loadDashboard} navigate={navigate} />}
          {activeSection === "owners" && <OwnerQueue owners={owners} loading={pageLoading} error={pageError} request={request} onRetry={loadSection} onSelect={setSelectedOwner} onError={(message) => notify(message, "error")} />}
          {activeSection === "vehicles" && <VehicleQueue vehicles={vehicles} loading={pageLoading} error={pageError} isExpiring={isExpiring} navigate={navigate} onRetry={loadSection} onSelect={(vehicle) => { setSelectedVehicle(vehicle); setVehicleChecks({}); }} />}
          {activeSection === "audit" && <AuditView audits={audits} loading={pageLoading} error={pageError} onRetry={loadSection} />}
        </section>
      </div>
      {selectedOwner && <OwnerReviewModal owner={selectedOwner} requestFile={requestFile} busy={actionBusy} onClose={() => setSelectedOwner(null)} onApprove={() => approveOwner(selectedOwner)} onReject={() => setConfirm({ type: "reject-owner", target: selectedOwner })} />}
      {selectedVehicle && <VehicleReviewModal vehicle={selectedVehicle} requestFile={requestFile} busy={actionBusy} isExpiring={isExpiring} checks={vehicleChecks} setChecks={setVehicleChecks} onClose={() => setSelectedVehicle(null)} onApprove={() => approveVehicle(selectedVehicle)} onReject={() => setConfirm({ type: "reject-vehicle", target: selectedVehicle })} onSuspend={() => setConfirm({ type: "suspend-vehicle", target: selectedVehicle })} />}
      {confirm && <ConfirmDialog confirm={confirm} busy={actionBusy} onCancel={() => setConfirm(null)} onConfirm={async (reason) => {
        if (confirm.type === "reject-owner") await rejectOwner(confirm.target, reason);
        if (confirm.type === "reject-vehicle") await rejectVehicle(confirm.target, reason);
        if (confirm.type === "suspend-vehicle") await suspendVehicle(confirm.target);
      }} />}
      {toast && <div role="status" className={`fixed bottom-5 right-5 z-[70] flex max-w-sm items-center gap-3 rounded-2xl px-4 py-3.5 text-sm font-semibold text-white shadow-card ${toast.type === "error" ? "bg-[#a52d2d]" : "bg-[#123d2e]"}`}><CheckCircle2 size={18} />{toast.message}<button onClick={() => setToast(null)} aria-label="Dismiss notification" className="ml-1 rounded-lg p-1 hover:bg-white/10"><X size={15} /></button></div>}
    </div>
  );
}

function DashboardView({ data, loading, error, onRetry, navigate }) {
  const cards = [
    { label: "Pending owners", value: data?.pending_owners, icon: <UsersRound size={20} />, tone: "green", link: "/admin/owners", hint: "Applications to review" },
    { label: "Pending vehicles", value: data?.pending_vehicles, icon: <FileCheck2 size={20} />, tone: "blue", link: "/admin/vehicles", hint: "Listings waiting for approval" },
    { label: "Approved today", value: data?.approved_today, icon: <BadgeCheck size={20} />, tone: "purple", link: "/admin/audit", hint: "Owner and vehicle decisions" },
    { label: "Expiring documents", value: data?.expiring_documents, icon: <ShieldAlert size={20} />, tone: "amber", link: "/admin/vehicles?view=expiring", hint: "Due in the next 14 days" },
  ];
  if (loading) return <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{cards.map((card) => <div key={card.label} className="skeleton h-36 rounded-3xl" />)}</div>;
  if (error) return <InlineError message={error} onRetry={onRetry} />;
  return (
    <>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map((card) => <button key={card.label} onClick={() => navigate(card.link)} className="rounded-3xl border border-line bg-white p-5 text-left shadow-soft transition hover:-translate-y-0.5 hover:shadow-card">
          <div className="flex items-start justify-between"><span className={`grid h-11 w-11 place-items-center rounded-2xl ${card.tone === "green" ? "bg-[#e7f4eb] text-accent" : card.tone === "blue" ? "bg-[#e9f1fb] text-[#3d6c9d]" : card.tone === "purple" ? "bg-[#f0ebfb] text-[#7459b4]" : "bg-[#fbf0dc] text-[#a8700d]"}`}>{card.icon}</span><ArrowRight size={17} className="text-[#a3ada6]" /></div>
          <p className="mt-5 text-3xl font-black tracking-tight text-ink">{card.value ?? "—"}</p><p className="mt-1 text-sm font-bold text-ink">{card.label}</p><p className="mt-1 text-xs text-muted">{card.hint}</p>
        </button>)}
      </div>
      <div className="mt-6 grid gap-5 xl:grid-cols-[1.3fr_.7fr]">
        <div className="rounded-3xl border border-line bg-white p-6 shadow-soft sm:p-7">
          <p className="eyebrow">A smooth handoff</p><h2 className="mt-2 text-xl font-black text-ink">Your review desk is ready.</h2><p className="mt-2 max-w-xl text-sm leading-6 text-muted">Owner details and supporting documents are together in one view. Approve a complete application in a click, or leave a clear reason if it needs another look.</p>
          <div className="mt-6 flex flex-wrap gap-3"><button onClick={() => navigate("/admin/owners")} className="btn-primary">Review owners <ArrowRight size={16} /></button><button onClick={() => navigate("/admin/vehicles")} className="btn-secondary">Review vehicles <ArrowRight size={16} /></button></div>
        </div>
        <div className="rounded-3xl bg-[#123d2e] p-6 text-white shadow-soft sm:p-7"><span className="grid h-11 w-11 place-items-center rounded-2xl bg-white/10 text-[#aee2c1]"><ShieldCheck size={21} /></span><h2 className="mt-5 text-lg font-extrabold">Safe, considered reviews</h2><p className="mt-2 text-sm leading-6 text-white/70">Sensitive documents are served only to authorized admins. Every approval, rejection and suspension leaves an audit record.</p><Link to="/admin/audit" className="mt-5 inline-flex items-center gap-2 text-sm font-bold text-[#aee2c1]">View audit trail <ArrowRight size={15} /></Link></div>
      </div>
    </>
  );
}

function OwnerQueue({ owners, loading, error, onRetry, request, onSelect, onError }) {
  if (loading) return <QueueSkeleton />;
  if (error) return <InlineError message={error} onRetry={onRetry} />;
  return (
    <div className="overflow-hidden rounded-3xl border border-line bg-white shadow-soft">
      <div className="flex items-center justify-between border-b border-line px-5 py-4 sm:px-6"><div><h2 className="font-extrabold text-ink">Pending owner applications</h2><p className="mt-1 text-xs text-muted">{owners.length} waiting for review</p></div><span className="rounded-full bg-[#fbf0dc] px-3 py-1.5 text-xs font-bold text-[#94630f]">Needs review</span></div>
      {owners.length ? <div className="divide-y divide-line">{owners.map((owner) => <button key={owner.user_id} onClick={async () => {
        try {
          onSelect(await request(`${api}/owners/${owner.user_id}`));
        } catch (loadError) {
          onError(loadError.message);
        }
      }} className="flex w-full items-center gap-4 px-5 py-4 text-left transition hover:bg-canvas sm:px-6">
        <span className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-[#e7f4eb] text-accent"><UsersRound size={20} /></span><span className="min-w-0 flex-1"><span className="block truncate font-extrabold text-ink">{owner.full_name}</span><span className="mt-1 block truncate text-xs text-muted">{owner.email} · {owner.phone}</span></span><span className="hidden text-right sm:block"><span className="block text-xs font-semibold text-muted">Submitted</span><span className="mt-1 block text-xs font-bold text-ink">{formatDate(owner.created_at)}</span></span><span className="rounded-full bg-[#fbf0dc] px-3 py-1.5 text-[11px] font-bold text-[#94630f]">Pending</span><ArrowRight size={17} className="shrink-0 text-muted" />
      </button>)}</div> : <EmptyState title="All caught up" text="There are no owner applications waiting for review." />}
    </div>
  );
}

function VehicleQueue({ vehicles, loading, error, isExpiring, navigate, onRetry, onSelect }) {
  if (loading) return <QueueSkeleton />;
  if (error) return <InlineError message={error} onRetry={onRetry} />;
  return (
    <>
      <div className="mb-4 flex gap-2">
        <button onClick={() => navigate("/admin/vehicles")} className={`rounded-xl px-4 py-2.5 text-xs font-bold ${!isExpiring ? "bg-accent text-white" : "border border-line bg-white text-muted"}`}>Pending review</button>
        <button onClick={() => navigate("/admin/vehicles?view=expiring")} className={`rounded-xl px-4 py-2.5 text-xs font-bold ${isExpiring ? "bg-accent text-white" : "border border-line bg-white text-muted"}`}>Expiring documents</button>
      </div>
      <div className="overflow-hidden rounded-3xl border border-line bg-white shadow-soft">
        <div className="flex items-center justify-between border-b border-line px-5 py-4 sm:px-6"><div><h2 className="font-extrabold text-ink">{isExpiring ? "Approved cars with expiring documents" : "Pending vehicle applications"}</h2><p className="mt-1 text-xs text-muted">{vehicles.length} {isExpiring ? "need a document check" : "waiting for review"}</p></div><span className={`rounded-full px-3 py-1.5 text-xs font-bold ${isExpiring ? "bg-red-50 text-red-700" : "bg-[#fbf0dc] text-[#94630f]"}`}>{isExpiring ? "Due soon" : "Needs review"}</span></div>
        {vehicles.length ? <div className="divide-y divide-line">{vehicles.map((vehicle) => <button key={vehicle.id} onClick={() => onSelect(vehicle)} className="flex w-full items-center gap-4 px-5 py-4 text-left transition hover:bg-canvas sm:px-6">
          <span className="grid h-12 w-16 shrink-0 place-items-center overflow-hidden rounded-xl bg-[#edf1ed]">{vehicle.photos?.length ? <QueueVehicleThumb photo={vehicle.photos[0]} /> : <Image size={20} className="text-muted" />}</span>
          <span className="min-w-0 flex-1"><span className="block truncate font-extrabold text-ink">{vehicle.year} {vehicle.make} {vehicle.model}</span><span className="mt-1 block truncate text-xs text-muted">{vehicle.plate} · {vehicle.owner_name || "CarHire fleet"} · {vehicle.location || "Kenya"}</span></span>
          {isExpiring ? <ExpirySummary vehicle={vehicle} /> : <span className="rounded-full bg-[#fbf0dc] px-3 py-1.5 text-[11px] font-bold text-[#94630f]">Pending</span>}
          <ArrowRight size={17} className="shrink-0 text-muted" />
        </button>)}</div> : <EmptyState title={isExpiring ? "No documents due soon" : "All caught up"} text={isExpiring ? "Approved vehicles have no insurance or inspection documents expiring in the next 14 days." : "There are no vehicles waiting for review."} />}
      </div>
    </>
  );
}

function ExpirySummary({ vehicle }) {
  const days = Math.min(daysUntil(vehicle.insurance_expiry), daysUntil(vehicle.inspection_expiry));
  return <span className={`hidden text-right text-xs font-bold sm:block ${days <= 14 ? "text-red-700" : "text-muted"}`}>Due in {days} days</span>;
}

function OwnerReviewModal({ owner, requestFile, busy, onClose, onApprove, onReject }) {
  const [detail, setDetail] = useState(owner);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    Promise.all([
      owner.id_document_download_url ? requestFileBlob(requestFile, owner.id_document_download_url) : Promise.resolve(null),
      owner.selfie_document_download_url ? requestFileBlob(requestFile, owner.selfie_document_download_url) : Promise.resolve(null),
    ]).then(([idImage, selfieImage]) => {
      if (active) setDetail({ ...owner, idImage, selfieImage });
    }).catch((loadError) => { if (active) setError(loadError.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [owner.user_id, requestFile]);
  return (
    <Modal title="Owner application" onClose={onClose}>
      <div className="mb-5 flex flex-wrap items-start justify-between gap-3"><div><p className="text-xl font-black text-ink">{owner.full_name}</p><p className="mt-1 text-sm text-muted">{owner.email} · {owner.phone}</p></div><span className="rounded-full bg-[#fbf0dc] px-3 py-1.5 text-xs font-bold text-[#94630f]">Pending review</span></div>
      <div className="grid gap-4 sm:grid-cols-2">
        <PrivatePreview title="National ID" path={owner.id_document_download_url} blob={detail.idImage} loading={loading} error={error} />
        <PrivatePreview title="Selfie" path={owner.selfie_document_download_url} blob={detail.selfieImage} loading={loading} error={error} />
      </div>
      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        <DetailValue label="National ID number" value={owner.national_id} />
        <DetailValue label="KRA PIN" value={owner.kra_pin} />
        <DetailValue label="Payout M-Pesa" value={owner.payout_phone} />
      </div>
      {error && <p role="alert" className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-800">{error}</p>}
      <div className="mt-6 flex flex-col-reverse gap-3 border-t border-line pt-5 sm:flex-row sm:justify-end"><button disabled={busy} onClick={onReject} className="btn-secondary !border-red-200 !text-red-700 hover:!bg-red-50">Reject</button><button disabled={busy || loading || !detail.idImage || !detail.selfieImage} onClick={onApprove} className="btn-primary">{busy ? <Spinner /> : <Check size={16} />} Approve owner</button></div>
      {(!owner.id_document_download_url || !owner.selfie_document_download_url) && <p className="mt-3 text-right text-xs text-muted">Both ID and selfie documents are required for approval.</p>}
    </Modal>
  );
}

function VehicleReviewModal({ vehicle, requestFile, busy, isExpiring, checks, setChecks, onClose, onApprove, onReject, onSuspend }) {
  const [documents, setDocuments] = useState({ logbook: null, insurance: null, ownerId: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    Promise.all([
      vehicle.logbook_download_url ? requestFileBlob(requestFile, vehicle.logbook_download_url) : Promise.resolve(null),
      vehicle.insurance_download_url ? requestFileBlob(requestFile, vehicle.insurance_download_url) : Promise.resolve(null),
      vehicle.owner_id_document_download_url ? requestFileBlob(requestFile, vehicle.owner_id_document_download_url) : Promise.resolve(null),
    ]).then(([logbook, insurance, ownerId]) => {
      if (active) setDocuments({ logbook, insurance, ownerId });
    }).catch((loadError) => { if (active) setError(loadError.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [vehicle.id, requestFile]);

  const checkItems = [
    { id: "plate", label: "Plate matches logbook" },
    { id: "owner", label: "Owner name matches ID" },
    { id: "insurance", label: "Insurance valid" },
  ];
  const readyToApprove = checkItems.every(({ id }) => checks[id]) &&
    vehicle.logbook_download_url && vehicle.insurance_download_url &&
    vehicle.insurance_expiry && vehicle.inspection_expiry &&
    daysUntil(vehicle.insurance_expiry) >= 0 && daysUntil(vehicle.inspection_expiry) >= 0 &&
    documents.logbook && documents.insurance && (!vehicle.owner_id || documents.ownerId) &&
    (!vehicle.owner_id || vehicle.owner_verification_status === "approved");
  const photoPaths = (vehicle.photos || []).map((photo) => {
    const id = photo.match(/vehicle-photos\/(\d+)/)?.[1];
    return id ? `${api}/vehicle-photos/${id}` : null;
  }).filter(Boolean);

  return (
    <Modal title={isExpiring ? "Document review" : "Vehicle application"} onClose={onClose}>
      <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xl font-black text-ink">{vehicle.year} {vehicle.make} {vehicle.model}</p><p className="mt-1 text-sm text-muted">{vehicle.plate} · {vehicle.owner_name || "CarHire fleet"} · {vehicle.location || "Kenya"}</p></div><StatusPill status={vehicle.approval_status} /></div>
      {photoPaths.length > 0 ? <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-3">{photoPaths.slice(0, 6).map((path) => <PrivatePreview key={path} title="Car photo" path={path} imageOnly />)}</div> : <div className="mt-5 rounded-2xl bg-canvas p-6 text-center text-sm text-muted">No vehicle photos were submitted.</div>}
      <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">{[
        ["Seats", vehicle.seats],
        ["Transmission", vehicle.transmission],
        ["Fuel", vehicle.fuel_type],
        ["Daily rate", `KES ${formatPrice(vehicle.daily_rate)}`],
        ["Deposit", `KES ${formatPrice(vehicle.deposit_amount)}`],
        ["Chassis", vehicle.chassis_number || "—"],
        ["Insurance expiry", vehicle.insurance_expiry],
        ["Inspection expiry", vehicle.inspection_expiry],
      ].map(([label, value]) => <DetailValue key={label} label={label} value={value} alert={label.endsWith("expiry") && daysUntil(value) <= 14} />)}</div>
      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        <PrivatePreview title="Owner ID" path={vehicle.owner_id_document_download_url} blob={documents.ownerId} loading={loading} error={error} />
        <PrivatePreview title="Logbook" path={vehicle.logbook_download_url} blob={documents.logbook} loading={loading} error={error} />
        <PrivatePreview title="Insurance certificate" path={vehicle.insurance_download_url} blob={documents.insurance} loading={loading} error={error} />
      </div>
      {error && <p role="alert" className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-800">{error}</p>}
      {!isExpiring && <div className="mt-5 rounded-2xl border border-line p-4">
        <h3 className="text-sm font-extrabold text-ink">Review checklist</h3><p className="mt-1 text-xs text-muted">Confirm each item before approving this listing.</p>
        <div className="mt-3 grid gap-2 sm:grid-cols-3">{checkItems.map((item) => <label key={item.id} className={`flex cursor-pointer items-center gap-2 rounded-xl border px-3 py-3 text-xs font-semibold transition ${checks[item.id] ? "border-accent bg-[#f1f8f3] text-accent" : "border-line text-muted"}`}><input type="checkbox" checked={Boolean(checks[item.id])} onChange={(event) => setChecks((current) => ({ ...current, [item.id]: event.target.checked }))} className="h-4 w-4 accent-[#147a55]" />{item.label}</label>)}</div>
      </div>}
      <div className="mt-6 flex flex-col-reverse gap-3 border-t border-line pt-5 sm:flex-row sm:justify-end">
        {isExpiring ? <button disabled={busy} onClick={onSuspend} className="btn-secondary !border-red-200 !text-red-700 hover:!bg-red-50"><ShieldAlert size={16} /> Suspend vehicle</button> : <button disabled={busy} onClick={onReject} className="btn-secondary !border-red-200 !text-red-700 hover:!bg-red-50">Reject</button>}
        {!isExpiring && <button disabled={busy || loading || !readyToApprove} onClick={onApprove} className="btn-primary">{busy ? <Spinner /> : <Check size={16} />} Approve vehicle</button>}
      </div>
      {!isExpiring && !readyToApprove && <p className="mt-3 text-right text-xs text-muted">Check all three items. Valid documents, dates and an approved owner are also required.</p>}
    </Modal>
  );
}

function AuditView({ audits, loading, error, onRetry }) {
  if (loading) return <QueueSkeleton />;
  if (error) return <InlineError message={error} onRetry={onRetry} />;
  return (
    <div className="overflow-hidden rounded-3xl border border-line bg-white shadow-soft">
      <div className="border-b border-line px-5 py-4 sm:px-6"><h2 className="font-extrabold text-ink">Recent review actions</h2><p className="mt-1 text-xs text-muted">Approvals, rejections and suspensions</p></div>
      {audits.length ? <div className="divide-y divide-line">{audits.map((audit) => <div key={audit.id} className="flex items-start gap-3 px-5 py-4 sm:px-6"><span className={`mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-xl ${audit.action === "approve" ? "bg-[#e7f4eb] text-accent" : audit.action === "reject" ? "bg-red-50 text-red-700" : "bg-[#fbf0dc] text-[#94630f]"}`}>{audit.action === "approve" ? <Check size={17} /> : audit.action === "suspend" ? <ShieldAlert size={17} /> : <X size={17} />}</span><div className="min-w-0 flex-1"><p className="text-sm font-bold capitalize text-ink">{actionPastTense(audit.action)} <span className="lowercase">{audit.target_type}</span> <span className="text-muted">#{audit.target_id}</span></p><p className="mt-1 text-xs text-muted">{audit.actor_name || "Admin"} · {formatDateTime(audit.created_at)}</p>{audit.reason && <p className="mt-2 rounded-lg bg-canvas px-3 py-2 text-xs text-muted">{audit.reason}</p>}</div></div>)}</div> : <EmptyState title="No audit actions yet" text="Admin approvals, rejections and suspensions will show here." />}
    </div>
  );
}

function PrivatePreview({ title, path, blob, loading, error, imageOnly = false }) {
  const [url, setUrl] = useState("");
  const [contentType, setContentType] = useState("");
  useEffect(() => {
    if (!path || !blob) return undefined;
    const nextUrl = URL.createObjectURL(blob);
    setUrl(nextUrl);
    setContentType(blob.type);
    return () => URL.revokeObjectURL(nextUrl);
  }, [path, blob]);

  if (imageOnly && path) {
    return <PrivatePhoto title={title} path={path} />;
  }
  if (!path) return <div className="flex min-h-32 flex-col items-center justify-center rounded-2xl border border-dashed border-line bg-canvas p-4 text-center"><FileText size={22} className="text-muted" /><p className="mt-2 text-xs font-bold text-muted">{title} not uploaded</p></div>;
  if (loading) return <div className="skeleton min-h-40 rounded-2xl" />;
  if (error) return <div role="alert" className="rounded-2xl bg-red-50 p-4 text-xs text-red-800">{error}</div>;
  if (!blob) return <div className="rounded-2xl border border-line p-4"><p className="text-xs font-bold text-ink">{title}</p><p className="mt-2 text-xs text-muted">Document could not be loaded.</p></div>;
  return <div className="overflow-hidden rounded-2xl border border-line bg-white"><div className="flex items-center gap-2 border-b border-line px-3 py-2.5"><FileText size={15} className="text-accent" /><span className="text-xs font-bold text-ink">{title}</span></div>{contentType === "application/pdf" ? <iframe title={title} src={url} className="h-48 w-full bg-canvas" /> : <img src={url} alt={title} className="h-48 w-full object-contain bg-[#f4f6f4]" />}</div>;
}

function PrivatePhoto({ title, path }) {
  const { requestFile } = useAuth();
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    let objectUrl;
    requestFile(path).then((blob) => {
      objectUrl = URL.createObjectURL(blob);
      if (active) setUrl(objectUrl);
    }).catch((loadError) => { if (active) setError(loadError.message); });
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [path, requestFile]);
  return <div className="relative min-h-28 overflow-hidden rounded-2xl bg-[#edf1ed]">{url ? <img src={url} alt={title} className="h-36 w-full object-cover" /> : error ? <span className="grid h-36 place-items-center text-xs text-red-700">Photo unavailable</span> : <div className="skeleton h-36" />}<span className="absolute bottom-2 left-2 rounded-lg bg-white/90 px-2 py-1 text-[10px] font-bold text-ink">{title}</span></div>;
}

async function requestFileBlob(requestFile, path) {
  return requestFile(path);
}

function QueueVehicleThumb({ photo }) {
  const fileId = photo.match(/vehicle-photos\/(\d+)/)?.[1];
  if (!fileId) return <Image size={20} className="text-muted" />;
  return <PrivatePhoto title="" path={`${api}/vehicle-photos/${fileId}`} />;
}

function ConfirmDialog({ confirm, busy, onCancel, onConfirm }) {
  const [reason, setReason] = useState("");
  const requiresReason = confirm.type.startsWith("reject");
  const isSuspend = confirm.type === "suspend-vehicle";
  const targetName = confirm.target.full_name || `${confirm.target.make} ${confirm.target.model}`;
  const [error, setError] = useState("");
  return (
    <div className="fixed inset-0 z-[60] grid place-items-center overflow-y-auto bg-[#10251b]/45 p-4" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !busy) onCancel(); }}>
      <section role="dialog" aria-modal="true" aria-labelledby="confirm-title" className="w-full max-w-md rounded-3xl bg-white p-6 shadow-card">
        <h2 id="confirm-title" className="text-lg font-black text-ink">{isSuspend ? "Suspend this vehicle?" : `Reject ${confirm.type === "reject-owner" ? "owner application" : "vehicle listing"}?`}</h2>
        <p className="mt-2 text-sm leading-6 text-muted">{isSuspend ? `${targetName} will be hidden from renters until it is reviewed again.` : `This will record a rejection for ${targetName}. The reason will be saved in the audit trail.`}</p>
        {requiresReason && <label className="mt-5 block"><span className="mb-2 block text-xs font-bold text-ink">Reason for rejection</span><textarea required minLength="1" maxLength="1000" value={reason} onChange={(event) => setReason(event.target.value)} rows="4" className="field min-h-28 resize-y py-3" placeholder="Tell the applicant what needs to change." /></label>}
        {error && <p role="alert" className="mt-3 text-xs text-red-700">{error}</p>}
        <div className="mt-6 flex justify-end gap-3"><button disabled={busy} onClick={onCancel} className="btn-secondary">Cancel</button><button disabled={busy || (requiresReason && !reason.trim())} onClick={async () => {
          setError("");
          try { await onConfirm(reason.trim()); } catch (confirmError) { setError(confirmError.message); }
        }} className={`btn-primary ${requiresReason || isSuspend ? "!bg-red-700 hover:!bg-red-800" : ""}`}>{busy ? <Spinner /> : isSuspend ? <ShieldAlert size={16} /> : <Check size={16} />}{isSuspend ? "Suspend vehicle" : "Confirm rejection"}</button></div>
      </section>
    </div>
  );
}

function Modal({ title, children, onClose }) {
  useEffect(() => {
    const closeOnEscape = (event) => { if (event.key === "Escape") onClose(); };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [onClose]);
  return (
    <div className="fixed inset-0 z-50 grid place-items-center overflow-y-auto bg-[#10251b]/50 p-3 sm:p-6" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section role="dialog" aria-modal="true" aria-label={title} className="my-auto max-h-[92vh] w-full max-w-4xl overflow-y-auto rounded-[1.75rem] bg-white p-5 shadow-card sm:p-7">
        <div className="mb-5 flex items-center justify-between border-b border-line pb-4"><p className="text-xs font-bold uppercase tracking-[.12em] text-muted">{title}</p><button onClick={onClose} aria-label="Close dialog" className="grid h-9 w-9 place-items-center rounded-xl text-muted hover:bg-canvas hover:text-ink"><X size={19} /></button></div>
        {children}
      </section>
    </div>
  );
}

function DetailValue({ label, value, alert = false }) {
  return <div className={`min-w-0 rounded-xl p-3 ${alert ? "bg-red-50" : "bg-canvas"}`}><p className="text-[10px] font-bold uppercase tracking-wider text-muted">{label}</p><p className={`mt-1 break-words text-sm font-bold ${alert ? "text-red-700" : "text-ink"}`}>{value || "—"}</p></div>;
}

function StatusPill({ status }) {
  const style = status === "approved" ? "bg-[#e7f4eb] text-accent" : status === "rejected" || status === "suspended" ? "bg-red-50 text-red-700" : "bg-[#fbf0dc] text-[#94630f]";
  return <span className={`shrink-0 rounded-full px-3 py-1.5 text-[11px] font-bold capitalize ${style}`}>{status || "pending"}</span>;
}

function InlineError({ message, onRetry }) {
  return <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-800"><span>{message}</span><button onClick={onRetry} className="font-bold underline underline-offset-2">Try again</button></div>;
}

function EmptyState({ title, text }) {
  return <div className="px-6 py-14 text-center"><span className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-canvas text-accent"><CheckCircle2 size={22} /></span><h3 className="mt-4 font-extrabold text-ink">{title}</h3><p className="mx-auto mt-2 max-w-sm text-sm leading-6 text-muted">{text}</p></div>;
}

function QueueSkeleton() {
  return <div className="overflow-hidden rounded-3xl border border-line bg-white p-5">{[0, 1, 2, 3].map((item) => <div key={item} className="flex items-center gap-4 border-b border-line py-4 last:border-0"><span className="skeleton h-12 w-12 rounded-2xl" /><span className="flex-1"><span className="skeleton block h-4 w-1/3 rounded-full" /><span className="skeleton mt-2 block h-3 w-1/2 rounded-full" /></span></div>)}</div>;
}

function Spinner() {
  return <span aria-label="Loading" className="h-4 w-4 animate-spin rounded-full border-2 border-current border-r-transparent" />;
}

function formatPrice(amount) {
  return new Intl.NumberFormat("en-KE", { maximumFractionDigits: 0 }).format(Number(amount || 0));
}

function formatDate(value) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("en-KE", { day: "numeric", month: "short", year: "numeric" }).format(new Date(value));
}

function formatDateTime(value) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("en-KE", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }).format(new Date(value));
}

function daysUntil(value) {
  if (!value) return Number.POSITIVE_INFINITY;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const expiry = new Date(`${value}T00:00:00`);
  return Math.ceil((expiry - today) / 86400000);
}

function actionPastTense(action) {
  return { approve: "Approved", reject: "Rejected", suspend: "Suspended" }[action] || action;
}
