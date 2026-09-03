"""
================================================================
 Pipeline d'extraction incrementale MySQL -> SQL Server
 Projet PFE : Analyse des performances des stations-service
================================================================

"""

import argparse
import json
import logging
import os
from datetime import datetime, date

import pymysql
import pyodbc

# ----------------------------------------------------------------
# CONFIGURATION - a adapter a votre environnement
# ----------------------------------------------------------------

MYSQL_CONFIG = {
    "host": "localhost",
    "password": "",
    "database": "db",
    "charset": "utf8mb4",
}

SQLSERVER_CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=MANAL\\SQLEXPRESS;"
    "DATABASE=DW_StationsService;"
    "Trusted_Connection=yes;"
)

FICHIER_ETAT = "etat_derniere_extraction.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("extraction_incrementale.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


# ----------------------------------------------------------------
# GESTION DE L'ETAT (derniere date extraite, pour l'incrementalite)
# ----------------------------------------------------------------

def lire_derniere_extraction() -> str:
    """Lit la date de la derniere extraction reussie. Par defaut,
    remonte 7 jours en arriere si aucun etat n'existe encore."""
    if os.path.exists(FICHIER_ETAT):
        with open(FICHIER_ETAT, "r", encoding="utf-8") as f:
            etat = json.load(f)
            return etat.get("derniere_date", "2026-07-27")
    return "2026-07-27"


def sauvegarder_extraction(date_extraction: str) -> None:
    with open(FICHIER_ETAT, "w", encoding="utf-8") as f:
        json.dump({"derniere_date": date_extraction, "execute_le": str(datetime.now())}, f)


# ----------------------------------------------------------------
# NETTOYAGE (reprend les regles etablies au Chapitre 5, tableau 5.1)
# ----------------------------------------------------------------

def nettoyer_texte(valeur):
    """Retire les guillemets et espaces parasites (cf. anomalie
    'Caracteres parasites' documentee au chapitre 5)."""
    if valeur is None:
        return None
    return str(valeur).replace('"', "").strip()


def nettoyer_decimal(valeur):
    """Convertit un nombre eventuellement au format virgule
    decimale (cf. anomalie 'Separateur decimal')."""
    if valeur is None:
        return None
    try:
        return float(str(valeur).replace(",", "."))
    except ValueError:
        return None


# ----------------------------------------------------------------
# EXTRACTION DEPUIS MYSQL
# ----------------------------------------------------------------

def extraire_nouvelles_ventes(cursor_mysql, depuis_date: str):
    """Recupere les lignes de ventes validees depuis la derniere
    extraction (chargement incremental base sur date_traitement)."""
    requete = """
        SELECT id_station, num_facture, code_client_facture, code_article,
               date_facture, prix, qte_livrees, date_traitement
        FROM ventes
        WHERE date_traitement > %s
          AND date_traitement != '0000-00-00 00:00:00'
    """
    cursor_mysql.execute(requete, (depuis_date,))
    return cursor_mysql.fetchall()


def extraire_nouveaux_achats(cursor_mysql, depuis_date: str):
    """Chargement incremental base sur dateAchat (et non date_validation,
    ce champ n'etant pas systematiquement renseigne pour les achats)."""
    requete = """
        SELECT id_station, numBL, numFacture, code_article, compte,
               dateAchat, quantite, cout, date_validation
        FROM achats
        WHERE dateAchat > %s
    """
    cursor_mysql.execute(requete, (depuis_date,))
    return cursor_mysql.fetchall()
 
 
def extraire_nouveaux_stocks(cursor_mysql, depuis_date: str):
    """Chargement incremental base sur date_jougage (et non date_validation,
    ce champ n'etant pas systematiquement renseigne pour les releves de stock)."""
    requete = """
        SELECT id_station, cuve, code_article, date_jougage, stock, date_validation
        FROM stock
        WHERE date_jougage > %s
    """
    cursor_mysql.execute(requete, (depuis_date,))
    return cursor_mysql.fetchall()

# ----------------------------------------------------------------
# CHARGEMENT VERS SQL SERVER (via table de transit, cf. figure 5.1)
# ----------------------------------------------------------------

