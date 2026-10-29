
from app import create_app

# Créer l'application Flask
app = create_app()

# Lancer le serveur en mode développement
if __name__ == "__main__":
    app.run(debug=True)
