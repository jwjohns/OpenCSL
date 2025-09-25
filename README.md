# Customer Semantic Layer (CSL)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![uv](https://img.shields.io/badge/package%20manager-uv-blue)](https://github.com/astral-sh/uv)

**Take back control of your data semantics. Vendors don't dictate our specs.**

An open source, enterprise-owned semantic control plane that prevents vendor lock-in from data companies like Snowflake, Tableau, and BlackRock.

## Mission

Enterprise data teams are being held hostage by vendor-controlled semantic layers. Companies like Snowflake, Tableau, and others are pushing "standards" that lock you into their ecosystems. **We refuse to let vendors dictate how enterprises define their business logic.**

The Customer Semantic Layer (CSL) puts semantic ownership back where it belongs: **with you**.

## Architecture

CSL follows these core principles:

- **Customer Sovereignty**: You own all business definitions, not vendors
- **Versioned & Auditable**: All semantic changes tracked like code
- **Portable**: Stored in neutral YAML/JSON, vendor-independent
- **Translatable**: Generate vendor-specific syntax on-demand
- **Composable**: Modular definitions that merge across domains
- **AI-First**: Native support for LLMs and semantic reasoning

```
┌─────────────────────────┐
│   Your Semantic Repo   │ ← YOU control this
│     (Git + YAML)       │
└───────────┬─────────────┘
            │
┌───────────▼─────────────┐
│    CSL Registry API     │
└─┬─────────┬─────────────┘
  │         │
  ▼         ▼
┌───────┐ ┌─────────────┐
│Vendor │ │   AI/LLM    │
│Adapter│ │  Semantic   │
│Layer  │ │    API      │
└───┬───┘ └─────────────┘
    │
    ▼
  Snowflake, Tableau, PowerBI...
  (They consume YOUR specs)
```

## Quick Start

```bash
git clone https://github.com/csl-community/customer-semantic-layer
cd customer-semantic-layer

# Set up environment (we use uv)
uv venv
source .venv/bin/activate
uv sync

# Start the registry
uvicorn registry.main:app --reload

# Your semantics are now available at:
# http://localhost:8000/metrics
# http://localhost:8000/dimensions
```

## Example Usage

### Define Your Metrics (YAML)
```yaml
# semantics/metrics/active_users.yaml
name: active_users
definition: "COUNT(DISTINCT user_id)"
filters:
  - "status = 'active'"
owner: analytics-team
tags: [user, engagement]
```

### Generate Vendor-Specific Output
```bash
# Generate Snowflake SQL
python registry/adapters/snowflake.py

# Generate Tableau TDS
python registry/adapters/tableau.py \
  --metric active_users \
  --table users \
  --server your-snowflake.com \
  --database PROD \
  --outfile active_users.tds

# Generate PowerBI Dataset
python registry/adapters/powerbi.py \
  --metric active_users \
  --table users \
  --server your-snowflake.com \
  --database PROD \
  --schema PUBLIC \
  --warehouse WH \
  --outfile active_users_dataset.json

# Generate Looker LookML
python registry/adapters/looker.py \
  --metric active_users \
  --table users \
  --outdir looker_output

# Generate dbt Models
python registry/adapters/dbt.py \
  --metric active_users \
  --table users \
  --outdir dbt_output

# Generate Superset Configs
python registry/adapters/superset.py \
  --metric active_users \
  --table users \
  --server your-snowflake.com \
  --database PROD \
  --schema PUBLIC \
  --outdir superset_output
```

### API Access
```bash
curl http://localhost:8000/metric/active_users
```

## Why This Matters

**The Problem**: Vendor-driven "standards" like OSI (Open Semantic Interchange) are trojan horses. They:
- Give vendors control over how you define your business
- Create new forms of lock-in at the semantic layer
- Force expensive migrations to "comply" with their specs
- Suppress innovation that doesn't fit their worldview

**Our Solution**: CSL flips the power dynamic:
- **You** define semantics in simple, portable YAML
- **Vendors** consume your definitions via adapters
- **Standards** emerge from community consensus, not corporate boardrooms
- **Migration** becomes trivial - just add a new adapter

## Contributing

This project belongs to the community, not any single company or vendor.

### How to Help
- **Add vendor adapters**: Support more BI tools, databases, and ML platforms
- **Improve governance**: Better approval workflows and audit trails
- **Extend semantics**: Support for more complex metric types and relationships
- **Documentation**: Help enterprises understand and adopt CSL

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## Project Governance

CSL is governed by the community to prevent vendor capture:

- **Technical Steering Committee**: Representatives from diverse enterprises and domains
- **Open Decision Making**: All major decisions made in public GitHub discussions
- **Vendor Neutral**: No single company controls the roadmap
- **Transparent Process**: Governance model documented and regularly reviewed

## Roadmap

### Phase 1: Foundation (Complete)
- [x] Core semantic schema (metrics, dimensions, entities)
- [x] Registry API service
- [x] Major vendor adapters (Snowflake, Tableau, PowerBI, Looker, dbt, Superset)

### Phase 2: Production Ready
- [ ] Governance workflows (approval, audit)
- [ ] Additional vendor adapters (Databricks, QuickSight, Grafana)
- [ ] Performance optimization and caching
- [ ] Authentication and authorization

### Phase 3: AI Integration
- [ ] LLM semantic API with embeddings
- [ ] Natural language query translation
- [ ] Automated semantic discovery
- [ ] Integration with AI copilots

### Phase 4: Enterprise Scale
- [ ] Multi-tenant deployment
- [ ] Advanced lineage tracking
- [ ] Semantic marketplace/sharing
- [ ] Real-time semantic validation

## Community

- **GitHub Discussions**: Planning and architecture discussions
- **Issues**: Bug reports and feature requests
- **Matrix/Discord**: Real-time community chat (coming soon)
- **Meetups**: Regular community calls (details TBD)

## License

MIT License - See [LICENSE](LICENSE) for details.

This ensures CSL remains free and open for all enterprises, forever.

---

**Remember**: Vendors serve us, not the other way around. Let's build the semantic layer WE need, not the one they want to sell us.

*Join the movement. Take back control of your data semantics.*