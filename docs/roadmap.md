# Auto-CV - Feuille de Route

## Phase 0 - Fondation

- Definir le concept produit.
- Aligner l'architecture sur Windows PC + acces compagnon iPad.
- Fixer la dualite de langue : depot en anglais, produit en francais.
- Preparer une structure de depot public propre.
- Ajouter README, badges, CI et documentation.
- Garder l'application local-first par defaut.

## Phase 1 - MVP PC

- Construire une coque desktop Windows minimale.
- Ajouter les reglages locaux.
- Ajouter le stockage SQLite.
- Utiliser le dossier `%USERPROFILE%\Desktop\GENERIQUE PRO` comme source documentaire exclusive.
- Utiliser `%USERPROFILE%\Desktop\GENERIQUE PRO\Auto-CV\Result` comme dossier de sortie exclusif.
- Charger le CV generique sans modification IA.
- Charger la lettre generique comme base d'adaptation.
- Ajouter le renommage intelligent des CV, lettres, propositions et mails.
- Ajouter la gestion des offres d'emploi.
- Ajouter une premiere gestion legere des opportunites freelance.
- Ajouter la synchronisation locale du contexte projets GitHub.
- Ajouter une preparation de mail deterministe sans LLM.
- Ajouter la conversion DOCX/PDF et XLSX/PDF via adaptateurs locaux.
- Ajouter les fiches d'offres.
- Ajouter le suivi des statuts de candidature.

## Phase 2 - Workflow Documentaire

- Importer les CV et lettres existants.
- Creer des dossiers d'export par candidature.
- Generer des paquets de pieces jointes.
- Convertir les documents DOCX/PDF et XLSX/PDF dans les deux sens utiles.
- Ajouter des controles simples de coherence.
- Ajouter les paragraphes reutilisables.

## Phase 3 - Assistance IA

- Ajouter une interface de service IA.
- Ajouter des regles deterministes d'extraction et de scoring.
- Integrer un modele local via un runner interchangeable.
- Benchmarker des modeles open source candidats.
- Reactiver l'adaptation locale IA seulement si elle apporte un gain clair face au workflow deterministe.
- Ajouter une validation humaine obligatoire avant sortie finale.
- Garder la modification IA du CV hors scope tant que le CV generique suffit.

## Phase 4 - Integration Gmail

- Connecter Gmail via des identifiants OAuth locaux.
- Creer des brouillons d'emails.
- Joindre les documents selectionnes.
- Envoyer seulement apres confirmation explicite.
- Suivre les candidatures envoyees localement.

## Phase 5 - Compagnon iPad

- Ajouter un serveur prive FastAPI sur le PC.
- Exposer uniquement les workflows necessaires.
- Ajouter une authentification locale par token.
- Supporter l'acces LAN en premier.
- Evaluer un tunnel prive plus tard si necessaire.

## Phase 6 - Finition

- Ajouter le packaging Windows.
- Ajouter des outils de sauvegarde/export.
- Ajouter des captures du logiciel.
- Ajouter les notes de release.
- Soigner les tags et la presentation GitHub.
