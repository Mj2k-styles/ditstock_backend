import click
from flask.cli import with_appcontext

from app import db
from app.constants import ROLE_ADMIN
from app.models.user import User
from app.schemas.user_schema import validate_password
from marshmallow import ValidationError


@click.command("create-admin")
@click.option("--email", prompt=True, help="E-mail de l'administrateur")
@click.option("--full-name", prompt="Nom complet", help="Nom complet")
@click.password_option(help="Mot de passe (8 caractères minimum)")
@with_appcontext
def create_admin(email, full_name, password):
    """Crée le premier compte administrateur."""
    email = email.strip().lower()

    try:
        validate_password(password)
    except ValidationError as err:
        raise click.ClickException(err.messages[0])

    if User.query.filter_by(email=email).first():
        raise click.ClickException("Cet e-mail existe déjà")

    admin = User(email=email, full_name=full_name, role=ROLE_ADMIN)
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()

    click.echo(f"Administrateur créé : {email}")
