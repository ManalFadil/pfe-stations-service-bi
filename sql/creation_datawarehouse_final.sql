/* ============================================================
   SCRIPT DE CREATION DU DATA WAREHOUSE
   Projet PFE : Analyse des performances des stations-service
   */


USE DW_StationsService;
GO

/* ============================================================
   1. TABLES DE DIMENSIONS
   ============================================================ */

-- Dimension Station
CREATE TABLE DIM_STATION (
    id_station          VARCHAR(7)      NOT NULL PRIMARY KEY,
    code_station         VARCHAR(20)     NULL,
    station_designation  VARCHAR(100)    NULL,
    code_societe          VARCHAR(20)     NULL,
    societe_designation  VARCHAR(100)    NULL,
    centre_analytique    VARCHAR(50)     NULL
);
GO

CREATE TABLE DIM_CLIENT (
    code_client_erp      VARCHAR(10)     NOT NULL PRIMARY KEY,
    client_designation   VARCHAR(150)    NULL
);
GO

CREATE TABLE DIM_PRODUIT (
    code_article          VARCHAR(25)     NOT NULL PRIMARY KEY,
    designation           VARCHAR(100)    NULL,
    categorie             VARCHAR(50)     NULL   
);
GO

CREATE TABLE DIM_FOURNISSEUR (
    compte                 VARCHAR(20)     NOT NULL PRIMARY KEY,
    ste                    VARCHAR(100)    NULL
);
GO

CREATE TABLE DIM_TEMPS (
    date_jour              DATE            NOT NULL PRIMARY KEY,
    jour                   INT             NULL,
    mois                   INT             NULL,
    nom_mois               VARCHAR(20)     NULL,
    trimestre              INT             NULL,
    annee                  INT             NULL,
    jour_semaine           VARCHAR(15)     NULL
);
GO


CREATE TABLE FAIT_VENTES (
    id_vente               INT IDENTITY(1,1) PRIMARY KEY,   
    num_facture             INT             NULL,
    id_station               VARCHAR(7)      NOT NULL,
    code_client_erp          VARCHAR(10)     NULL,
    code_article              VARCHAR(25)     NOT NULL,
    date_facture              DATE            NOT NULL,
    prix                       DECIMAL(10,2)   NULL,
    qte_livrees                DECIMAL(10,2)   NULL,
    montant                     AS (prix * qte_livrees) PERSISTED,  
    date_traitement            DATETIME        NULL,
    date_validation             DATETIME        NULL,
    validateur                   VARCHAR(25)     NULL,

    CONSTRAINT FK_VENTES_STATION FOREIGN KEY (id_station) REFERENCES DIM_STATION(id_station),
    CONSTRAINT FK_VENTES_CLIENT  FOREIGN KEY (code_client_erp) REFERENCES DIM_CLIENT(code_client_erp),
    CONSTRAINT FK_VENTES_PRODUIT FOREIGN KEY (code_article) REFERENCES DIM_PRODUIT(code_article),
    CONSTRAINT FK_VENTES_TEMPS   FOREIGN KEY (date_facture) REFERENCES DIM_TEMPS(date_jour)
);
GO

CREATE TABLE FAIT_ACHATS (
    id_achat                INT IDENTITY(1,1) PRIMARY KEY,
    numBL                     VARCHAR(20)     NULL,
    numFacture                 VARCHAR(20)     NULL,
    id_station                  VARCHAR(7)      NOT NULL,
    code_article                 VARCHAR(25)     NOT NULL,
    compte                        VARCHAR(20)     NULL,
    dateAchat                     DATE            NOT NULL,
    quantite                       DECIMAL(10,2)   NULL,
    cout                            DECIMAL(10,2)   NULL,
    document                         VARCHAR(50)     NULL,
    camion                            VARCHAR(30)     NULL,
    chauffeur                         VARCHAR(50)     NULL,
    date_validation                    DATETIME        NULL,
    validateur                          VARCHAR(25)     NULL,

    CONSTRAINT FK_ACHATS_STATION FOREIGN KEY (id_station) REFERENCES DIM_STATION(id_station),
    CONSTRAINT FK_ACHATS_PRODUIT FOREIGN KEY (code_article) REFERENCES DIM_PRODUIT(code_article),
    CONSTRAINT FK_ACHATS_FOURNISSEUR FOREIGN KEY (compte) REFERENCES DIM_FOURNISSEUR(compte),
    CONSTRAINT FK_ACHATS_TEMPS FOREIGN KEY (dateAchat) REFERENCES DIM_TEMPS(date_jour)
);
GO

CREATE TABLE FAIT_STOCK (
    id_stock                INT IDENTITY(1,1) PRIMARY KEY,
    id_station                 VARCHAR(7)      NOT NULL,
    cuve                         VARCHAR(10)     NULL,
    code_article                  VARCHAR(25)     NOT NULL,
    date_jougage                   DATE            NOT NULL,
    stock                            DECIMAL(10,2)   NULL,
    stock_calcule                     DECIMAL(10,2)   NULL,
    variation                          DECIMAL(10,2)   NULL,
    date_validation                     DATETIME        NULL,
    validateur                           VARCHAR(25)     NULL,

    CONSTRAINT FK_STOCK_STATION FOREIGN KEY (id_station) REFERENCES DIM_STATION(id_station),
    CONSTRAINT FK_STOCK_PRODUIT FOREIGN KEY (code_article) REFERENCES DIM_PRODUIT(code_article),
    CONSTRAINT FK_STOCK_TEMPS   FOREIGN KEY (date_jougage) REFERENCES DIM_TEMPS(date_jour)
);
GO


