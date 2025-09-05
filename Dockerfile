FROM apache/spark:4.0.0-java21-python3

WORKDIR /app

COPY requirements.txt /app/
COPY functionel_predict_incident_by_week.py /app/

# Installer les dépendances Python
USER root
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


