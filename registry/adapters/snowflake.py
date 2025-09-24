def metric_to_snowflake(metric: dict, table: str = "users") -> str:
    """Generate Snowflake SQL for a metric definition."""
    sql = f"SELECT {metric['definition']} AS {metric['name']} FROM {table}"
    if metric.get("filters"):
        sql += " WHERE " + " AND ".join(metric["filters"])
    return sql + ";"

if __name__ == "__main__":
    # Demo usage
    example_metric = {
        "name": "active_users",
        "definition": "COUNT(DISTINCT user_id)",
        "filters": ["status = 'active'"]
    }
    print("Snowflake SQL Output:")
    print(metric_to_snowflake(example_metric))