EJEMPLO = {"age": 65, "origin_of_tumor": 1, "type_of_admission": 1, "ecog": 2, "apacheii": 18,
           "sapsiii": 47, "sofa": 6, "lactate": 2.1, "pafi": 220, "platelet": 180000,
           "ventilatory_support": 1, "vasopressors_use": 0, "shock": 1, "sepsis": 1}


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200 and r.json()["model_version"]


def test_predict(client):
    r = client.post("/api/v1/predict", json={"inputs": [EJEMPLO, {"age": 50}]})
    assert r.status_code == 200
    preds = r.json()["predictions"]
    assert len(preds) == 2 and 0 <= preds[0]["p_estancia"] <= 1


def test_predict_valor_invalido(client):
    r = client.post("/api/v1/predict", json={"inputs": [{**EJEMPLO, "shock": 7}]})
    assert r.status_code == 422
