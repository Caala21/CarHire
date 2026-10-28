import smtplib
from email.message import EmailMessage
from typing import Protocol
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.core.config import settings
from app.models.enums import VerificationChannel


class VerificationSender(Protocol):
    def send(self, destination: str, code: str) -> None: ...


class ConsoleVerificationSender:
    def __init__(self, channel: VerificationChannel, user_id: int):
        self.channel = channel
        self.user_id = user_id

    def send(self, destination: str, code: str) -> None:
        if settings.production:
            raise RuntimeError("Console verification delivery is disabled in production")
        print(
            f"[DEV VERIFICATION] channel={self.channel.value} "
            f"user={self.user_id} code={code}",
            flush=True,
        )


class SMTPEmailVerificationSender:
    def send(self, destination: str, code: str) -> None:
        if settings.smtp_host is None or settings.smtp_from_email is None:
            raise RuntimeError("SMTP verification is not fully configured")

        message = EmailMessage()
        message["Subject"] = "CarHire verification code"
        message["From"] = settings.smtp_from_email
        message["To"] = destination
        message.set_content(
            f"Your CarHire verification code is {code}. It expires in 10 minutes."
        )

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as client:
            if settings.smtp_starttls:
                client.starttls()
            if settings.smtp_username:
                if settings.smtp_password is None:
                    raise RuntimeError("SMTP_PASSWORD is required when SMTP_USERNAME is set")
                client.login(settings.smtp_username, settings.smtp_password.get_secret_value())
            client.send_message(message)


class AfricasTalkingSMSVerificationSender:
    def send(self, destination: str, code: str) -> None:
        if (
            settings.africastalking_username is None
            or settings.africastalking_api_key is None
        ):
            raise RuntimeError("Africa's Talking SMS verification is not fully configured")

        base_url = (
            "https://api.sandbox.africastalking.com"
            if settings.africastalking_sandbox
            else "https://api.africastalking.com"
        )
        form_data = {
            "username": settings.africastalking_username,
            "to": destination,
            "message": f"Your CarHire verification code is {code}. It expires in 10 minutes.",
        }
        if settings.africastalking_sender_id:
            form_data["from"] = settings.africastalking_sender_id

        request = Request(
            f"{base_url}/version1/messaging",
            data=urlencode(form_data).encode("ascii"),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
                "apiKey": settings.africastalking_api_key.get_secret_value(),
            },
            method="POST",
        )
        with urlopen(request, timeout=10) as response:
            if response.status >= 400:
                raise RuntimeError(
                    f"Africa's Talking SMS delivery failed with HTTP {response.status}"
                )


def send_verification_code(
    channel: VerificationChannel, destination: str, code: str, user_id: int
) -> None:
    if channel is VerificationChannel.EMAIL:
        if settings.verification_email_sender == "smtp":
            sender: VerificationSender = SMTPEmailVerificationSender()
        else:
            sender = ConsoleVerificationSender(channel, user_id)
    elif settings.verification_sms_sender == "africastalking":
        sender = AfricasTalkingSMSVerificationSender()
    else:
        sender = ConsoleVerificationSender(channel, user_id)

    sender.send(destination, code)
