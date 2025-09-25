import argparse
import json
from pathlib import Path
import os, sys
import yaml

def create_superset_dataset(metric: dict, table: str, conn: dict) -> dict:
    """
    Create Apache Superset dataset configuration for a metric.

    Superset datasets define the data source, columns, and metrics
    that can be used in charts and dashboards.
    """
    dataset_name = f"{table}_{metric['name']}"

    # Generate SQL expression for the metric
    sql_expression = generate_superset_metric_sql(metric)

    dataset = {
        "table_name": table,
        "schema": conn.get('schema', 'public'),
        "database": {
            "database_name": conn.get('database', 'default'),
            "sqlalchemy_uri": generate_sqlalchemy_uri(conn)
        },
        "columns": [
            {
                "column_name": "user_id",
                "type": "STRING",
                "groupby": True,
                "filterable": True,
                "description": "User identifier"
            },
            {
                "column_name": "status",
                "type": "STRING",
                "groupby": True,
                "filterable": True,
                "description": "User status"
            }
        ],
        "metrics": [
            {
                "metric_name": metric['name'],
                "metric_type": "count_distinct" if "DISTINCT" in metric['definition'] else "sum",
                "expression": sql_expression,
                "description": f"CSL-generated metric: {metric.get('definition', '')}",
                "verbose_name": metric['name'].replace('_', ' ').title(),
                "d3format": ",d",
                "extra": {
                    "csl_generated": True,
                    "owner": metric.get('owner'),
                    "tags": metric.get('tags', [])
                }
            }
        ]
    }

    return dataset

def generate_superset_metric_sql(metric: dict) -> str:
    """Convert CSL metric definition to Superset SQL expression."""
    definition = metric['definition']

    # Superset uses slightly different SQL syntax
    # Convert common patterns
    sql = definition

    # Handle SAFE_DIVIDE (BigQuery) -> NULLIF pattern for Superset
    if 'SAFE_DIVIDE(' in sql:
        # Convert SAFE_DIVIDE(a, b) to CAST(a AS FLOAT) / NULLIF(b, 0)
        import re
        safe_divide_pattern = r'SAFE_DIVIDE\(([^,]+),\s*([^)]+)\)'

        def replace_safe_divide(match):
            numerator = match.group(1).strip()
            denominator = match.group(2).strip()
            return f"CAST({numerator} AS FLOAT) / NULLIF({denominator}, 0)"

        sql = re.sub(safe_divide_pattern, replace_safe_divide, sql)

    # Add WHERE clause filters to the expression if present
    if metric.get('filters'):
        # For Superset, we'll use conditional aggregation
        conditions = []
        for filter_expr in metric['filters']:
            conditions.append(f"CASE WHEN {filter_expr} THEN 1 ELSE NULL END")

        # Wrap the metric in conditional logic
        if 'COUNT(' in sql:
            # For count metrics, multiply by the condition
            base_metric = sql
            condition_clause = " * ".join(conditions) if conditions else "1"
            sql = f"{base_metric} * {condition_clause}"

    return sql

def generate_sqlalchemy_uri(conn: dict) -> str:
    """Generate SQLAlchemy connection URI based on connection type."""
    # Default to Snowflake for now, but could be extended for other databases
    server = conn.get('server', '')
    database = conn.get('database', '')
    schema = conn.get('schema', 'public')
    warehouse = conn.get('warehouse', '')

    if 'snowflake' in server.lower():
        # Snowflake SQLAlchemy URI format
        return f"snowflake://{{username}}:{{password}}@{server}/{database}/{schema}?warehouse={warehouse}"
    else:
        # Generic PostgreSQL format as fallback
        return f"postgresql://{{username}}:{{password}}@{server}:5432/{database}"

def create_superset_chart(metric: dict, dataset_name: str) -> dict:
    """Create a basic Superset chart configuration for the metric."""
    chart_config = {
        "slice_name": f"{metric['name'].replace('_', ' ').title()} Chart",
        "viz_type": "big_number_total",
        "datasource": dataset_name,
        "params": {
            "metric": metric['name'],
            "adhoc_filters": [],
            "row_limit": 10000,
            "time_range": "No filter",
            "granularity_sqla": None,
            "subheader": f"Generated from CSL metric: {metric['name']}"
        },
        "description": f"Auto-generated chart for CSL metric {metric['name']}",
        "cache_timeout": 3600,
        "owners": []
    }

    # Add filters if present in the metric definition
    if metric.get('filters'):
        adhoc_filters = []
        for filter_expr in metric['filters']:
            if ' = ' in filter_expr:
                field, value = filter_expr.split(' = ', 1)
                field = field.strip()
                value = value.strip().strip("'\"")

                adhoc_filters.append({
                    "clause": "WHERE",
                    "subject": field,
                    "operator": "==",
                    "comparator": value,
                    "expressionType": "SIMPLE"
                })

        chart_config["params"]["adhoc_filters"] = adhoc_filters

    return chart_config

def metric_to_superset_configs(metric: dict, table: str, conn: dict) -> tuple[dict, dict]:
    """Generate Superset dataset and chart configurations from CSL metric."""
    dataset_config = create_superset_dataset(metric, table, conn)
    chart_config = create_superset_chart(metric, f"{table}_{metric['name']}")

    return dataset_config, chart_config

def main():
    ap = argparse.ArgumentParser(description="Generate Superset configs from CSL metric")
    ap.add_argument("--metric", required=True, help="Metric name (e.g., active_users)")
    ap.add_argument("--table", required=True, help="Base table or view (e.g., users)")
    ap.add_argument("--server", required=True, help="Database server host")
    ap.add_argument("--database", required=True, help="Database name")
    ap.add_argument("--schema", required=True, help="Schema name")
    ap.add_argument("--warehouse", help="Warehouse name (for Snowflake)")
    ap.add_argument("--outdir", required=True, help="Output directory for JSON files")
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

    conn = {
        "server": args.server,
        "database": args.database,
        "schema": args.schema,
        "warehouse": args.warehouse
    }

    dataset_config, chart_config = metric_to_superset_configs(target, args.table, conn)

    # Create output directory
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # Write dataset config
    dataset_file = outdir / f"{args.table}_{args.metric}_dataset.json"
    with open(dataset_file, "w") as f:
        json.dump(dataset_config, f, indent=2)

    # Write chart config
    chart_file = outdir / f"{args.metric}_chart.json"
    with open(chart_file, "w") as f:
        json.dump(chart_config, f, indent=2)

    print(f"Generated Superset configurations:")
    print(f"  Dataset: {dataset_file}")
    print(f"  Chart: {chart_file}")

if __name__ == "__main__":
    main()