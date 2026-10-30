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