def charger_ventes(cursor_sql, lignes):
    inserees = 0

    for ligne in lignes:
        id_station = nettoyer_texte(ligne[0])
        code_client = nettoyer_texte(ligne[2])
        code_article = nettoyer_texte(ligne[3])
        prix = nettoyer_decimal(ligne[5])
        qte = nettoyer_decimal(ligne[6])

        # ==========================================================
        # 1. VERIFICATION STATION
        # ==========================================================
        cursor_sql.execute(
            """
            SELECT COUNT(*)
            FROM DIM_STATION
            WHERE id_station = ?
            """,
            id_station
        )

        if cursor_sql.fetchone()[0] == 0:
            log.warning(
                "Station inconnue : %s",
                id_station
            )
            continue

        # ==========================================================
        # 2. INSERTION CLIENT S'IL N'EXISTE PAS
        # ==========================================================
        cursor_sql.execute(
            """
            SELECT COUNT(*)
            FROM DIM_CLIENT
            WHERE id_station = ?
              AND code_client_erp = ?
            """,
            id_station,
            code_client
        )

        if cursor_sql.fetchone()[0] == 0:

            cursor_sql.execute(
                """
                INSERT INTO DIM_CLIENT
                    (id_station, code_client_erp, client_designation)
                VALUES (?, ?, ?)
                """,
                id_station,
                code_client,
                None
            )

            log.info(
                "Nouveau client ajoute : station=%s, client=%s",
                id_station,
                code_client
            )

        # ==========================================================
        # 3. INSERTION PRODUIT S'IL N'EXISTE PAS
        # ==========================================================
        cursor_sql.execute(
            """
            SELECT COUNT(*)
            FROM DIM_PRODUIT
            WHERE code_article = ?
            """,
            code_article
        )

        if cursor_sql.fetchone()[0] == 0:

            cursor_sql.execute(
                """
                INSERT INTO DIM_PRODUIT
                    (code_article, designation)
                VALUES (?, ?)
                """,
                code_article,
                None
            )

            log.info(
                "Nouveau produit ajoute : %s",
                code_article
            )

        # ==========================================================
        # 4. INSERTION DE LA VENTE
        # ==========================================================
        cursor_sql.execute(
            """
            INSERT INTO FAIT_VENTES
                (
                    num_facture,
                    id_station,
                    code_client_erp,
                    code_article,
                    date_facture,
                    prix,
                    qte_livrees
                )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ligne[1],
            id_station,
            code_client,
            code_article,
            ligne[4],
            prix,
            qte
        )

        inserees += 1

    return inserees

def charger_achats(cursor_sql, lignes):
    inserees = 0
    for ligne in lignes:
        id_station = nettoyer_texte(ligne[0])
        code_article = nettoyer_texte(ligne[3])
        compte = nettoyer_texte(ligne[4])
        quantite = nettoyer_decimal(ligne[6])
        cout = nettoyer_decimal(ligne[7])

        cursor_sql.execute(
            "SELECT COUNT(*) FROM DIM_FOURNISSEUR WHERE compte = ?", compte
        )
        if cursor_sql.fetchone()[0] == 0:
            continue  # mouvement interne sans fournisseur (cf. section 5.3)

        cursor_sql.execute(
            """
            INSERT INTO FAIT_ACHATS
                (numBL, numFacture, id_station, code_article, compte,
                 dateAchat, quantite, cout)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            nettoyer_texte(ligne[1]), nettoyer_texte(ligne[2]), id_station,
            code_article, compte, ligne[5], quantite, cout,
        )
        inserees += 1
    return inserees


def charger_stocks(cursor_sql, lignes):
    inserees = 0
    for ligne in lignes:
        id_station = nettoyer_texte(ligne[0])
        stock = nettoyer_decimal(ligne[4])

        # Controle de plausibilite physique (cf. anomalie "valeurs
        # de jaugeage aberrantes", seuil de 30 000 L etabli chapitre 5)
        if stock is not None and stock > 30000:
            log.warning("Valeur de stock aberrante ignoree : %s L (station %s)",
                        stock, id_station)
            continue

        cursor_sql.execute(
            """
            INSERT INTO FAIT_STOCK (id_station, cuve, code_article, date_jougage, stock)
            VALUES (?, ?, ?, ?, ?)
            """,
            id_station, nettoyer_texte(ligne[1]), nettoyer_texte(ligne[2]), ligne[3], stock,
        )
        inserees += 1
    return inserees


# ----------------------------------------------------------------
# ORCHESTRATION
# ----------------------------------------------------------------

def executer_pipeline(depuis_date: str):
    log.info("=" * 60)
    log.info("Debut de l'extraction incrementale (depuis %s)", depuis_date)

    connexion_mysql = pymysql.connect(**MYSQL_CONFIG)
    connexion_sql = pyodbc.connect(SQLSERVER_CONN_STR)
    cursor_mysql = connexion_mysql.cursor()
    cursor_sql = connexion_sql.cursor()

    try:
        ventes = extraire_nouvelles_ventes(cursor_mysql, depuis_date)
        log.info("%d nouvelles lignes de ventes recuperees", len(ventes))
        nb_ventes = charger_ventes(cursor_sql, ventes)

        achats = extraire_nouveaux_achats(cursor_mysql, depuis_date)
        log.info("%d nouvelles lignes d'achats recuperees", len(achats))
        nb_achats = charger_achats(cursor_sql, achats)

        stocks = extraire_nouveaux_stocks(cursor_mysql, depuis_date)
        log.info("%d nouveaux releves de stock recuperes", len(stocks))
        nb_stocks = charger_stocks(cursor_sql, stocks)

        connexion_sql.commit()
        sauvegarder_extraction(str(datetime.now()))

        log.info("Chargement termine : %d ventes, %d achats, %d releves de stock inseres",
                  nb_ventes, nb_achats, nb_stocks)

    except Exception as erreur:
        connexion_sql.rollback()
        log.error("Erreur pendant le pipeline, annulation : %s", erreur)
        raise
    finally:
        cursor_mysql.close()
        cursor_sql.close()
        connexion_mysql.close()
        connexion_sql.close()
        log.info("Connexions fermees.")
        log.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extraction incrementale MySQL -> SQL Server")
    parser.add_argument(
        "--date-depart", default=None,
        help="Force une date de depart (format AAAA-MM-JJ) au lieu de reprendre "
             "automatiquement depuis la derniere execution.",
    )
    args = parser.parse_args()

    date_depart = args.date_depart or lire_derniere_extraction()
    executer_pipeline(date_depart)
