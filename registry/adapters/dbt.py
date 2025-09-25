import argparse
import os
from pathlib import Path
import sys
import yaml

def create_dbt_model(metric: dict, table: str) -> str:
    """
    Create dbt model SQL for a metric.

    dbt models are SQL files that define transformations.
    This generates a model that calculates the metric.
    """
    model_name = f"mart_{metric['name']}"
    definition = metric['definition']

    # Build the SQL query
    sql_lines = ["{{", f"  config(materialized='table')", "}}", ""]

    # Add documentation comment
    sql_lines.extend([
        f"-- {metric['name'].replace('_', ' ').title()} Metric",
        f"-- Owner: {metric.get('owner', 'Unknown')}",
        f"-- Tags: {', '.join(metric.get('tags', []))}",
        ""
    ])

    # Build SELECT statement
    select_clause = f"SELECT {definition} AS {metric['name']}"

    # Add additional context columns if this is an aggregate
    if any(agg in definition.upper() for agg in ['COUNT', 'SUM', 'AVG', 'MAX', 'MIN']):
        # For aggregate metrics, we might want to include grouping dimensions
        sql_lines.append(f"{select_clause}")
        sql_lines.append(f"FROM {{{{ ref('{table}') }}}}")

        # Add WHERE clause for filters
        if metric.get('filters'):
            sql_lines.append("WHERE")
            filter_conditions = []
            for filter_expr in metric['filters']:
                filter_conditions.append(f"  {filter_expr}")
            sql_lines.extend(filter_conditions)
    else:
        # For calculated metrics, include the full expression
        sql_lines.append(f"{select_clause}")
        sql_lines.append(f"FROM {{{{ ref('{table}') }}}}")

        if metric.get('filters'):
            sql_lines.append("WHERE")
            for filter_expr in metric['filters']:
                sql_lines.append(f"  {filter_expr}")

    return "\n".join(sql_lines)

def create_dbt_schema(metric: dict, model_name: str) -> dict:
    """Create dbt schema.yml entry for the metric model."""

    schema = {
        "version": 2,
        "models": [
            {
                "name": model_name,
                "description": f"Calculated metric: {metric['name']}",
                "columns": [
                    {
                        "name": metric['name'],
                        "description": f"Metric definition: {metric['definition']}",
                        "meta": {
                            "owner": metric.get('owner', 'Unknown'),
                            "tags": metric.get('tags', [])
                        }
                    }
                ]
            }
        ]
    }

    return schema

def create_dbt_metric_yaml(metric: dict, model_name: str) -> dict:
    """
    Create dbt metrics.yml definition (dbt 1.6+ semantic layer).

    This creates a dbt semantic layer metric that can be used
    with dbt's built-in metrics functionality.
    """

    # Determine metric type based on definition
    definition = metric['definition'].upper()
    if 'COUNT(' in definition:
        metric_type = "count"
    elif 'SUM(' in definition:
        metric_type = "sum"
    elif 'AVG(' in definition:
        metric_type = "average"
    elif 'RATIO' in definition or 'DIVIDE' in definition:
        metric_type = "ratio"
    else:
        metric_type = "expression"

    dbt_metric = {
        "version": 2,
        "metrics": [
            {
                "name": metric['name'],
                "label": metric['name'].replace('_', ' ').title(),
                "model": f"ref('{model_name}')",
                "description": f"CSL-generated metric: {metric.get('definition', '')}",
                "type": metric_type,
                "sql": metric['definition'],
                "timestamp": "created_at",  # Assuming a timestamp column exists
                "time_grains": ["day", "week", "month", "quarter", "year"],
                "dimensions": ["status"] if metric.get('filters') else [],
                "meta": {
                    "owner": metric.get('owner'),
                    "tags": metric.get('tags', []),
                    "csl_generated": True
                }
            }
        ]
    }

    # Add filters if present
    if metric.get('filters'):
        dbt_metric["metrics"][0]["filters"] = []
        for filter_expr in metric['filters']:
            dbt_metric["metrics"][0]["filters"].append({
                "field": filter_expr.split(' = ')[0].strip(),
                "operator": "=",
                "value": filter_expr.split(' = ')[1].strip().strip("'\"")
            })

    return dbt_metric

def metric_to_dbt_files(metric: dict, table: str) -> tuple[str, dict, dict]:
    """Generate dbt model SQL, schema YAML, and metric YAML from CSL metric."""
    model_name = f"mart_{metric['name']}"

    model_sql = create_dbt_model(metric, table)
    schema_yaml = create_dbt_schema(metric, model_name)
    metric_yaml = create_dbt_metric_yaml(metric, model_name)

    return model_sql, schema_yaml, metric_yaml

def main():
    ap = argparse.ArgumentParser(description="Generate dbt files from CSL metric")
    ap.add_argument("--metric", required=True, help="Metric name (e.g., active_users)")
    ap.add_argument("--table", required=True, help="Base table or view (e.g., users)")
    ap.add_argument("--outdir", required=True, help="Output directory for dbt files")
    args = ap.parse_args()

    # Load metric from semantics directory
    root = Path(__file__).resolve().parents[2]  # repo root
    sem_dir = root / "semantics" / "metrics"
    target = None

    for p in sem_dir.glob("*.y*ml"):
        with open(p, "r") as f:
            data = yaml.safe_load(f)
        if data.get("name") == args.metric:
            target = data
            break

    if not target:
        print(f"Metric '{args.metric}' not found in {sem_dir}", file=sys.stderr)
        sys.exit(1)

    model_sql, schema_yaml, metric_yaml = metric_to_dbt_files(target, args.table)

    model_name = f"mart_{args.metric}"

    # Create output directories
    outdir = Path(args.outdir)
    models_dir = outdir / "models" / "marts"
    models_dir.mkdir(parents=True, exist_ok=True)

    # Write model SQL file
    model_file = models_dir / f"{model_name}.sql"
    with open(model_file, "w") as f:
        f.write(model_sql)

    # Write schema YAML file
    schema_file = models_dir / "schema.yml"
    with open(schema_file, "w") as f:
        yaml.dump(schema_yaml, f, default_flow_style=False, sort_keys=False)

    # Write metrics YAML file
    metrics_file = outdir / "metrics.yml"
    with open(metrics_file, "w") as f:
        yaml.dump(metric_yaml, f, default_flow_style=False, sort_keys=False)

    print(f"Generated dbt files:")
    print(f"  Model: {model_file}")
    print(f"  Schema: {schema_file}")
    print(f"  Metrics: {metrics_file}")

if __name__ == "__main__":
    main()