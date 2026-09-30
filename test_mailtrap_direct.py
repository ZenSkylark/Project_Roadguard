import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ⚠️ PASTE YOUR ACTUAL MAILTRAP CREDENTIALS HERE
USERNAME = "266acb407b9615"
PASSWORD = "954212bcfdb008"

msg = MIMEMultipart()
msg["From"] = "noreply@roadguard.ph"
msg["To"] = "anyone@example.com"  # Mailtrap captures ALL recipients, this can be anything
msg["Subject"] = "Direct Mailtrap Test"
msg.attach(MIMEText("If you see this in your sandbox, Mailtrap SMTP is working!", "plain"))

try:
    with smtplib.SMTP("sandbox.smtp.mailtrap.io", 2525) as server:
        server.login(USERNAME, PASSWORD)
        server.send_message(msg)
    print("✅ SUCCESS! Check your Mailtrap sandbox inbox now.")
except Exception as e:
    print(f"❌ FAILED: {e}")