import argparse
import json
from pathlib import Path
import os, sys
import yaml

def create_powerbi_dataset(metric: dict, table: str, conn: dict) -> dict:
    """
    Create PowerBI dataset JSON for a metric definition.

    PowerBI datasets define tables, columns, measures, and relationships.
    This generates a basic dataset with a measure based on the CSL metric.
    """
    dataset_name = f"{metric['name']}_dataset"

    dataset = {
        "name": dataset_name,
        "compatibilityLevel": 1500,
        "model": {
            "culture": "en-US",
            "tables": [
                {
                    "name": table,
                    "columns": [
                        {
                            "name": "user_id",
                            "dataType": "string",
                            "sourceColumn": "user_id"
                        },
                        {
                            "name": "status",
                            "dataType": "string",
                            "sourceColumn": "status"
                        }
                    ],
                    "measures": [
                        {
                            "name": metric['name'],
                            "expression": generate_dax_expression(metric),
                            "formatString": "0"
                        }
                    ],
                    "partitions": [
                        {
                            "name": f"{table}_partition",
                            "mode": "import",
                            "source": {
                                "type": "m",
                                "expression": generate_powerquery_m(table, conn)
                            }
                        }
                    ]
                }
            ]
        }
    }

    return dataset

def generate_dax_expression(metric: dict) -> str:
    """Convert CSL metric definition to DAX expression."""
    definition = metric['definition']

    # Simple mapping from SQL aggregations to DAX
    if 'COUNT(DISTINCT' in definition:
        # Extract column name from COUNT(DISTINCT column_name)
        column = definition.split('COUNT(DISTINCT ')[1].split(')')[0].strip()
        dax = f"DISTINCTCOUNT({column})"
    elif 'SUM(' in definition:
        column = definition.split('SUM(')[1].split(')')[0].strip()
        dax = f"SUM({column})"
    elif 'AVG(' in definition:
        column = definition.split('AVG(')[1].split(')')[0].strip()
        dax = f"AVERAGE({column})"
    else:
        # Fallback - try to convert basic SQL to DAX
        dax = definition.replace('COUNT(DISTINCT ', 'DISTINCTCOUNT(').replace('AVG(', 'AVERAGE(')

    # Add filters if present
    if metric.get('filters'):
        filter_conditions = []
        for filter_expr in metric['filters']:
            # Convert SQL WHERE conditions to DAX FILTER expressions
            # This is basic - would need more sophisticated parsing for complex filters
            filter_conditions.append(filter_expr.replace("'", '"'))

        if filter_conditions:
            # Wrap in CALCULATE with filter conditions
            filter_str = ' && '.join([f"[{condition.split(' = ')[0]}] = {condition.split(' = ')[1]}" for condition in filter_conditions])
            dax = f"CALCULATE({dax}, {filter_str})"

    return dax

def generate_powerquery_m(table: str, conn: dict) -> str:
    """Generate Power Query M expression for data source connection."""
    # This generates M code for connecting to Snowflake
    # In a real implementation, you'd support multiple data sources

    server = conn.get('server', '')
    database = conn.get('database', '')
    schema = conn.get('schema', '')
    warehouse = conn.get('warehouse', '')

    m_expression = f'''
let
    Source = Snowflake.Databases("{server}", "{warehouse}"),
    Database = Source{{[Name="{database}"]}}[Data],
    Schema = Database{{[Name="{schema}"]}}[Data],
    Table = Schema{{[Name="{table}"]}}[Data]
in
    Table
'''

    return m_expression.strip()

def metric_to_powerbi_dataset(metric: dict, table: str, conn: dict) -> dict:
    """Generate PowerBI dataset JSON from CSL metric definition."""
    return create_powerbi_dataset(metric, table, conn)

def main():
    ap = argparse.ArgumentParser(description="Generate PowerBI dataset from CSL metric")
    ap.add_argument("--metric", required=True, help="Metric name (e.g., active_users)")
    ap.add_argument("--table", required=True, help="Base table or view (e.g., users)")
    ap.add_argument("--server", required=True, help="Snowflake account host")
    ap.add_argument("--database", required=True, help="Database name")
    ap.add_argument("--schema", required=True, help="Schema name")
    ap.add_argument("--warehouse", required=True, help="Warehouse name")
    ap.add_argument("--outfile", required=True, help="Output .json path")
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

    dataset = metric_to_powerbi_dataset(target, args.table, conn)

    # Ensure .json extension
    outfile = args.outfile
    if not outfile.lower().endswith(".json"):
        outfile += ".json"

    with open(outfile, "w") as f:
        json.dump(dataset, f, indent=2)

    print(f"Generated PowerBI dataset: {outfile}")

if __name__ == "__main__":
    main()