
from flask_restx import Namespace, Resource

# Créer un espace de noms pour la vérification de l'API
health_ns = Namespace("health", description="Vérification de l'API")


@health_ns.route("/")
class HealthCheck(Resource):
    def get(self):
        return {
            "status": "ok",
            "message": "API Gestion de Stock opérationnelle"
        }, 200
