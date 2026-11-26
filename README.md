# Rakuten Product Classification – MLOps Pipeline

Weighted F1 of 73.4% on the test split: a linear SVM on TF-IDF text features, trained, versioned, served and monitored by an automated pipeline.

Measured as `f1_score(average="weighted")` on a stratified 20% test split, in a training run on 16,983 product listings (title and description) across 27 categories; test accuracy 73.1%, best 3-fold cross-validation score (weighted F1) 71.6%. The pipeline works on text only; images are not used yet.

Capstone of the MLOps Engineer certification (Liora, in partnership with Université Paris 1 Panthéon-Sorbonne), May to July 2025, built on the [Rakuten product classification challenge](https://challengedata.ens.fr/participants/challenges/35/). The focus is the infrastructure – orchestration, tracking, serving, monitoring – not model accuracy; the [Data Science capstone](https://github.com/PeterStieg/feb25_bds_classification-of-rakuten-e-commerce-products) covers the modelling. · [Demo on Streamlit](https://may25-bds-rakuten.streamlit.app/)

## Contents

- [Results](#results)
- [Setup](#setup)
- [Services](#services)
- [Pipeline](#pipeline)
- [Prediction API](#prediction-api)
- [Monitoring](#monitoring)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [Development](#development)
- [Troubleshooting](#troubleshooting)
- [Team](#team)
- [Status and Next Steps](#status-and-next-steps)

## Results

| Item | Detail |
| --- | --- |
| Model | SVM, linear kernel (`C` tuned over 0.1, 1, 10) |
| Features | TF-IDF, 1,000 features, French stop words removed |
| Data | 16,983 listings, 27 categories |
| Test weighted F1 | 73.4% |
| Test accuracy | 73.1% |
| Best cross-validation score (weighted F1, 3 folds) | 71.6% |

Compared in the same grid search: random forest, logistic regression and XGBoost.

## Setup

### Clone the repository

```bash
git clone https://github.com/PeterStieg/may25_bmlops_classification-of-rakuten-e-commerce-products.git
cd may25_bmlops_classification-of-rakuten-e-commerce-products
```

### Install and start

```bash
chmod +x ./scripts/*
./scripts/1_install_docker.sh      # Docker and unzip
./scripts/2_download.sh            # download the dataset (one-time)
./scripts/3_run_docker.sh          # write .env, build the ML image, start all services
```

For later starts, keep the project name the scripts and DAGs expect:

```bash
docker compose -p rakuten_project up -d
```

If services start slowly on a small machine, they retry on their own; all containers should be up within a few minutes.

### Load data and train

1. Open Airflow at [http://localhost:8080](http://localhost:8080).
2. Trigger the DAG `prepare_data` – it then loads 2,000 records every 15 minutes.
3. Trigger the DAG `ml_pipeline_docker` to preprocess, train and register a model.

To reset the data and create a fresh test set, use the DAG `reset_data`.

## Services

| Service | Address | Default login |
| --- | --- | --- |
| Airflow | [localhost:8080](http://localhost:8080) | `airflow` / `airflow` |
| Flower (Celery workers) | [localhost:5555](http://localhost:5555) | – |
| MLflow | [localhost:5001](http://localhost:5001) | – |
| FastAPI | [localhost:8000/docs](http://localhost:8000/docs) | – |
| Streamlit presentation | [localhost:8501](http://localhost:8501) | – |
| Grafana | [localhost:3000](http://localhost:3000) | `admin` / `admin` |
| Prometheus | [localhost:9090](http://localhost:9090) | – |
| pgAdmin | [localhost:8081](http://localhost:8081) | `rakuten@admin.com` / `rakutenadmin` |
| MinIO console | [localhost:9001](http://localhost:9001) | `rakutenadmin` / `rakutenadmin` |

The logins are defaults for local use. From another machine, replace `localhost` with the server's IP address.

## Pipeline

### Data

- **Incremental loading:** the DAG `prepare_data` loads 2,000 records every 15 minutes.
- **Reset:** the DAG `reset_data` resets the database and sets aside a stratified test set.
- **Storage:** PostgreSQL holds the text data and metadata. MinIO is set up as object storage but not used by the current DAGs.

### Preprocessing (`containers/rakuten-ml/preprocessing.py`)

- Text cleaning and French stop-word removal (NLTK)
- A cleaned text version for the classical models and a minimally cleaned one reserved for future BERT models
- TF-IDF with 1,000 features; features, targets and vectorizer go to `processed_data/`

### Training (`containers/rakuten-ml/training.py`)

- Random forest, logistic regression, SVM and XGBoost
- `GridSearchCV` with 3-fold cross-validation, scored by weighted F1
- Parameters, metrics and models logged to MLflow
- **Quality gate:** a new model is registered only if its weighted F1 on the evaluation set beats the registered model

### Retraining

The DAG `ml_pipeline_docker` decides on each run:

- **F1 below 0.7** on the evaluation set: retrain.
- **F1 at 0.7 or above:** retrain once at least 10,000 new records have arrived since the last training; otherwise skip.

### Drift detection

The DAG `run_drift_detection` runs every two hours. It compares a 5% sample against the reference data with Evidently's `DataDriftPreset`, flags drift when more than 30% of the columns drift, and saves an HTML report. It does not trigger retraining yet.

## Prediction API

`main.py` serves the current registered model with FastAPI: `POST /predict/` takes a title and a description (French text) and returns the category name, its confidence and the top three categories. Category IDs are mapped to names in `containers/rakuten-ml/category_mapping.json`.

```bash
curl -X POST "http://localhost:8000/predict/" \
     -H "Content-Type: application/json" \
     -d '{"title": "iPhone 13", "description": "smartphone avec écran OLED"}'
```

```json
{
  "predictions": [{
    "category": "Video Games & Consoles > Consoles",
    "confidence": 1.0,
    "top_3": [{
      "category": "Video Games & Consoles > Consoles",
      "confidence": 1.0
    }]
  }],
  "model_id": "rakuten_classifier",
  "status": "success"
}
```

The interactive docs at [localhost:8000/docs](http://localhost:8000/docs) accept the same request under "Try it out".

## Monitoring

Prometheus collects metrics from a StatsD exporter that receives the MLflow training metrics and from a node exporter. Grafana provisions three dashboards (`grafana/dashboards/`):

- **FastAPI Metrics:** total requests, requests per second, P95 latency, average request duration, requests by endpoint, error rate (4xx/5xx), requests in progress – Prometheus has a scrape job for FastAPI, but `main.py` doesn't expose a `/metrics` endpoint yet, so this dashboard stays empty
- **MLflow Metrics:** accuracy, cross-validation score and F1 over time, each with its best value in the last 24 hours; model runs over time and in the last 24 hours
- **Node Exporter System Metrics:** CPU, memory, disk throughput, network throughput

## Project Structure

```
main.py                     FastAPI application
streamlit_app.py, pages/    Streamlit presentation
containers/
├── rakuten-ml/             ML image: preprocessing, training, prediction,
│                           drift detection, category mapping
└── rakuten_st/             Streamlit helpers and flowcharts
dags/                       Airflow DAGs
├── prepare_data_dag.py     incremental loading (every 15 minutes)
├── ml_pipeline_docker_dag.py   retraining decision and training
├── reset_data_dag.py       database reset and test set
├── run_drift_detection_dag.py  drift detection (every 2 hours)
└── tasks/                  upload, download and ML task modules
grafana/                    dashboards and provisioning
prometheus.yml              scrape configuration
postgres-init/              database initialization
scripts/                    setup scripts 1–3
tests/                      API tests (pytest)
docker-compose.yml          all services
Dockerfile.api, Dockerfile.streamlit
requirements*.txt           dependencies per image
```

Created at runtime and not in the repository: `raw_data/`, `processed_data/` and the trained models in `models/`.

## Tech Stack

- **Orchestration:** Apache Airflow 3 with Celery workers, Redis and Flower
- **Storage:** PostgreSQL 16, MinIO (set up, not yet used)
- **Machine learning:** scikit-learn, XGBoost, NLTK
- **Tracking and registry:** MLflow
- **Serving:** FastAPI
- **Presentation:** Streamlit
- **Monitoring:** Prometheus, StatsD exporter, node exporter, Grafana
- **Drift detection:** Evidently
- **Containers:** Docker, Docker Compose
- **Tests:** pytest (API health and training-status checks)

## Development

All services share the Docker network `rakuten_project_default`, which is why the project name `rakuten_project` matters.

**ML code:** edit the scripts in `containers/rakuten-ml/` and test them in the container:

```bash
docker run --rm --network rakuten_project_default -v $(pwd)/containers/rakuten-ml:/app -w /app rakuten-ml:latest python your_script.py
```

Then add or update the DAGs in `dags/` and test them in the Airflow UI.

**API:** edit `main.py`, then build and test the image:

```bash
docker build -f Dockerfile.api -t rakuten-fastapi:latest .
```

**Monitoring:** edit `prometheus.yml` and the dashboards in `grafana/`; check the targets at [localhost:9090/targets](http://localhost:9090/targets).

Work on a feature branch and open a pull request with a note on how the change was tested.

## Troubleshooting

**Container build fails**

```bash
docker system prune -f
docker build --no-cache -t rakuten-ml:latest ./containers/rakuten-ml/
docker build --no-cache -f Dockerfile.api -t rakuten-fastapi:latest .
```

**API can't reach the ML pipeline or the database**
- Check that all containers are on `rakuten_project_default`.
- Check that models exist: `ls models/`
- Check that the database holds data: run the DAG `prepare_data`.

**Dashboards show no data**
- Check the Prometheus targets: [localhost:9090/targets](http://localhost:9090/targets)
- Check that the StatsD exporter runs: `docker ps | grep statsd`
- Run the ML pipeline at least once to create metrics.

**Retraining doesn't start**
- Check the evaluation F1 in MLflow: below 0.7 retrains at once.
- Check the backlog: at least 10,000 new records are needed above 0.7.

**DAG doesn't appear in Airflow**
- Check the syntax: `python dags/ml_pipeline_docker_dag.py`
- Refresh the Airflow UI and check the scheduler logs.

**Prediction errors**
- Check the logs: `docker logs rakuten-fastapi`
- Check that the models are mounted: `docker exec rakuten-fastapi ls /app/models/`

**Packages fail to install on the host**
- Use the Docker images instead; dependencies are in `containers/rakuten-ml/requirements_ml.txt` and `requirements_api.txt`.

## Team

Team project of four. Main contributions as listed on the Streamlit presentation's team page (`pages/2_Team_Presentation.py`):

- **Marie Ernø-Møller** – MLflow tracking, Evidently drift detection, Prometheus scraping and Grafana visualization
- **Qi Bao** – foundational architecture, Airflow orchestration, project management
- **Robert Wilson** – model development and evaluation, text preprocessing, FastAPI integration
- **Peter Stieg** – «debugging, testing and refactoring, text preprocessing, Streamlit presentation»

## Status and Next Steps

Learning project: the pipeline runs end to end – loading, training, quality gate, serving and monitoring – but has not been tested under production load. Drift detection reports but does not yet trigger retraining, the API has no authentication, and the FastAPI dashboard has no metrics source.

Next steps the team identified:

- Token-based API authentication
- Drift detection as a retraining trigger, with alerting
- Deep learning models for text (BERT) and images
- A/B testing and gradual rollout of new models
- CI/CD for tests, builds and deployment
- Managed storage and databases, Kubernetes, infrastructure as code

<!--
OPEN ITEMS – fill in, then delete this block and every «…» marker:

1. Your contribution, Team section: the wording in «…» is taken from the
   Streamlit team page. Confirm it or replace it.
-->
