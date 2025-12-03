# Release Process

## 1. Versioning
This project uses semantic versioning:
- MAJOR: breaking changes
- MINOR: new features
- PATCH: fixes

## 2. Release Steps
1. Ensure all GitHub Actions workflows pass:
   - CDK synth
   - dbt tests
   - Synthetic smoke test
2. Update CHANGELOG.md (if present).
3. Tag the release:
```
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin vX.Y.Z
```
4. Create a GitHub Release with:
   - Summary of changes
   - Relevant artifacts (optional)

## 3. Post-Release
- Monitor issues.
- Update documentation for any user-facing changes.
