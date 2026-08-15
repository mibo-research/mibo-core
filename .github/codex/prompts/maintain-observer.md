# MIBO observer maintenance task

Read `AGENTS.md` first.

Inspect the MIBO automation layer for the smallest safe engineering improvement that increases readiness for the next registered survey wave.

Priorities:
1. deterministic execution and reproducibility;
2. protocol conformance;
3. secret isolation;
4. provider-adapter test coverage;
5. raw-data integrity and hashes;
6. failure/retry state-machine correctness;
7. actionable pre-wave diagnostics.

Do not:
- change frozen query text or hashes;
- change wave dates/windows;
- change k=10;
- change scientific hypotheses or thresholds;
- infer scientific conclusions from raw outputs;
- make provider calls or UI observations;
- expose secrets or raw research data.

Return:
- current readiness risks;
- the smallest recommended code change;
- tests that should prove it;
- whether the change would require a protocol amendment (normally: no).
