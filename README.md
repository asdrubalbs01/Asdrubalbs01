# Convertisseur de partitions PDF vers MusicXML (MuseScore)

Application web Flask permettant de convertir un PDF de partition en fichier MusicXML compatible MuseScore grâce à un outil d'OCR musical (Audiveris par défaut).

## Fonctionnalités
- Formulaire web simple pour téléverser un PDF.
- Conversion serveur via une commande OMR (Audiveris suggéré) et génération d'un fichier `.musicxml` ou `.mxl`.
- Lien de téléchargement direct après conversion.
- Gestion des erreurs courantes (pas de fichier, format incorrect, échec de conversion).

## Prérequis
- Python 3.10 ou supérieur.
- Un outil d'OCR musical installé sur la machine (Audiveris recommandé).

### Installation d'Audiveris (exemple)
1. Installez Java JDK 11 ou supérieur.
2. Téléchargez Audiveris depuis <https://github.com/Audiveris/audiveris/releases> (version CLI recommandée).
3. Ajoutez le binaire `audiveris` à votre `PATH` pour qu'il soit accessible depuis le terminal.
4. Vérifiez l'installation :
   ```bash
   audiveris -version
   ```

> Vous pouvez remplacer Audiveris par tout outil OMR capable de produire du MusicXML ; adaptez alors la commande dans `app.py` (fonction `build_conversion_command`).

## Installation locale
1. Clonez le dépôt puis placez-vous dedans :
   ```bash
   git clone <votre-depot.git>
   cd <votre-depot>
   ```
2. Créez (facultatif) un environnement virtuel puis installez les dépendances :
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows : .venv\\Scripts\\activate
   pip install -r requirements.txt
   ```
3. Lancez le serveur Flask :
   ```bash
   python app.py
   ```
4. Ouvrez l'application : <http://127.0.0.1:5000/>.

Les fichiers envoyés sont placés dans `uploads/` et les fichiers MusicXML générés dans `output/`.

## Commande de conversion utilisée
Par défaut (modifiable dans `app.py`), la commande exécutée est :
```bash
audiveris -batch -export -output output/ chemin/vers/fichier.pdf
```
Assurez-vous que le binaire `audiveris` est disponible dans votre `PATH`. Les fichiers générés (ex. `*.musicxml` ou `*.mxl`) sont ensuite proposés en téléchargement.

## Déploiement sur Render.com
1. Créez un compte sur <https://render.com/>.
2. Poussez ce projet sur un dépôt Git accessible (GitHub, GitLab, etc.).
3. Depuis le tableau de bord Render, créez un **New Web Service** et reliez-le à votre dépôt.
4. Choisissez l'environnement **Python**.
5. Commande de démarrage :
   ```bash
   gunicorn app:app
   ```
6. Render installe automatiquement les paquets listés dans `requirements.txt`.
7. Une fois le déploiement terminé, une URL publique sera disponible, par exemple :
   ```
   https://mon-convertisseur-partitions.onrender.com
   ```
   Utilisez ce lien pour accéder à la page de conversion en ligne.

## Structure du projet
```
app.py
Procfile
requirements.txt
uploads/        # PDF reçus
output/         # Fichiers MusicXML générés
templates/
  index.html
static/
  style.css
```

## Notes
- Assurez-vous que le serveur dispose des dépendances nécessaires à l'outil OMR (Java pour Audiveris, etc.).
- Pour renforcer la sécurité en production, définissez la variable d'environnement `FLASK_SECRET_KEY`.
- Les répertoires `uploads/` et `output/` peuvent être purgés périodiquement selon vos besoins.
