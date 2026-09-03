"""
================================================================
 Script PySpark - Preuve de concept de traitement distribue
 Projet PFE : Analyse des performances des stations-service
================================================================
"""

import argparse
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window


def build_spark_session(app_name: str = "AnalyseCA_StationsService") -> SparkSession:
    """Initialise la session Spark (mode local, adapte a une demonstration)."""
    return (
        SparkSession.builder
        .appName(app_name)
        .master("local[*]")
        .config("spark.sql.shuffle.partitions", "8")
        .getOrCreate()
    )


def charger_ventes(spark: SparkSession, chemin_csv: str):
    """Charge le fichier de ventes et force un schema explicite."""
    df = (
        spark.read
        .option("header", True)
        .option("inferSchema", False)
        .csv(chemin_csv)
    )
    df = (
        df.withColumn("prix", F.col("prix").cast("double"))
          .withColumn("qte_livrees", F.col("qte_livrees").cast("double"))
          .withColumn("date_facture", F.to_date("date_facture"))
          .withColumn("montant", F.col("prix") * F.col("qte_livrees"))
    )
    return df


def controle_qualite(df):
    """Applique les memes controles de qualite que le pipeline ETL SQL
    (cf. Chapitre 5, section 5.3) : exclusion des lignes incompletes
    ou physiquement aberrantes."""
    avant = df.count()
    df_propre = df.filter(
        F.col("prix").isNotNull()
        & F.col("qte_livrees").isNotNull()
        & (F.col("qte_livrees") > 0)
        & F.col("date_facture").isNotNull()
    )
    apres = df_propre.count()
    print(f"[Controle qualite] {avant - apres} lignes exclues sur {avant} "
          f"({(avant - apres) / avant:.2%})")
    return df_propre


def ca_par_station(df):
    """Chiffre d'affaires total et moyen par station."""
    return (
        df.groupBy("id_station", "station_designation")
          .agg(
              F.round(F.sum("montant"), 2).alias("ca_total"),
              F.round(F.avg("montant"), 2).alias("ca_moyen_ligne"),
              F.count("*").alias("nb_lignes"),
          )
          .orderBy(F.desc("ca_total"))
    )


def evolution_mensuelle(df):
    """Chiffre d'affaires agrege par mois, toutes stations confondues."""
    return (
        df.withColumn("annee", F.year("date_facture"))
          .withColumn("mois", F.month("date_facture"))
          .groupBy("annee", "mois")
          .agg(F.round(F.sum("montant"), 2).alias("ca_mensuel"))
          .orderBy("annee", "mois")
    )


def top_stations_par_produit(df, n: int = 3):
    """Classement des stations par produit (fonction fenetree),
    illustrant une operation typique de traitement distribue."""
    fenetre = Window.partitionBy("designation").orderBy(F.desc("ca_produit"))
    agg = (
        df.groupBy("designation", "station_designation")
          .agg(F.round(F.sum("montant"), 2).alias("ca_produit"))
    )
    return (
        agg.withColumn("rang", F.row_number().over(fenetre))
           .filter(F.col("rang") <= n)
           .orderBy("designation", "rang")
    )


def main():
    parser = argparse.ArgumentParser(description="Analyse CA stations-service via PySpark")
    parser.add_argument("--input", required=True, help="Chemin du fichier CSV de ventes")
    args = parser.parse_args()

    spark = build_spark_session()
    spark.sparkContext.setLogLevel("WARN")

    print("=" * 60)
    print("Chargement des donnees...")
    df = charger_ventes(spark, args.input)
    df = controle_qualite(df)
    df.cache()

    print("\n--- Chiffre d'affaires par station ---")
    ca_par_station(df).show(10, truncate=False)

    print("\n--- Evolution mensuelle du chiffre d'affaires ---")
    evolution_mensuelle(df).show(12, truncate=False)

    print("\n--- Top 3 stations par produit ---")
    top_stations_par_produit(df).show(20, truncate=False)

    print("=" * 60)
    spark.stop()


if __name__ == "__main__":
    main()
