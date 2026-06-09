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

### ApplicationRecord

Suit une candidature :

- offre associee ;
- variante de CV choisie ;
- lettre de motivation ;
- statut ;
- objet de l'email ;
- corps de l'email ;
- pieces jointes ;
- date d'envoi ;
- date de relance.

### GenerationRun

Trace une generation IA ou automatique :

- contexte d'entree ;
- modele ou moteur de regles utilise ;
- sortie generee ;
- statut de validation ;
- date.

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
