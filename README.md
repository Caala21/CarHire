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
admins can review all bookings at `GET /api/admin/bookings`.