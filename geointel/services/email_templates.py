from geointel.i18n import t

_WRAPPER = """
<div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 24px;
            border: 1px solid #e2e8f0; border-radius: 8px;">
  <div style="color: #1a237e; font-weight: 700; font-size: 18px; margin-bottom: 16px;">
    GeoIntel
  </div>
  <p style="color: #0f172a; font-size: 14px; line-height: 1.6;">{body}</p>
</div>
"""


def _render(subject_key: str, body_key: str, lang: str, **kwargs: str) -> tuple[str, str]:
    subject = t(subject_key, lang, **kwargs)
    body = t(body_key, lang, **kwargs)
    return subject, _WRAPPER.format(body=body)


def render_welcome(name: str, plan: str, lang: str = "ru") -> tuple[str, str]:
    return _render("email.welcome.subject", "email.welcome.body", lang, name=name, plan=plan)


def render_invoice(
    name: str, invoice_id: int, plan: str, amount_tiyin: int, status: str, lang: str = "ru"
) -> tuple[str, str]:
    amount_som = f"{amount_tiyin / 100:.2f}"
    return _render(
        "email.invoice.subject",
        "email.invoice.body",
        lang,
        name=name,
        invoice_id=str(invoice_id),
        plan=plan,
        amount=amount_som,
        status=status,
    )


def render_payment_confirmed(
    name: str, invoice_id: int, plan: str, lang: str = "ru"
) -> tuple[str, str]:
    return _render(
        "email.payment_confirmed.subject",
        "email.payment_confirmed.body",
        lang,
        name=name,
        invoice_id=str(invoice_id),
        plan=plan,
    )


def render_threshold_breach(
    subject_name: str, metric: str, severity: str, decade: str, lang: str = "ru"
) -> tuple[str, str]:
    return _render(
        "email.threshold.subject",
        "email.threshold.body",
        lang,
        subject_name=subject_name,
        metric=metric,
        severity=severity,
        decade=decade,
    )


def render_decade_summary(
    name: str, decade: str, items: list[str], lang: str = "ru"
) -> tuple[str, str]:
    items_str = "; ".join(items) if items else "-"
    return _render(
        "email.decade_summary.subject",
        "email.decade_summary.body",
        lang,
        name=name,
        decade=decade,
        items=items_str,
    )
