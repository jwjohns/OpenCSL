import argparse
from pathlib import Path
import os, sys
import yaml

def create_lookml_view(metric: dict, table: str) -> str:
    """
    Create LookML view definition for a metric.

    Looker uses LookML to define views, dimensions, and measures.
    This generates a basic view with the metric as a measure.
    """
    view_name = f"{table}_view"

    # Generate measure definition
    measure_lookml = generate_lookml_measure(metric)

    # Basic view template
    lookml = f'''view: {view_name} {{
  sql_table_name: {table} ;;

  dimension: user_id {{
    type: string
    sql: ${{TABLE}}.user_id ;;
  }}

  dimension: status {{
    type: string
    sql: ${{TABLE}}.status ;;
  }}

{measure_lookml}
}}'''

    return lookml

def generate_lookml_measure(metric: dict) -> str:
    """Convert CSL metric definition to LookML measure."""
    measure_name = metric['name']
    definition = metric['definition']

    # Convert SQL aggregations to LookML measure types
    if 'COUNT(DISTINCT' in definition:
        column = definition.split('COUNT(DISTINCT ')[1].split(')')[0].strip()
        measure_type = "count_distinct"
        sql_field = column
    elif 'COUNT(' in definition:
        column = definition.split('COUNT(')[1].split(')')[0].strip()
        if column == "*":
            measure_type = "count"
            sql_field = None
        else:
            measure_type = "count"
            sql_field = column
    elif 'SUM(' in definition:
        column = definition.split('SUM(')[1].split(')')[0].strip()
        measure_type = "sum"
        sql_field = column
    elif 'AVG(' in definition:
        column = definition.split('AVG(')[1].split(')')[0].strip()
        measure_type = "average"
        sql_field = column
    elif 'SAFE_DIVIDE(' in definition or 'NULLIF(' in definition:
        # Complex calculated measure - use the full expression
        measure_type = "number"
        sql_field = definition
    else:
        # Fallback to number type with full SQL
        measure_type = "number"
        sql_field = definition

    # Start building the measure
    lookml_lines = [f"  measure: {measure_name} {{"]
    lookml_lines.append(f"    type: {measure_type}")

    if sql_field:
        if measure_type == "number":
            # For complex calculations, use full SQL expression
            lookml_lines.append(f"    sql: {sql_field} ;;")
        else:
            # For simple aggregations, reference the column
            lookml_lines.append(f"    sql: ${{TABLE}}.{sql_field} ;;")

    # Add filters if present
    if metric.get('filters'):
        filter_conditions = []
        for filter_expr in metric['filters']:
            # Convert SQL WHERE conditions to LookML filters
            if ' = ' in filter_expr:
                field, value = filter_expr.split(' = ', 1)
                field = field.strip()
                value = value.strip().strip("'\"")
                filter_conditions.append(f"${{TABLE}}.{field} = '{value}'")
            else:
                filter_conditions.append(f"${{TABLE}}.{filter_expr}")

        if filter_conditions:
            filter_sql = " AND ".join(filter_conditions)
            lookml_lines.append(f"    filters: [where: \"{filter_sql}\"]")

    # Add metadata
    if metric.get('owner'):
        lookml_lines.append(f"    # Owner: {metric['owner']}")

    if metric.get('tags'):
        tags_str = ", ".join(metric['tags'])
        lookml_lines.append(f"    # Tags: {tags_str}")

    lookml_lines.append("  }")

    return "\n".join(lookml_lines)

def create_lookml_dashboard(metric: dict) -> str:
    """Create a basic LookML dashboard showcasing the metric."""
    dashboard_name = f"{metric['name']}_dashboard"

    dashboard = f'''dashboard: {dashboard_name} {{
  title: "{metric['name'].replace('_', ' ').title()} Dashboard"

  element: {metric['name']}_tile {{
    title: "{metric['name'].replace('_', ' ').title()}"
    type: single_value
    query: {{
      model: your_model
      explore: your_explore
      measures: [{metric['name']}]
    }}
  }}
}}'''

    return dashboard

def metric_to_lookml(metric: dict, table: str) -> tuple[str, str]:
    """Generate LookML view and dashboard from CSL metric definition."""
    view_lookml = create_lookml_view(metric, table)
    dashboard_lookml = create_lookml_dashboard(metric)
    return view_lookml, dashboard_lookml

def main():
    ap = argparse.ArgumentParser(description="Generate LookML files from CSL metric")
    ap.add_argument("--metric", required=True, help="Metric name (e.g., active_users)")
    ap.add_argument("--table", required=True, help="Base table or view (e.g., users)")
    ap.add_argument("--outdir", required=True, help="Output directory for .view.lkml and .dashboard.lkml files")
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

    view_lookml, dashboard_lookml = metric_to_lookml(target, args.table)

    # Create output directory
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # Write view file
    view_file = outdir / f"{args.table}.view.lkml"
    with open(view_file, "w") as f:
        f.write(view_lookml)

    # Write dashboard file
    dashboard_file = outdir / f"{args.metric}_dashboard.dashboard.lkml"
    with open(dashboard_file, "w") as f:
        f.write(dashboard_lookml)

    print(f"Generated LookML files:")
    print(f"  View: {view_file}")
    print(f"  Dashboard: {dashboard_file}")

if __name__ == "__main__":
    main()