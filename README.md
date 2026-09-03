# Analyse des performances des stations-service — BI & Big Data

Projet de fin d'études (Master) portant sur la conception d'un système décisionnel
pour le pilotage de la performance d'un réseau de 25 stations-service, à partir de
données réelles issues d'un système d'information opérationnel MySQL.

## Contexte

Les données opérationnelles (ventes, achats, stocks) sont dispersées dans une base
MySQL sans consolidation ni restitution décisionnelle. Ce projet vise à construire un
entrepôt de données et des tableaux de bord permettant une aide à la décision fiable,
tout en menant une analyse critique de la pertinence d'une architecture Big Data au
regard du volume réel des données traitées.

## Architecture

```
MySQL (source) → ETL (staging + contrôles qualité) → SQL Server (DW_StationsService) → Power BI
```

Le modèle de données suit un schéma en constellation : trois tables de faits
(`FAIT_VENTES`, `FAIT_ACHATS`, `FAIT_STOCK`) organisées autour de cinq dimensions
partagées (`DIM_STATION`, `DIM_CLIENT`, `DIM_PRODUIT`, `DIM_FOURNISSEUR`, `DIM_TEMPS`).

## Contenu du dépôt

| Dossier | Contenu |
|---|---|
| `sql/` | Script de création complet de l'entrepôt de données SQL Server (dimensions, faits, table analytique de détection d'anomalies de stock) |
| `etl/` | Script Python d'extraction incrémentale automatisant le chargement quotidien des nouvelles données depuis MySQL vers SQL Server, avec reprise des règles de fiabilisation des données établies au cours du projet |
| `bigdata/` | Script PySpark constituant une preuve de concept de traitement distribué, comparé expérimentalement à l'approche SQL Server retenue |

## Points clés du projet

- **Modélisation dimensionnelle** : schéma en constellation, avec gestion d'une clé
  composite pour la dimension client (un identifiant client n'étant unique qu'au
  sein d'une station donnée).
- **Qualité des données** : audit systématique des données sources via des tables
  de transit (staging), ayant permis d'identifier et de corriger plusieurs
  catégories d'anomalies (encodages, formats, valeurs aberrantes, incohérences
  référentielles).
- **Détection d'anomalies de stock** : comparaison entre stock théorique (calculé
  à partir des mouvements d'achats et de ventes) et stock physiquement jaugé,
  selon une méthode validée par le métier.
- **Positionnement Big Data** : analyse argumentée, appuyée par une comparaison
  expérimentale des temps d'exécution (SQL Server vs PySpark), concluant que le
  volume actuel des données ne justifie pas une architecture de traitement
  distribué.
- **Sécurité des accès** : mécanisme de sécurité au niveau des lignes (Row-Level
  Security) dans Power BI, différenciant l'accès aux données selon le profil de
  l'utilisateur (direction vs responsable de station).
- **Automatisation** : pipeline d'extraction incrémentale, conçu pour une exécution
  quotidienne locale (Planificateur de tâches Windows), les bases de données
  n'étant pas exposées publiquement pour des raisons de confidentialité.

## Technologies utilisées

MySQL · SQL Server · SSIS · Power BI (DAX) · Python · PySpark · Git

## Auteur

Projet réalisé dans le cadre d'un Master en Ingénierie Big Data et Cloud Computing-Manal Fadil.

## Avertissement

Les scripts fournis dans ce dépôt utilisent des identifiants de connexion génériques
(placeholders) à adapter à votre propre environnement. Les données réelles de
l'entreprise ne sont pas incluses dans ce dépôt pour des raisons de confidentialité.

