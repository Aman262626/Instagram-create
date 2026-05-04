import base64
import hashlib
import json
import os
import random
import re
import secrets
import string
import time

from cryptography.fernet import Fernet, InvalidToken
from flask import Flask, request, jsonify, send_from_directory
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import requests as http_requests
import names

app = Flask(__name__, static_folder="../public", static_url_path="")

_secret = os.environ.get("SECRET_KEY")
if not _secret:
    raise RuntimeError(
        "SECRET_KEY environment variable must be set. "
        "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
    )
app.config["SECRET_KEY"] = _secret

_serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])
_fernet_key = base64.urlsafe_b64encode(hashlib.sha256(_secret.encode()).digest())
_fernet = Fernet(_fernet_key)

# ─── Indian name lists for username generation ───

INDIAN_FIRST_NAMES = [
    "Aman", "Vihaan", "Vivaan", "Ananya", "Diya", "Advik", "Kabir",
    "Aaradhya", "Reyansh", "Sai", "Arjun", "Ishaan", "Rudra", "Sia",
    "Myra", "Ayaan", "Shaurya", "Anaya", "Krisha", "Kavya", "Rohan",
    "Shreya", "Ishita", "Yash", "Priya", "Riya", "Rahul", "Amit",
    "Sumit", "Pooja", "Neha", "Raj", "Simran", "Aditya", "Krishna",
    "Laksh", "Tanvi", "Ishika", "Ved", "Yuvraj", "Anushka", "Divya",
    "Sanya", "Ria", "Jay", "Virat", "Ravindra", "Sneha", "Nikhil",
]

INDIAN_LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Kumar", "Singh", "Patel", "Reddy",
    "Rao", "Yadav", "Jha", "Malhotra", "Mehta", "Choudhary", "Thakur",
    "Mishra", "Trivedi", "Dwivedi", "Pandey", "Tiwari", "Joshi",
    "Desai", "Shah", "Nair", "Menon", "Iyer", "Khan", "Ansari", "Sheikh",
]


def _generate_username():
    first = random.choice(INDIAN_FIRST_NAMES).lower()
    last = random.choice(INDIAN_LAST_NAMES).lower()
    num = random.randint(10, 9999)
    return f"{first}{last}{num}"


def _get_ig_headers():
    ua = (
        f"Mozilla/5.0 (Linux; Android {random.randint(9, 13)}; "
        f"{''.join(random.choices(string.ascii_uppercase, k=3))}"
        f"{random.randint(111, 999)}) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
    )
    try:
        cookies = http_requests.get(
            "https://www.instagram.com/api/v1/web/accounts/login/ajax/",
            headers={"user-agent": ua},
            timeout=20,
        ).cookies
        resp = http_requests.get(
            "https://www.instagram.com/",
            headers={"user-agent": ua},
            timeout=20,
        )
        appid = resp.text.split('APP_ID":"')[1].split('"')[0]
        rollout = resp.text.split('rollout_hash":"')[1].split('"')[0]
        return {
            "authority": "www.instagram.com",
            "accept": "*/*",
            "content-type": "application/x-www-form-urlencoded",
            "cookie": f"csrftoken={cookies['csrftoken']}; mid={cookies['mid']}; ig_did={cookies['ig_did']}",
            "user-agent": ua,
            "x-csrftoken": cookies["csrftoken"],
            "x-ig-app-id": appid,
            "x-instagram-ajax": rollout,
        }
    except Exception:
        return None


def _encode_session(data):
    payload = json.dumps(data).encode()
    encrypted = _fernet.encrypt(payload)
    return _serializer.dumps(encrypted.decode())


def _decode_session(token, max_age=600):
    encrypted_str = _serializer.loads(token, max_age=max_age)
    decrypted = _fernet.decrypt(encrypted_str.encode())
    return json.loads(decrypted)


# ─── Serve the frontend ───

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


# ─── API: send verification email ───

@app.route("/api/send-code", methods=["POST"])
def send_code():
    body = request.get_json(force=True)
    email = body.get("email", "").strip()
    if not email:
        return jsonify({"ok": False, "error": "Email is required."}), 400

    headers = _get_ig_headers()
    if not headers:
        return jsonify({"ok": False, "error": "Could not initialize session. Please try again."}), 502

    try:
        mid = headers["cookie"].split("mid=")[1].split(";")[0]
        data = {"device_id": mid, "email": email}
        r = http_requests.post(
            "https://www.instagram.com/api/v1/accounts/send_verify_email/",
            headers=headers,
            data=data,
            timeout=20,
        )
        if 'email_sent":true' in r.text:
            session_token = _encode_session({"email": email, "headers": headers})
            return jsonify({"ok": True, "session_token": session_token})
        else:
            return jsonify({"ok": False, "error": r.text[:200]}), 400
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


# ─── API: verify OTP ───

