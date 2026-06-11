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
- aucun fichier source n'est modifie directement ;
- toute modification passe par une copie de travail dans `Result` ;
- les resultats generes restent hors Git ;
- les resultats de modification, tri et preparation documentaire sont places dans :

```text
%USERPROFILE%\Desktop\GENERIQUE PRO\Auto-CV\Result
```

Chaque cible obtient ensuite son propre dossier :

```text
Result/<Cible>_<PosteOuMission>_<Date>/
```

## Atelier de Modification Documentaire

La V1 pivote vers un atelier de modification fiable sans LLM.

Workflow de modification :

```text
Document source
  -> Dupliquer et ouvrir
  -> copie de travail dans le dossier cible
  -> modification dans Word ou le lecteur PDF
  -> Finaliser ou Annuler
```

Regles :

- `Dupliquer et ouvrir` cree une copie de travail DOCX ou PDF dans le dossier cible ;
- `Finaliser` conserve la copie seulement si son contenu a change ;
- `Finaliser` place une copie inchangee en pré-suppression ;
- `Annuler` place la copie de travail en pré-suppression ;
- l'onglet `Pré-suppression` permet de restaurer ou supprimer definitivement ces copies ;
- toute entree non restauree est supprimee automatiquement apres 30 jours ;
- si Word ou le lecteur PDF verrouille le fichier, Auto-CV demande de fermer le document ;
- la source reste strictement intacte.

La zone de pré-suppression vit dans :

```text
Result/_PreSuppression
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

## Projets Publics

Auto-CV doit synchroniser les projets GitHub publics pour garder une bibliotheque de projets a citer manuellement.

Objectif :

- recuperer les projets publics pertinents ;
- extraire un resume local exploitable ;
- identifier les technos et themes ;
- permettre a Victor de retrouver rapidement les projets pertinents a citer dans une lettre ou un CV ;
- copier le nom du projet ;
- copier l'URL du projet ;
- copier un hyperlien Word ou seul le nom du projet est visible et cliquable.

La synchronisation GitHub sert de bibliotheque publique. Elle ne modifie aucun document automatiquement.

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
- Excel XLSX, hors focus de l'atelier de modification.

Conversions prioritaires :

```text
DOCX -> PDF
PDF  -> DOCX
```

Regles :

- DOCX -> PDF doit servir aux exports propres de CV, lettres et propositions ;
- PDF -> DOCX doit etre vu comme une reconstruction editable, pas comme une garantie de mise en page parfaite ;
- les conversions Excel restent secondaires et peuvent revenir apres stabilisation du workflow DOCX/PDF ;
- les conversions doivent rester locales ;
- aucun document personnel converti ne doit etre committe dans le repo public.
- les erreurs utilisateur sont journalisees dans `~/.autocv/logs/autocv.log`.

Cas d'usage V1 :

- convertir une lettre DOCX en PDF final ;
- reconstruire un PDF en DOCX editable quand necessaire ;
- ouvrir la copie obtenue dans Word pour correction manuelle.

## Logs Locaux

Auto-CV garde un journal local pour diagnostiquer les erreurs sans bruit dans l'interface :

```text
~/.autocv/logs/autocv.log
```

Ce journal couvre notamment les erreurs d'ouverture, conversion, restauration, suppression et creation de pack.

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
