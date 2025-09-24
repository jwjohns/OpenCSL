import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
import os, sys
import yaml

def create_tds(metric: dict, sql: str, conn: dict, datasource_name: str = None) -> ET.ElementTree:
    """
    Create a Tableau Data Source (TDS) file with Custom SQL relation.

    NOTE: Tableau TDS format is XML; this generator focuses on essentials:
    - datasource (name, version)
    - connection (class='snowflake', server, dbname, schema, warehouse)
    - relation type='text' (Custom SQL) with the generated SQL for the metric
    """
    if not datasource_name:
        datasource_name = f"{metric['name']}_datasource"

    # Create datasource element
    ds = ET.Element("datasource", {
        "caption": datasource_name,
        "inline": "true",
        "version": "18.1"  # broadly compatible
    })

    # Connection element
    connection = ET.SubElement(ds, "connection", {
        "class": "snowflake",
        "server": conn.get("server", ""),
        "dbname": conn.get("database", ""),
        "schema": conn.get("schema", ""),
        "warehouse": conn.get("warehouse", ""),
        "authentication": "username-password",  # or 'oauth', etc.
    })

    # Custom SQL relation
    relation = ET.SubElement(connection, "relation", {
        "name": "Custom SQL Query",
        "type": "text"
    })
    relation.text = sql

    # Add a simple column definition for the metric output
    column = ET.SubElement(ds, "column", {
        "name": f"[{metric['name']}]",
        "datatype": "integer",  # heuristic; extend mapping as needed
        "role": "measure",
        "type": "quantitative"
    })

    return ET.ElementTree(ds)

def metric_to_tableau_tds(metric: dict, table: str, conn: dict) -> ET.ElementTree:
    """Generate Tableau TDS file for a metric with Snowflake connection."""
    sql = f"SELECT {metric['definition']} AS {metric['name']} FROM {table}"
    if metric.get("filters"):
        sql += " WHERE " + " AND ".join(metric["filters"])
    sql += ";"
    return create_tds(metric, sql, conn)

def main():
    ap = argparse.ArgumentParser(description="Generate Tableau TDS file from CSL metric")
    ap.add_argument("--metric", required=True, help="Metric name (e.g., active_users)")
    ap.add_argument("--table", required=True, help="Base table or view (e.g., users)")
    ap.add_argument("--server", required=True, help="Snowflake account host")
    ap.add_argument("--database", required=True, help="Database name")
    ap.add_argument("--schema", required=True, help="Schema name")
    ap.add_argument("--warehouse", required=True, help="Warehouse name")
    ap.add_argument("--outfile", required=True, help="Output .tds path")
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

    tree = metric_to_tableau_tds(target, args.table, conn)

    # Ensure .tds extension
    outfile = args.outfile
    if not outfile.lower().endswith(".tds"):
        outfile += ".tds"

    tree.write(outfile, encoding="utf-8", xml_declaration=True)
    print(f"Generated Tableau TDS: {outfile}")

if __name__ == "__main__":
    main()