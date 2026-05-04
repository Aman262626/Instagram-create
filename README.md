# IG Account Creator – Web App

A web-based Instagram account creator with a clean, step-by-step UI.  
Designed to be deployed on **Vercel** using Python serverless functions.

## Features

- **Step 1** – Enter your email address  
- **Step 2** – Verify the 6-digit OTP sent to your inbox  
- **Step 3** – Account is created automatically with a random Indian-style username  
- Copy username, password, and session cookies with one click

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Vanilla HTML / CSS / JS |
| Backend | Python (Flask) – Vercel Serverless Functions |
| API | Instagram private web API |

## Deploy to Vercel

1. Push this repo to GitHub.
2. Import the repository in [Vercel](https://vercel.com/new).
3. Vercel will auto-detect the `vercel.json` configuration.
4. Add a `SECRET_KEY` environment variable in Vercel → Settings → Environment Variables.  
   Generate one with: `python -c "import secrets; print(secrets.token_hex(32))"`
5. Click **Deploy**.

## Local Development

```bash
pip install -r requirements.txt
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
cd api && flask --app index run --debug
```

Then open `http://localhost:5000`.

## Project Structure

```
├── api/
│   └── index.py          # Flask API (serverless on Vercel)
├── public/
│   └── index.html         # Frontend UI
├── requirements.txt       # Python dependencies
├── vercel.json            # Vercel build & routing config
└── README.md
```

## How It Works

1. **Send Code** – Initialises an Instagram web session and sends a verification email.  
2. **Verify OTP** – Confirms the email code via Instagram's API.  
3. **Create Account** – Generates a random username/password and registers the account.

Session state is passed between steps as a signed token (via `itsdangerous`) so the serverless functions remain stateless and tamper-proof.
