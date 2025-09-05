# BigData_overloaded
Allows to build a docker image overloaded with means library and tools

> Projet intentionnellement “overloaded” pour tester une stack data/ML complète : 
Apache Spark 4, Python 3, scikit-learn, XGBoost, PostgreSQL 15, le tout orchestré avec Docker Compose.
L'ensembl permet de test de nombreuse configuration, librairie, ou modèle en jouant avec le script Python de base. 
Un dossier avec un script Faker Js à adapté celons vos besoin pour alimenter de donnée fictive votre base de données dans votre container. 

## 🧱 Stack et services 

> Dossier FeedBDD  
> Ce dossier contient un script fakerJs pour nourrire votre base de donnée de données fictive. 

PostgreSQL 15 : base OLTP/feature store minimal.
Spark Master : planification/coordination du cluster.
Spark Worker : exécute les tâches (peut être multiplié).
Spark App : conteneur applicatif (scripts Python/ML, libs installées).

Ports exposés:
Postgres : 5432   
Spark Master (UI) : 8083 (redirigé vers 8080 interne)  
Spark Master (cluster) : 7077  
Spark Worker (UI) : 8081  

Dans docker-compose.yml, le Master mappe 8083:8080 (UI) et 7077:7077 (cluster). Le Worker expose 8081:8081.

## ✅ Prérequis

>Docker + Docker Compose (v2+)  
Node  
Ressources : prévoir ~4–8 Go de RAM libres pour Spark + Postgres.

## 📁 Arborescence 
 ```bassh
.
├─ data/ # jeux de données + scripts Python
│ └─ functionel_predict_incident_by_week.py
├─ logs/
│ ├─ sparkmaster/
│ ├─ spark-worker-1/
│ └─ spark-app/
├─ Dockerfile # image du service spark-app
├─ requirements.txt # dépendances Python ML
└─ docker-compose.yml # 
```

## 🧾 Fichiers de config

#### 1) docker-compose.yaml => créer vos services dans votre image docker.
#### 2) Dockerfile (pour spark-app) => construit le service qui lance le script.
#### 3) requirements.txt => list toute les dépendance utilie à vortre projet. 

Modifier c'est fichier, pour ajouter ou retirer des librairie ou faire des modifications importante, puis re-builder votre image. 
 #### 4) Variables d’environnement (.env)

Vous pouvez définir vos propres identifiants Postgres dans un fichier .env à la racine du projet :
 ```bassh
DB_USER=feed_incident
DB_PASSWORD=feed_incident
DB_NAME=feed_incident
```
Ces variables sont injectées automatiquement dans docker-compose.yml grâce à la syntaxe ${VAR} :

 ```bassh
services:
  db:
    image: postgres:15
    container_name: postgres_db
    restart: always
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: ${DB_NAME}
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
```

Vous pouvez ainsi changer rapidement vos identifiants en éditant uniquement le fichier .env, sans modifier docker-compose.yml.

### 📂 Dossier data/ mappé dans le conteneur
Le dossier data/ à la racine du projet est partagé avec le répertoire /opt/spark/data à l’intérieur du conteneur spark-app (et aussi dans les services Spark Master et Worker).

Cela signifie que :

Si vous ajoutez un script Python dans ```./data``` sur votre machine hôte, il sera automatiquement visible dans le conteneur sous ```/opt/spark/data```.

Vous pouvez donc développer vos scripts localement et les exécuter directement dans le conteneur sans rebuild.

### Exemple :
Créez un script localement :   
  ```data/mon_script.py```

Entrez dans le conteneur :  
```docker exec -it spark-app /bin/bash```

Exécutez la commande suivante pour lancer votre script:  
```python3 /opt/spark/data/mon_script.py```

Ce mécanisme est très pratique pour itérer rapidement sur vos jobs Spark ou vos modèles ML.

## 🚀 Build & démarrage

Construire l’image applicative (spark-app) et démarrer l’ensemble :
```bash 
docker compose up -d --build 
```
Vérifier que tout est parti :
```bash 
docker compose ps
```
UIs :  
Spark Master UI : http://localhost:8083  
Spark Worker-1 UI : http://localhost:8081  
Postgres (CLI externe) : psql postgresql://feed_incident:feed_incident@localhost:5432/feed_incident  

## 🧰 Travailler dans le conteneur spark-app
#### 1) Ouvrir un shell interactif
```bash 
docker exec -it spark-app /bin/bash
```
 Cette commande vous permet d'entrer dans votre container depuis un terminale.
#### 2) Lancer un script Python « pur » (scikit-learn / XGBoost)
```bash 
python3 /opt/spark/data/functionel_predict_incident_by_week.py
```

## 🛠️ Problèmes courants & astuces

* Ports déjà utilisés : changez 8083/8081/5432 dans docker-compose.yml.

* Le Worker ne rejoint pas le Master : vérifiez command du worker et que spark://spark-master:7077 est reachable (logs du Worker, pare-feu local).

* Dépendances Python manquantes : rebuild avec --build après avoir modifié requirements.txt.

* Accès DB depuis Spark : n’utilisez pas localhost mais postgres_db comme host.

* Mémoire insuffisante : réduisez la taille des jobs ou augmentez la RAM Docker. Vous pouvez aussi limiter les ressources des services via deploy.resources.
* Vérifier les droits de lecture et d'écriture de vos fichier. (Spark à besoin d'écrire dans les dossier de son container mais aussi sur les dossier mapper sur votre machine)