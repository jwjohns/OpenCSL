from fastapi import FastAPI, HTTPException
from .models import Metric, Dimension
from .utils import load_semantics

app = FastAPI(title="Customer Semantic Layer", version="0.1.0")

# Load all semantic definitions on startup
semantics = load_semantics()

@app.get("/")
def root():
    return {
        "message": "Customer Semantic Layer - Take back control of your data semantics",
        "version": "0.1.0",
        "metrics_count": len(semantics["metrics"]),
        "dimensions_count": len(semantics["dimensions"])
    }

@app.get("/metrics")
def list_metrics():
    return list(semantics["metrics"].keys())

@app.get("/dimensions")
def list_dimensions():
    return list(semantics["dimensions"].keys())

@app.get("/metric/{name}")
def get_metric(name: str):
    metric = semantics["metrics"].get(name)
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")
    return metric

@app.get("/dimension/{name}")
def get_dimension(name: str):
    dim = semantics["dimensions"].get(name)
    if not dim:
        raise HTTPException(status_code=404, detail="Dimension not found")
    return dim

@app.get("/reload")
def reload_semantics():
    """Reload semantic definitions from disk"""
    global semantics
    semantics = load_semantics()
    return {
        "message": "Semantics reloaded",
        "metrics_count": len(semantics["metrics"]),
        "dimensions_count": len(semantics["dimensions"])
    }