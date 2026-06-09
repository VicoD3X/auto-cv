# Auto-CV - Modele de Donnees Initial

Ce modele est un point de depart. Il evoluera quand le premier vrai workflow sera implemente.

## Entites

### CandidateProfile

Stocke le profil professionnel stable :

- identite ;
- resume professionnel ;
- competences ;
- formation ;
- experiences ;
- projets ;
- preferences.

### CVVariant

Represente une version de CV :

- nom ;
- role cible ;
- langue ;
- chemin du fichier source ;
- chemin du fichier exporte ;
- tags ;
- date de derniere modification.

### CoverLetterTemplate

Stocke une structure reutilisable de lettre de motivation :

- nom ;
- langue ;
- role cible ;
- corps du modele ;
- paragraphes reutilisables ;
- tags.

### Company

Stocke les informations d'une entreprise :

- nom ;
- site web ;
- secteur ;
- notes.

### JobOffer

Stocke une opportunite :

- entreprise ;
- intitule du poste ;
- URL ;
- description brute ;
- exigences extraites ;
- localisation ;
- type de contrat ;
- fourchette de salaire si disponible ;
- notes.

### FreelanceOpportunity

Stocke une opportunite freelance legere :

- client ou plateforme ;
- besoin exprime ;
- type de mission ;
- budget ou TJM si connu ;
- URL ;
- notes ;
- statut.

### ApplicationRecord

Suit une candidature :

- offre associee ;
- variante de CV choisie ;
- lettre de motivation ;
- statut ;
- chemin source du CV generique ;
- chemin de sortie du CV renomme ;
- chemin source de la lettre generique ;
- chemin de sortie de la lettre ou proposition ;
- objet de l'email ;
- corps de l'email ;
- pieces jointes ;
- date d'envoi ;
- date de relance.

### MailDraft

Stocke une proposition de mail :

- type d'opportunite ;
- cible ;
- poste ou mission ;
- objet ;
- corps ;
- pieces jointes ;
- moteur utilise ;
- statut de validation.

### GenerationRun

Trace une generation IA ou automatique :

- contexte d'entree ;
- modele ou moteur de regles utilise ;
- sortie generee ;
- statut de validation ;
- date.

### GitHubProject

Stocke un projet synchronise depuis GitHub :

- nom du depot ;
- URL ;
- description ;
- topics ;
- langages principaux ;
- resume README ;
- tags metier ;
- date de derniere synchronisation.

### ConversionJob

Suit une conversion documentaire :

- fichier source ;
- format source ;
- format cible ;
- fichier de sortie ;
- statut ;
- adaptateur utilise ;
- date ;
- notes de validation.

### AttachmentBundle

Regroupe les fichiers prepares pour une candidature :

- CV ;
- lettre de motivation ;
- fichiers optionnels ;
- dossier d'export ;
- checksum ou marqueur de version.

## Cycle de Statuts

```text
brouillon -> pret -> envoye -> relance -> entretien -> cloture
```

Statuts terminaux possibles :

- refuse ;
- accepte ;
- archive.
