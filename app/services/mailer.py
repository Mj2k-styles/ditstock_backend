"""
Envoi d'e-mails (réinitialisation du mot de passe, alertes de stock).

Configuration par variables d'environnement : MAIL_SERVER, MAIL_PORT,
MAIL_USERNAME, MAIL_PASSWORD, MAIL_USE_TLS, MAIL_FROM.
Sans MAIL_SERVER, l'e-mail n'est pas envoyé : il est seulement journalisé.
En test, les messages sont conservés dans app.extensions["outbox"].
"""
import logging
import smtplib
import threading
from email.message import EmailMessage

from flask import current_app

logger = logging.getLogger(__name__)


def _send_smtp(config, message):
    try:
        with smtplib.SMTP(config["server"], config["port"], timeout=10) as smtp:
            if config["use_tls"]:
                smtp.starttls()
            if config["username"]:
                smtp.login(config["username"], config["password"])
            smtp.send_message(message)
        logger.info("E-mail envoyé", extra={"to": message["To"], "subject": message["Subject"]})
    except (OSError, smtplib.SMTPException):
        logger.exception("Échec de l'envoi d'un e-mail à %s", message["To"])


def send_mail(to, subject, body):
    """Envoie un e-mail texte en arrière-plan (ne bloque jamais la requête)."""
    app = current_app._get_current_object()
    recipients = [to] if isinstance(to, str) else list(to)
    if not recipients:
        return

    message = EmailMessage()
    message["From"] = app.config["MAIL_FROM"]
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject
    message.set_content(body)

    if app.config.get("TESTING"):
        app.extensions.setdefault("outbox", []).append(message)
        return

    if not app.config.get("MAIL_SERVER"):
        logger.info("E-mail non envoyé (MAIL_SERVER absent) : %s -> %s", subject, message["To"])
        return

    config = {
        "server": app.config["MAIL_SERVER"],
        "port": app.config["MAIL_PORT"],
        "use_tls": app.config["MAIL_USE_TLS"],
        "username": app.config.get("MAIL_USERNAME"),
        "password": app.config.get("MAIL_PASSWORD"),
    }
    threading.Thread(target=_send_smtp, args=(config, message), daemon=True).start()
