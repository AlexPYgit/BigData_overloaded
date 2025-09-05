import json
import os
import h3
import pandas as pd
import xgboost as xgb
from dotenv import load_dotenv
from pyspark.sql import SparkSession
from pyspark.sql.functions import expr
from pyspark.sql.functions import udf, col, count, avg
from pyspark.sql.types import StringType
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score, accuracy_score, f1_score
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split


load_dotenv()

# --- 1. Initialisation de Spark ---
spark = SparkSession.builder \
     .appName("prediction-visualization") \
     .config("spark.jars.packages", "org.postgresql:postgresql:42.6.0") \
     .getOrCreate()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# Construire l'URL JDBC dynamiquement
# --- 2. Chargement des données (similaire à ton code précédent) ---
jdbc_url = f"jdbc:postgresql://{DB_HOST}:{DB_PORT}/{DB_NAME}"

connection_properties = {
    "user": DB_USER,
    "password": DB_PASSWORD,
    "driver": "org.postgresql.Driver"
}

# Requête SQL pour récupérer les colonnes nécessaires
query = """
(
  SELECT location_latt AS latitude,
         location_long AS longitude,
         declared_at,
         closed_at
  FROM incidents
  WHERE declared_at >= date_trunc('month', CURRENT_DATE - interval '2 month')
    AND declared_at < date_trunc('month', CURRENT_DATE)
) AS incidents
"""

df = spark.read.jdbc(url=jdbc_url, table=query, properties=connection_properties)

# --- 3. Ajout des colonnes temporelles et H3 ---
df = df.withColumn("day_of_week", expr("dayofweek(declared_at)"))
df = df.withColumn("hour_of_day", expr("hour(declared_at)"))
df = df.withColumn("duration_hours",
    (expr("unix_timestamp(closed_at) - unix_timestamp(declared_at)") / 3600).cast("double"))

def lat_lng_to_h3_R9(lat, lng, resolution=9):
    return h3.latlng_to_cell(lat, lng, resolution)
lat_lng_to_h3_udf = udf(lat_lng_to_h3_R9, StringType())
df = df.withColumn("h3_index", lat_lng_to_h3_udf(col("latitude"), col("longitude")))

# --- 4. Agrégation par H3 et colonnes temporelles ---
agg_df = df.groupBy("h3_index", "day_of_week", "hour_of_day") \
           .agg(count("*").alias("incident_count"),
                avg("duration_hours").alias("avg_duration_hours"))


# --- 5. Conversion en Pandas ---
train_data_pd = agg_df.toPandas()
print(train_data_pd.head(5))

# Encodage du h3_index en entier
le = LabelEncoder()
train_data_pd["h3_index_encoded"] = le.fit_transform(train_data_pd["h3_index"])

# Features (X) et target (y)
X = train_data_pd[["day_of_week", "hour_of_day", "h3_index_encoded", "avg_duration_hours"]].values
y = train_data_pd["incident_count"].values

# On redécoupe la base en train/test
X_train,X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# --- 6. Entraînement du modèle ---
model = xgb.XGBRegressor(
    objective="count:poisson",
    random_state=42,
    n_estimators=500,
    max_depth=8,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8
)
model.fit(X_train, y_train)

# --- 7. Prédictions ---
y_test_pred = model.predict(X_test)
y_train_pred = model.predict(X_train)

# --- 8. Calcul des métriques ---
mse = mean_squared_error(y_train, y_train_pred)
mae = mean_absolute_error(y_train, y_train_pred)
r2 = r2_score(y_train, y_train_pred)

results_df = pd.DataFrame(X_train, columns=["day_of_week", "hour_of_day", "h3_index_encoded", "avg_duration_hours"])
results_df["h3_index"] = le.inverse_transform(results_df["h3_index_encoded"].astype(int))
results_df["predicted_incident_count"] = y_train_pred
results_df["true_incident_count"] = y_train

print("=== Métriques du modèle ===")
print(f"MAE (Mean Absolute Error) : {mae:.2f}")
print(f"MSE (Mean Squared Error) : {mse:.2f}")
print(f"R² (Coefficient de détermination) : {r2:.2f}")
# Score global du modèle (R² sur tout X, y)
print("\nScore global du modèle :", model.score(X, y))

print("\n=== agg_df (résolution 9) ===")
agg_df.show(10, truncate=False)

# --- 10. Regroupement par jour de la semaine ---
grouped_by_day = results_df.groupby(["day_of_week", "hour_of_day"]) \
    .agg({
        "predicted_incident_count": "sum",
        "true_incident_count": "sum",
        "h3_index": lambda x: list(set(x))  # liste unique de zones H3 par jour
            })     \
    .reset_index()

# Construction JSON hiérarchique
structured = {}

for day in range(1, 8):  # 1=dimanche ... 7=samedi
    structured[str(day)] = {}
    for hour in range(0, 24):  # heures 0 à 23
        row = grouped_by_day[
            (grouped_by_day["day_of_week"] == day) &
            (grouped_by_day["hour_of_day"] == hour)
        ]
        if not row.empty:
            r = row.iloc[0]
            structured[str(day)][str(hour)] = {
                "predicted_incident_count": int(r["predicted_incident_count"]),
                "true_incident_count": int(r["true_incident_count"]),
                "h3_index": r["h3_index"]
            }
        else:
            structured[str(day)][str(hour)] = {
                "predicted_incident_count": 0,
                "true_incident_count": 0,
                "h3_index": []
            }

# Sauvegarde
with open("grouped_h3_by_day_structured.json", "w") as f:
    json.dump(structured, f, indent=2, ensure_ascii=False)

