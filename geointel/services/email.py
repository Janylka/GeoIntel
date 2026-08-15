import logging
import os
from typing import Any

import resend

resend.api_key = os.getenv("RESEND_API_KEY", "re_dummy")


def send_email(
    to_email: str, subject: str, html_body: str, attachment_path: str | None = None
) -> bool:
    try:
        data: dict[str, Any] = {
            "from": "GeoIntel <noreply@geointel.kg>",
            "to": [to_email],
            "subject": subject,
            "html": html_body,
        }

        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, "rb") as f:
                file_content = f.read()
                data["attachments"] = [
                    {"filename": os.path.basename(attachment_path), "content": list(file_content)}
                ]

        r = resend.Emails.send(data)  # type: ignore[arg-type]
        logging.info(f"Sent email to {to_email}: {r}")
        return True
    except Exception as e:
        logging.error(f"Failed to send email to {to_email}: {e}")
        return False
