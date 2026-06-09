# Auto-CV - Concept Produit

## Vision

Auto-CV est un espace de travail personnel tout-en-un pour gerer les candidatures.

Son objectif est simple : supprimer la friction, la repetition et le jonglage de fichiers qui rendent les candidatures longues, penibles et mentalement usantes.

Le projet est personnel. Le depot GitHub est public et soigne comme un projet portfolio, mais le logiciel n'est pas pense comme un produit commercial.

## Probleme Central

Le workflow actuel de candidature disperse trop d'actions :

- plusieurs versions de CV ;
- reecritures regulieres de lettres de motivation ;
- offres d'emploi stockees ou copiees dans plusieurs endroits ;
- allers-retours dans l'explorateur Windows ;
- preparation manuelle des pieces jointes ;
- brouillons d'emails recrees a la main ;
- suivi fragile de ce qui a ete envoye, quand, et a qui.

Ce bruit fait perdre du temps et degoute progressivement du fait de postuler.

## Objectif Produit

Auto-CV doit transformer ce desordre en pipeline controle :

```text
Offre d'emploi
  -> analyse
  -> choix ou adaptation du CV
  -> generation de la lettre
  -> verification
  -> paquet de documents
  -> brouillon Gmail ou envoi confirme
  -> suivi de candidature
```

Le logiciel doit rester simple, professionnel et calme. On ne cherche pas une experience futuriste. On cherche un outil qui retire de la charge mentale.

## Utilisateur Principal

Le profil utilisateur cible est clair :

- jeune Data Scientist ;
- Master 2 valide via OpenClassrooms ;
- en recherche d'un poste salarie dans une grande entreprise ;
- besoin d'un outil pratique pour postuler plus vite, plus proprement, et avec moins de friction.

## Non-Objectifs

Auto-CV n'est pas :

- un SaaS ;
- un produit monetisable ;
- une plateforme multi-utilisateur ;
- une application macOS ;
- un outil qui postule automatiquement sans validation humaine ;
- un remplacement du jugement personnel.

## Workflows Cles

### 1. Gerer le Materiel Personnel

Stocker et organiser :

- profil maitre ;
- competences ;
- experiences ;
- formations ;
- projets ;
- variantes de CV ;
- modeles de lettres ;
- paragraphes reutilisables ;
- exports.

### 2. Capturer une Offre

Enregistrer :

- entreprise ;
- poste ;
- URL ;
- description ;
- localisation ;
- mots-cles ;
- deadline ;
- notes personnelles.

### 3. Preparer une Candidature

Le systeme doit aider a :

- identifier la meilleure variante de CV ;
- suggerer des ajustements ;
- generer ou adapter une lettre de motivation ;
- verifier la coherence entre offre, CV et lettre ;
- produire le paquet final de pieces jointes.

### 4. Suivre les Candidatures

Suivre des statuts comme :

- brouillon ;
- pret a envoyer ;
- envoye ;
- relance a prevoir ;
- entretien ;
- refuse ;
- accepte ;
- archive.

### 5. Workflow Gmail Optionnel

Plus tard, Auto-CV pourra preparer ou envoyer des emails via Gmail :

- creer un brouillon ;
- joindre CV et lettre ;
- enregistrer la date d'envoi ;
- stocker la reference localement.

Ce module reste secondaire par rapport au coeur documentaire.

## Role de l'IA

L'IA doit assister le workflow, pas remplacer la decision humaine.

Taches utiles :

- resumer une offre ;
- extraire les competences demandees ;
- comparer l'offre avec le profil candidat ;
- suggerer des ajustements de CV ;
- rediger une premiere version de lettre ;
- detecter les informations manquantes ;
- generer une checklist avant envoi.

La couche IA doit privilegier des modeles open source locaux afin de garder un cout nul et un maximum de confidentialite.

## Direction Interface

L'interface doit etre :

- simple ;
- lisible ;
- professionnelle ;
- rapide a parcourir ;
- structuree autour des workflows reels.

Auto-CV doit ressembler a un outil personnel serieux, pas a une demo visuelle.
