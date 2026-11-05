# CarHire

## Google sign-in

Configure the Google OAuth web client ID as `GOOGLE_CLIENT_ID` in the backend
environment and `VITE_GOOGLE_CLIENT_ID` in the frontend environment. Use the
same client ID for both. Google-created accounts still need a phone number and
phone verification before they can apply as an owner or use booking flows.

## AI vehicle search

The public `POST /api/assistant/search` endpoint uses the Anthropic API when
`ANTHROPIC_API_KEY` is configured. Set `ANTHROPIC_MODEL` to choose the model
(defaults to `claude-3-5-haiku-latest`). Without a key, or if the Anthropic
request fails, searches use keyword matching against known vehicle makes,
models, and locations, as well as transmission, fuel type, and prices stated
after “under”. Requests without a key return the reply “AI mode is off, showing
keyword results”. The endpoint is limited to 10 requests per minute per IP
address.

## Demo data

From `backend/`, run `python -m app.seed_demo` to add six sample approved
vehicles and one approved demo owner. The seed uses reserved placeholder
identity/contact values and image URLs, creates no identity documents, and is
safe to run repeatedly.

## Pickup locations and nearby search

Vehicle listings show an owner-entered pickup area. Owners can set the area
and map pin while listing or editing a car; exact coordinates are only shared
with the owner, admins, and a customer after their booking is confirmed.
Customers can search by town/area or use “Near me”; browser coordinates are
used for that search only and are neither stored nor included in access logs.
Nearby results are distance-sorted and show rounded distances.

The backend reverse-geocodes owner-selected pins through Nominatim and caches
the results. Apply the Alembic migrations with `alembic upgrade head` from
`backend/` to add vehicle coordinates and the geocoding cache.

## Booking holds

Unpaid pending bookings hold their dates for 30 minutes. Run
`python -m app.jobs.check_expiry` at least once per minute to release expired
holds; booking and availability requests also release expired holds.

Booking intervals include `start_date` and exclude `end_date` (the checkout
date). Verified users can create bookings at `POST /api/bookings`, review their
bookings at `GET /api/bookings/me`, and cancel before the start date at
`POST /api/bookings/{id}/cancel`. Vehicle availability is returned as blocked
date ranges from `GET /api/vehicles/{id}/availability?from=YYYY-MM-DD&to=YYYY-MM-DD`.
Owners can review bookings for their vehicles at `GET /api/owners/me/bookings`;
admins can review all bookings at `GET /api/admin/bookings`. Owners can block
dates on their own vehicles and admins on any vehicle with
`POST /api/vehicles/{id}/blocks`; remove a block with
`DELETE /api/vehicles/{id}/blocks/{block_id}`. Public availability includes
both booking and owner/admin blocks. Vehicle search accepts `available_from`
and `available_to` to omit cars with conflicts.