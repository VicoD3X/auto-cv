# Auto-CV - Perimetre V1

## Objectif

La V1 doit deja reduire la friction reelle des candidatures, sans attendre un moteur IA complet.

Elle doit permettre de partir d'un dossier local unique, d'une offre ou mission, puis de produire une candidature propre avec un minimum d'allers-retours manuels.

## Source Documentaire Unique

La V1 part exclusivement de ce dossier local :

```text
%USERPROFILE%\Desktop\GENERIQUE PRO
```

Fichiers attendus :

```text
CV_Victor_Aubry_Data_Scientist_pdf.pdf
Lettre_motivation_Victor_Aubry.docx
```

Regles :

- le CV generique est utilise tel quel ;
- pas de modification IA du CV en V1 ;
- la lettre generique sert de base editable ;
- les resultats generes restent hors Git ;
- les resultats de modification, tri et preparation documentaire sont places dans :

```text
%USERPROFILE%\Desktop\GENERIQUE PRO\Auto-CV\Result
```

## Candidature Salariee

Workflow principal :

```text
Offre d'emploi
  -> fiche candidature
  -> CV generique
  -> lettre generique copiee et renommee
  -> ajustement manuel si necessaire
  -> validation humaine
  -> export
  -> statut
```

La V1 sans LLM doit etre fiable avant tout :

- copier les documents sources sans les modifier ;
- renommer les sorties proprement ;
- garder la lettre generique editable ;
- laisser l'ajustement fin a la validation humaine ;
- ne jamais lancer de modele local par defaut.

Le CV est copie et renomme proprement dans le dossier `Result`, mais son contenu n'est pas modifie par IA.

La lettre generique copiee est sauvegardee dans `Result` avec un nom explicite.

Le mail de candidature est prepare par un template deterministe :

- objet du mail ;
- corps du mail ;
- rappel des pieces jointes ;
- ton professionnel court.

Les brouillons de mail sont sauvegardes comme previsualisations `.txt` dans `Result`.

## Projets GitHub

Auto-CV doit synchroniser les projets GitHub pour garder un contexte projet local exploitable.

Objectif :

- recuperer les projets publics pertinents ;
- extraire un resume local exploitable ;
- identifier les technos et themes ;
- permettre a Victor de retrouver rapidement les projets pertinents a citer dans une lettre.

La synchronisation GitHub sert de contexte. Elle ne remplace pas la validation humaine.

## Face Freelance

La V1 prefigure aussi une petite gestion freelance.

Elle doit permettre de suivre une opportunite de mission avec :

- client ou plateforme ;
- besoin exprime ;
- type de mission ;
- budget ou TJM si connu ;
- statut ;
- message/proposition associe ;
- export ou note finale.

La sortie freelance V1 reste une base documentaire legere :

```text
Besoin client
  -> documents generiques copies
  -> notes de mission
  -> mail deterministe si necessaire
```

Cette face reste plus legere que la partie salariat.

Le message freelance et son objet peuvent etre prepares par template local.

## Renommage Intelligent

La V1 doit renommer les documents generes ou tries avec des noms explicites.

Format de base :

```text
TypeDocument_Cible_PosteOuMission_Date.ext
```

Exemples :

```text
CV_Airbus_Data_Scientist_2026_06_09.pdf
Lettre_Motivation_Airbus_Data_Scientist_2026_06_09.docx
Proposition_Freelance_Client_Dashboard_2026_06_09.docx
Mail_Airbus_Data_Scientist_2026_06_09.txt
```

Le renommage doit rester lisible, stable et compatible Windows.

## Conversion de Formats Documentaires

La V1 doit aussi integrer un module de conversion documentaire.

Formats concernes :

- DOCX ;
- PDF ;
- Excel XLSX.

Conversions prioritaires :

```text
DOCX -> PDF
PDF  -> DOCX
XLSX -> PDF
PDF  -> XLSX
```

Regles :

- DOCX -> PDF doit servir aux exports propres de CV, lettres et propositions ;
- PDF -> DOCX doit etre vu comme une reconstruction editable, pas comme une garantie de mise en page parfaite ;
- XLSX -> PDF doit permettre de produire un export lisible ;
- PDF -> XLSX doit etre limite aux PDF contenant des tableaux exploitables ;
- les conversions doivent rester locales ;
- aucun document personnel converti ne doit etre committe dans le repo public.

Cas d'usage V1 :

- convertir une lettre DOCX en PDF final ;
- reconstruire un PDF en DOCX editable quand necessaire ;
- exporter un fichier Excel de suivi en PDF ;
- extraire un tableau PDF vers un fichier Excel quand le document s'y prete.

## Hors Scope V1

La V1 ne fait pas encore :

- modification IA du CV ;
- adaptation IA automatique des lettres ;
- generation IA des propositions freelance ;
- envoi Gmail automatique ;
- scoring avance des offres ;
- app iPad autonome ;
- gestion CRM freelance complete ;
- moteur IA publie dans le repo public.
- preservation parfaite de mise en page PDF complexe ;
- extraction fiable de tableaux PDF non structures.
