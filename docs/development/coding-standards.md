# Coding Standards

## 1. General Principles
- Favor clarity over cleverness.
- Include comments for non-obvious logic.
- Use consistent naming conventions.

## 2. TypeScript (CDK)
- Use strict typing.
- Enable `strict` in tsconfig.json.
- Export constructs cleanly.
- Avoid magic numbers—use constants or env vars.

## 3. Python (Synthetic Pipeline)
- Follow PEP8 formatting.
- Add type hints where possible.
- Prefer pathlib over os.path.
- Log progress using print or logging module (no silent failures).

## 4. dbt Models
- Name staging models with `stg_*`.
- Use `ref()` and `source()` everywhere.
- Include `version: 2` YAML files with tests.
- Include lineage and documentation blocks.
- Materialize marts as tables unless otherwise required.

## 5. YAML Configs
- Indentation: 2 spaces.
- Use lowercase field names.
- Keep mappings and constraints in separate config files.