@app.route("/api/verify-otp", methods=["POST"])
def verify_otp():
    body = request.get_json(force=True)
    otp = body.get("otp", "").strip()
    session_token = body.get("session_token", "")

    if not otp or not session_token:
        return jsonify({"ok": False, "error": "OTP and session token are required."}), 400

    try:
        sess = _decode_session(session_token)
    except (BadSignature, SignatureExpired, InvalidToken):
        return jsonify({"ok": False, "error": "Invalid or expired session. Please restart."}), 400

    headers = sess["headers"]
    email = sess["email"]

    try:
        mid = headers["cookie"].split("mid=")[1].split(";")[0]
        v_data = {"code": otp, "device_id": mid, "email": email}
        v_res = http_requests.post(
            "https://www.instagram.com/api/v1/accounts/check_confirmation_code/",
            headers=headers,
            data=v_data,
            timeout=20,
        )
        if 'status":"ok' in v_res.text:
            signup_code = v_res.json().get("signup_code")
            sess["signup_code"] = signup_code
            new_token = _encode_session(sess)
            return jsonify({"ok": True, "session_token": new_token})
        else:
            return jsonify({"ok": False, "error": "Invalid OTP. Try again."}), 400
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


# ─── API: create account ───

@app.route("/api/create-account", methods=["POST"])
def create_account():
    body = request.get_json(force=True)
    session_token = body.get("session_token", "")

    if not session_token:
        return jsonify({"ok": False, "error": "Session token is required."}), 400

    try:
        sess = _decode_session(session_token)
    except (BadSignature, SignatureExpired, InvalidToken):
        return jsonify({"ok": False, "error": "Invalid or expired session. Please restart."}), 400

    headers = sess["headers"]
    email = sess["email"]
    signup_code = sess.get("signup_code")

    try:
        fname = names.get_first_name()
        uname = _generate_username()
        pwd = f"{fname}@{secrets.randbelow(889) + 111}"

        mid = headers["cookie"].split("mid=")[1].split(";")[0]
        ig_did = headers["cookie"].split("ig_did=")[1].split(";")[0]
        csrftoken = headers["x-csrftoken"]

        create_data = {
            "enc_password": f"#PWD_INSTAGRAM_BROWSER:0:{round(time.time())}:{pwd}",
            "email": email,
            "username": uname,
            "first_name": fname,
            "month": random.randint(1, 12),
            "day": random.randint(1, 28),
            "year": random.randint(1992, 2002),
            "client_id": mid,
            "seamless_login_enabled": "1",
            "tos_version": "row",
            "force_sign_up_code": signup_code,
        }

        res = http_requests.post(
            "https://www.instagram.com/api/v1/web/accounts/web_create_ajax/",
            headers=headers,
            data=create_data,
            timeout=20,
        )

        if '"account_created":true' in res.text:
            sid = res.cookies.get("sessionid", "")
            full_cookies = f"mid={mid}; ig_did={ig_did}; csrftoken={csrftoken}; sessionid={sid}"
            return jsonify({
                "ok": True,
                "username": uname,
                "password": pwd,
                "cookies": full_cookies,
            })
        else:
            return jsonify({"ok": False, "error": "Account creation failed. Try again."}), 400
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


# ─── Temp Mail helpers (mail.tm) ───

def _mail_random_string(length=12):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def _mail_get_domain():
    try:
        r = http_requests.get("https://api.mail.tm/domains", timeout=10)
        return r.json()["hydra:member"][0]["domain"]
    except Exception:
        return None


# ─── API: create temp email ───

@app.route("/api/create-email", methods=["POST"])
def create_temp_email():
    domain = _mail_get_domain()
    if not domain:
        return jsonify({"ok": False, "error": "Could not fetch mail domain."}), 502

    addr = _mail_random_string() + "@" + domain
    pwd = _mail_random_string(16)

    try:
        http_requests.post(
            "https://api.mail.tm/accounts",
            json={"address": addr, "password": pwd},
            timeout=10,
        )
        tok_resp = http_requests.post(
            "https://api.mail.tm/token",
            json={"address": addr, "password": pwd},
            timeout=10,
        )
        token = tok_resp.json().get("token")
        if not token:
            return jsonify({"ok": False, "error": "Failed to authenticate temp email."}), 502

        mail_token = _encode_session({"mail_addr": addr, "mail_token": token})
        return jsonify({"ok": True, "email": addr, "mail_token": mail_token})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


# ─── API: check inbox for OTP ───

@app.route("/api/check-otp", methods=["POST"])
def check_otp():
    body = request.get_json(force=True)
    mail_token_str = body.get("mail_token", "")
    if not mail_token_str:
        return jsonify({"ok": False, "error": "Mail token is required."}), 400

    try:
        mt = _decode_session(mail_token_str)
    except (BadSignature, SignatureExpired, InvalidToken):
        return jsonify({"ok": False, "error": "Mail session expired. Generate a new email."}), 400

    bearer = mt["mail_token"]
    headers = {"Authorization": f"Bearer {bearer}"}

    try:
        inbox = http_requests.get(
            "https://api.mail.tm/messages", headers=headers, timeout=10
        ).json().get("hydra:member", [])

        codes = []
        for msg in inbox[:5]:
            msg_data = http_requests.get(
                f"https://api.mail.tm/messages/{msg['id']}",
                headers=headers,
                timeout=10,
            ).json()
            text = (msg_data.get("text", "") + " " + msg_data.get("subject", ""))
            found = re.findall(r"\b\d{4,8}\b", text)
            codes.extend(found)

        codes = list(dict.fromkeys(codes))
        return jsonify({"ok": True, "codes": codes})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
