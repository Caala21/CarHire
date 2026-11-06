from decimal import Decimal
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CarHire API"
    database_url: str = "postgresql+psycopg://carhire:carhire@localhost:5432/carhire"
    jwt_secret_key: str = "development-only-change-this-secret-before-deploying"
    google_client_id: str | None = None
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
    anthropic_api_key: SecretStr | None = None
    anthropic_model: str = "claude-3-5-haiku-latest"
    mpesa_env: Literal["sandbox", "production"] = "sandbox"
    mpesa_consumer_key: SecretStr | None = None
    mpesa_consumer_secret: SecretStr | None = None
    mpesa_shortcode: SecretStr | None = None
    mpesa_passkey: SecretStr | None = None
    mpesa_callback_base_url: SecretStr | None = None
    mpesa_callback_secret: SecretStr | None = None
    commission_percent: Decimal = Decimal("10")
    nominatim_user_agent: str = "CarHire/0.1 (https://github.com/Caala21/CarHire)"

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

        if self.production or self.mpesa_env == "production":
            mpesa_fields = (
                self.mpesa_consumer_key,
                self.mpesa_consumer_secret,
                self.mpesa_shortcode,
                self.mpesa_passkey,
                self.mpesa_callback_base_url,
                self.mpesa_callback_secret,
            )
            if not all(
                field is not None and bool(field.get_secret_value().strip())
                for field in mpesa_fields
            ):
                raise ValueError("Production requires all MPESA_* settings")

        if not Decimal("0") <= self.commission_percent <= Decimal("100"):
            raise ValueError("COMMISSION_PERCENT must be between 0 and 100")

        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()