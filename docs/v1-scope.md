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
- les exports generes restent hors Git.

## Candidature Salariee

Workflow principal :

```text
Offre d'emploi
  -> fiche candidature
  -> CV generique
  -> lettre adaptee par IA locale
  -> validation humaine
  -> export
  -> statut
```

L'IA locale doit faire des ajustements legers :

- adapter l'accroche au poste ;
- reprendre les mots importants de l'offre ;
- relier l'offre a des projets data reels ;
- conserver un ton professionnel francais ;
- ne pas inventer d'experience.

## Projets GitHub

Auto-CV doit synchroniser les projets GitHub pour donner du contexte au moteur local.

Objectif :

- recuperer les projets publics pertinents ;
- extraire un resume local exploitable ;
- identifier les technos et themes ;
- permettre a l'IA de citer ou valoriser les bons projets dans une lettre.

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

La sortie IA n'est pas une lettre de motivation, mais une proposition courte :

```text
Besoin client
  -> projets pertinents
  -> approche proposee
  -> message freelance
```

Cette face reste plus legere que la partie salariat.

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
- envoi Gmail automatique ;
- scoring avance des offres ;
- app iPad autonome ;
- gestion CRM freelance complete ;
- moteur IA publie dans le repo public.
- preservation parfaite de mise en page PDF complexe ;
- extraction fiable de tableaux PDF non structures.
