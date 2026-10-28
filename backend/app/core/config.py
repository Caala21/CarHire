from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CarHire API"
    database_url: str = "postgresql+psycopg://carhire:carhire@localhost:5432/carhire"
    jwt_secret_key: str = "development-only-change-this-secret-before-deploying"
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    cors_origins: str = "http://localhost:5173"
    production: bool = False
    verification_email_sender: Literal["console", "smtp"] = "console"
    verification_sms_sender: Literal["console", "africastalking"] = "console"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_from_email: str | None = None
    smtp_starttls: bool = True
    africastalking_username: str | None = None
    africastalking_api_key: SecretStr | None = None
    africastalking_sender_id: str | None = None
    africastalking_sandbox: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def validate_verification_senders(self) -> "Settings":
        if self.production and self.jwt_secret_key == "development-only-change-this-secret-before-deploying":
            raise ValueError("Production requires a non-development JWT secret")

        if self.production and (
            self.verification_email_sender == "console"
            or self.verification_sms_sender == "console"
        ):
            raise ValueError("Production requires non-console verification senders")

        if self.verification_email_sender == "smtp" and not all(
            (self.smtp_host, self.smtp_from_email)
        ):
            raise ValueError("SMTP verification requires SMTP_HOST and SMTP_FROM_EMAIL")
        if self.verification_email_sender == "smtp" and self.smtp_username and not self.smtp_password:
            raise ValueError("SMTP_USERNAME requires SMTP_PASSWORD")

        if self.verification_sms_sender == "africastalking" and not all(
            (self.africastalking_username, self.africastalking_api_key)
        ):
            raise ValueError(
                "Africa's Talking verification requires AFRICASTALKING_USERNAME "
                "and AFRICASTALKING_API_KEY"
            )

        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()