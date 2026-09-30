import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ⚠️ PASTE YOUR RESEND API KEY HERE
API_KEY = ""

# ⚠️ This MUST be the email you signed up to Resend with
YOUR_EMAIL = ""

msg = MIMEMultipart()
msg["From"] = "onboarding@resend.dev"
msg["To"] = YOUR_EMAIL
msg["Subject"] = "Resend Direct Test from Roadguard"
msg.attach(MIMEText("If you got this in your REAL inbox, Resend SMTP works!", "plain"))

try:
    with smtplib.SMTP_SSL("smtp.resend.com", 465) as server:
        server.login("resend", API_KEY)
        server.send_message(msg)
    print(f"✅ SUCCESS! Check your REAL inbox at {YOUR_EMAIL}")
except Exception as e:
    print(f"❌ FAILED: {e}")