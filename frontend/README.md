# CarHire frontend

Mobile-first React + Vite client for the FastAPI car hire API.

## Run locally

```sh
npm install
cp .env.example .env
npm run dev
```

Set `VITE_API_URL` to the FastAPI origin (for example `http://localhost:8000`).
The frontend calls the routes documented by the API's `/openapi.json`.

Access and refresh tokens are stored in browser local storage so a session
survives page refreshes. An expired access token is refreshed once and the
original request is retried; if the refresh token has expired, the app asks the
user to sign in again.

## Admin pitch demo

The app does not ship hard-coded credentials or seeded records. Create these
two accounts in your development database before the pitch:

| Demo account | Email | Setup |
|---|---|---|
| Administrator | `demo.admin@example.com` | Provision with the command below; enter the password at the prompt. |
| Owner applicant | `demo.owner@example.com` | Create at `/signup`, using phone `254700000002`; choose a password and verify the phone. |

Provision the administrator with the backend command. It prompts for a password
and does not put it in shell history:

```sh
cd backend
.venv/bin/python -m app.jobs.seed_admin demo.admin@example.com \
  --name "Demo Admin" --phone 254700000001
```

For the owner account, use the verification code printed in the API server log.
Submit both owner documents and the vehicle listing (including its photos,
logbook and insurance) before beginning the review pitch.

Click path:

1. Open `/demo` for the short overview, then choose **Open admin area**.
2. Sign in at `/admin` as `demo.admin@example.com`.
3. Open **Owners**, select the pending application and review the ID and selfie.
4. Choose **Approve owner** (or **Reject**, which requires a reason).
5. Open **Vehicles**, select the pending car, review its photos and documents,
   tick all three review checks, then choose **Approve vehicle**.
6. Show **Dashboard** and **Audit trail** for the updated counts and decision.

**Reset demo data:** there is deliberately no in-app reset action. Reset only a
local development database using the team's development database workflow;
never reset production data for a demo.
