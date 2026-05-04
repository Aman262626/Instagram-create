# IG Account Creator – Web App

A web-based Instagram account creator with a clean, step-by-step UI.  
Designed to be deployed on **Vercel** using Python serverless functions.

## Features

- **Temp Email** – Generate a disposable email with one click (via mail.tm, no API key needed)  
- **Auto OTP** – Inbox is polled automatically to detect and fill the OTP  
- **Manual Email** – Or enter your own email address  
- **Account History** – All created accounts stored locally in the browser  
- Copy username, password, and cookies with one click

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
4. Click **Deploy** – works out of the box, no extra settings needed.

> **Optional:** For extra security, add a `SECRET_KEY` environment variable in Vercel → Settings → Environment Variables.

## Local Development

```bash
pip install -r requirements.txt
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

1. **Generate Email** – Creates a temp email via mail.tm, or use your own.  
2. **Send Code** – Initialises an Instagram web session and sends a verification email.  
3. **Auto OTP** – Polls the temp inbox for the OTP code (or enter manually).  
4. **Create Account** – Generates a random username/password and registers the account.  
5. **History** – Saves all account info (email, username, password) in the browser.

Session state is encrypted (Fernet/AES) and signed so the serverless functions remain stateless and tamper-proof.
