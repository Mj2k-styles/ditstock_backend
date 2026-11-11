# Rôles de l'application (cahier des charges, section 2)
ROLE_ADMIN = "admin"
ROLE_GESTIONNAIRE = "gestionnaire"
ROLE_MAGASINIER = "magasinier"

ROLES = (ROLE_ADMIN, ROLE_GESTIONNAIRE, ROLE_MAGASINIER)


# Types de mouvements de stock (cahier des charges, table stock_movements)
MOVEMENT_ENTREE = "ENTREE"
MOVEMENT_SORTIE = "SORTIE"
MOVEMENT_TRANSFERT = "TRANSFERT"
MOVEMENT_AJUSTEMENT = "AJUSTEMENT"

MOVEMENT_TYPES = (
    MOVEMENT_ENTREE,
    MOVEMENT_SORTIE,
    MOVEMENT_TRANSFERT,
    MOVEMENT_AJUSTEMENT,
)

# Types réservés au gestionnaire (et à l'admin) : le magasinier
# n'enregistre que des entrées et des sorties.
MANAGER_ONLY_MOVEMENT_TYPES = (MOVEMENT_TRANSFERT, MOVEMENT_AJUSTEMENT)
