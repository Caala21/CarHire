import smtplib
from email.message import EmailMessage
from typing import Protocol

from app.core.config import settings


class PasswordResetSender(Protocol):
    def send(self, destination: str, reset_link: str) -> None: ...


class ConsolePasswordResetSender:
    def __init__(self, user_id: int):
        self.user_id = user_id

    def send(self, destination: str, reset_link: str) -> None:
        if settings.production:
            raise RuntimeError("Console password reset delivery is disabled in production")
        print(
            f"[DEV PASSWORD RESET] user={self.user_id} link={reset_link}",
            flush=True,
        )


class SMTPPasswordResetSender:
    def send(self, destination: str, reset_link: str) -> None:
        if settings.smtp_host is None or settings.smtp_from_email is None:
            raise RuntimeError("SMTP password reset delivery is not fully configured")

        message = EmailMessage()
        message["Subject"] = "Reset your CarHire password"
        message["From"] = settings.smtp_from_email
        message["To"] = destination
        message.set_content(
            "We received a request to reset your CarHire password. "
            "This link expires in 30 minutes and can only be used once:\n\n"
            f"{reset_link}\n\n"
            "If you did not request this, you can ignore this email."
        )

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as client:
            if settings.smtp_starttls:
                client.starttls()
            if settings.smtp_username:
                if settings.smtp_password is None:
                    raise RuntimeError("SMTP_PASSWORD is required when SMTP_USERNAME is set")
                client.login(settings.smtp_username, settings.smtp_password.get_secret_value())
            client.send_message(message)


def send_password_reset(destination: str, reset_link: str, user_id: int) -> None:
    if settings.password_reset_email_sender == "smtp":
        sender: PasswordResetSender = SMTPPasswordResetSender()
    else:
        sender = ConsolePasswordResetSender(user_id)
    sender.send(destination, reset_link)
