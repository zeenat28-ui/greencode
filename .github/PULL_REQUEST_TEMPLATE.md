## What & why

<!-- One or two sentences: what this changes and why. Link the issue: Closes #123 -->

## Type of change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that changes existing behaviour)
- [ ] Docs / chore (no production code change)

## How it was verified

- [ ] `python -m pytest tests/ -q` passes locally
- [ ] New/updated tests cover the change (or a note on why not)
- [ ] Secret scan is clean (`pre-commit run --all-files` or Gitleaks)

## Measurement honesty (required for anything touching energy/carbon)

- [ ] No fabricated figures: every number comes from a real engine call with provenance
- [ ] `measurement_is_hardware` and grid `intensity_source_tier` are surfaced, never hidden
- [ ] A missing measurement is withheld (e.g. `input_basis: "not_supplied"`), not invented

## Secrets checklist

- [ ] No `.env`, key, or token material is committed (`.env.example` placeholders only)
- [ ] Any new config key is documented in `.env.example` with a **non-token-shaped** placeholder

## Screenshots / logs (if UI or CLI output changed)

<!-- paste before/after -->
