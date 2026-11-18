"""Migrations, données de démonstration, e-mails, logs JSON et métriques."""
import json
import logging
import smtplib

import pytest
from flask_migrate import upgrade
from sqlalchemy import inspect

from app import create_app, db
from app.logging_config import JsonFormatter, configure_logging
from app.models.product import Product
from app.models.stock_movement import StockMovement
from app.models.user import User
from app.services import mailer


def test_migrations_creent_tout_le_schema(tmp_path):
    """flask db upgrade sur une base vide aboutit au même schéma que les modèles."""
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'migrations.db'}",
    })
    with app.app_context():
        upgrade()
        inspector = inspect(db.engine)
        tables = set(inspector.get_table_names())
        assert {"products", "suppliers", "stock_movements", "audit_logs", "users"} <= tables
        product_columns = {c["name"] for c in inspector.get_columns("products")}
        assert {"supplier_id", "unit", "sale_price", "image_url"} <= product_columns
        assert "contact" in {c["name"] for c in inspector.get_columns("suppliers")}
        assert "supplier_id" in {c["name"] for c in inspector.get_columns("stock_movements")}
        db.engine.dispose()

    # alembic.ini (fileConfig) désactive les loggers existants : on les réactive
    for logger in logging.Logger.manager.loggerDict.values():
        if isinstance(logger, logging.Logger):
            logger.disabled = False


def test_seed_demo_refuse_sans_autorisation(app, monkeypatch):
    monkeypatch.delenv("ALLOW_DEMO_SEED", raising=False)
    result = app.test_cli_runner().invoke(args=["seed-demo"])
    assert result.exit_code != 0
    assert "ALLOW_DEMO_SEED" in result.output


def test_seed_demo_idempotent(app, monkeypatch):
    monkeypatch.setenv("ALLOW_DEMO_SEED", "1")
    runner = app.test_cli_runner()
    first = runner.invoke(args=["seed-demo", "--password", "Demo12345!"])
    assert first.exit_code == 0, first.output
    assert User.query.count() == 3
    assert Product.query.count() == 6
    movements = StockMovement.query.count()
    assert movements > 0

    second = runner.invoke(args=["seed-demo", "--password", "Demo12345!"])
    assert second.exit_code == 0
    assert Product.query.count() == 6
    assert StockMovement.query.count() == movements


def test_mail_journalise_sans_serveur(app, caplog):
    app.config.update(TESTING=False, MAIL_SERVER="")
    with caplog.at_level(logging.INFO):
        mailer.send_mail("a@test.sn", "Sujet", "Corps")
    assert "MAIL_SERVER absent" in caplog.text


def test_mail_envoye_par_smtp(app, monkeypatch):
    sent = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            sent.append(("connect", host, port))

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def starttls(self):
            sent.append(("tls",))

        def login(self, user, password):
            sent.append(("login", user))

        def send_message(self, message):
            sent.append(("send", message["To"]))

    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    config = {"server": "smtp.test", "port": 587, "use_tls": True,
              "username": "u", "password": "p"}
    message = mailer.EmailMessage()
    message["To"] = "a@test.sn"
    mailer._send_smtp(config, message)
    assert sent == [("connect", "smtp.test", 587), ("tls",), ("login", "u"), ("send", "a@test.sn")]


def test_mail_echec_smtp_journalise(monkeypatch, caplog):
    def refuse(*args, **kwargs):
        raise OSError("connexion refusée")

    monkeypatch.setattr(smtplib, "SMTP", refuse)
    message = mailer.EmailMessage()
    message["To"] = "a@test.sn"
    mailer._send_smtp({"server": "x", "port": 1, "use_tls": False,
                       "username": "", "password": ""}, message)
    assert "Échec de l'envoi" in caplog.text


def test_mail_en_arriere_plan(app, monkeypatch):
    app.config.update(TESTING=False, MAIL_SERVER="smtp.test")
    started = []

    class FakeThread:
        def __init__(self, target, args, daemon):
            started.append(args[1]["Subject"])

        def start(self):
            pass

    monkeypatch.setattr(mailer.threading, "Thread", FakeThread)
    mailer.send_mail(["a@test.sn"], "Alerte", "Corps")
    mailer.send_mail([], "Personne", "Corps")
    assert started == ["Alerte"]


def test_logs_au_format_json(capsys):
    configure_logging("json", "INFO")
    try:
        logging.getLogger("ditstock.test").info("Bonjour", extra={"user_id": 7})
        line = capsys.readouterr().out.strip().splitlines()[-1]
        entry = json.loads(line)
        assert entry["message"] == "Bonjour"
        assert entry["level"] == "INFO"
        assert entry["user_id"] == 7
    finally:
        logging.getLogger().handlers.clear()


def test_format_texte_et_exceptions():
    configure_logging("text", "WARNING")
    try:
        assert not isinstance(logging.getLogger().handlers[0].formatter, JsonFormatter)
    finally:
        logging.getLogger().handlers.clear()
    try:
        raise ValueError("boum")
    except ValueError:
        record = logging.makeLogRecord({"msg": "erreur", "exc_info": __import__("sys").exc_info()})
    assert "boum" in json.loads(JsonFormatter().format(record))["exception"]


def test_endpoint_metrics(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert b"flask_http_request" in response.data


@pytest.mark.parametrize("value, expected", [("1", True), ("oui", True), ("false", False)])
def test_options_booleennes(monkeypatch, value, expected):
    from app import _env_bool
    monkeypatch.setenv("MAIL_USE_TLS", value)
    assert _env_bool("MAIL_USE_TLS") is expected


def test_connexions_verifiees_avant_usage(app):
    """Après un redémarrage de PostgreSQL, les connexions mortes du pool sont remplacées."""
    assert app.config["SQLALCHEMY_ENGINE_OPTIONS"]["pool_pre_ping"] is True
