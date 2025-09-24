# Contributing to Customer Semantic Layer (CSL)

Thank you for contributing to CSL! This project belongs to the community - together we're taking back control from vendor-driven "standards" that lock enterprises into proprietary ecosystems.

## Mission Reminder

**Vendors don't dictate our specs.** We build the semantic layer enterprises need, not what vendors want to sell us.

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- [uv](https://github.com/astral-sh/uv) (we use uv, not pip)

### Setup
```bash
git clone https://github.com/csl-community/customer-semantic-layer
cd customer-semantic-layer

# Set up environment
uv venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
uv sync

# Run the API
uvicorn registry.main:app --reload
```

### Test the POC
```bash
# List available metrics
curl http://localhost:8000/metrics

# Get a specific metric
curl http://localhost:8000/metric/active_users

# Generate Snowflake SQL
python registry/adapters/snowflake.py

# Generate Tableau TDS
python registry/adapters/tableau.py \
  --metric active_users \
  --table users \
  --server demo.snowflakecomputing.com \
  --database DEMO \
  --schema PUBLIC \
  --warehouse COMPUTE_WH \
  --outfile demo.tds
```

## 🛠️ How to Contribute

### 1. Add New Vendor Adapters
Help liberate more enterprises by supporting additional BI tools and databases:

- **PowerBI**: Generate PBIX or Power Query M code
- **Looker**: Generate LookML files
- **dbt**: Generate dbt model definitions
- **Apache Superset**: Generate dataset configurations
- **Grafana**: Generate dashboard JSON

Create adapters in `registry/adapters/` following the pattern of existing ones.

### 2. Enhance Semantic Definitions
Extend the YAML schema to support:

- Complex metric calculations
- Metric dependencies and lineage
- Data quality rules
- Business glossary terms
- Multi-dimensional hierarchies

### 3. Improve Governance
Add features that keep semantics under enterprise control:

- Approval workflows for semantic changes
- Audit trails and change history
- Role-based access control
- Semantic validation rules
- Integration with Git workflows

### 4. AI Integration
Make CSL the best semantic layer for AI copilots:

- Semantic embeddings for similarity search
- Natural language to metric translation
- Automated semantic discovery
- LLM-friendly API endpoints

## 📋 Contribution Guidelines

### Code Style
We use standard Python tooling (all managed by uv):

```bash
# Install dev dependencies
uv add --dev black isort flake8 pytest

# Format code
black .
isort .

# Lint
flake8 .

# Test
pytest
```

### Semantic Definitions
When adding example metrics/dimensions:

- Use realistic business scenarios
- Include proper ownership and tags
- Test with multiple vendor adapters
- Document any special considerations

### Vendor Adapters
When creating new adapters:

- Follow the pattern: `metric_dict → vendor_specific_output`
- Include command-line interface for testing
- Add comprehensive docstrings
- Test with real vendor tools when possible
- Never assume vendor-specific extensions

### Documentation
- Update README.md for new features
- Add examples for new adapters
- Keep CLAUDE.md current with development practices
- Include inline code comments for complex logic

## 🔄 Development Workflow

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-adapter`)
3. **Commit** your changes (`git commit -m 'Add PowerBI adapter'`)
4. **Push** to the branch (`git push origin feature/amazing-adapter`)
5. **Open** a Pull Request

### Pull Request Guidelines
- Describe the problem you're solving
- Include examples of the new functionality
- Test your changes thoroughly
- Update documentation as needed
- Keep commits focused and atomic

## 🏛️ Governance

CSL is community-governed to prevent vendor capture:

- **Open decisions**: Major changes discussed in GitHub Issues
- **Transparent process**: All governance documented publicly
- **Vendor neutrality**: No single company controls the roadmap
- **Community consensus**: Changes require community review

## 🤝 Community Standards

- **Be respectful**: We're all fighting vendor lock-in together
- **Stay focused**: Keep discussions on technical and architectural topics
- **Share knowledge**: Help others understand enterprise data challenges
- **Think long-term**: Consider how changes affect enterprise adoption

## 📞 Getting Help

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Architecture and design questions
- **Matrix/Discord**: Real-time community chat (coming soon)

## 🎉 Recognition

Contributors who make significant impacts will be:
- Listed in project credits
- Invited to the Technical Steering Committee
- Given commit access after sustained contributions

---

**Remember**: Every line of code you contribute helps enterprises break free from vendor-controlled semantics. Thank you for joining the fight! 🛡️