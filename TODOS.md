# TODOS

Deferred from the 2026-09-08 build. Each entry is self-contained.

## P1

- **Run the weekly job off a laptop.** What: GitHub Actions or Cloud Run job instead of launchd. Why: a laptop that is closed on Monday morning skips the run. Blocker: Jarvis is OAuth authorization-code only, so a CI runner cannot log in; needs either a service credential from the Jarvis gateway team or the API-native path below. Effort: M (CC: S once the gateway supports a service token).
- **API-native Jarvis client.** What: replace `claude -p` workers with the Anthropic Messages API using the MCP connector against the Jarvis gateway plus the server-side web search tool. Why: removes the dependency on a logged-in CLI, makes cost and latency per call observable. Depends on: a bearer token the gateway accepts unattended. Effort: L (CC: M).

## P2

- **Week-over-week deltas.** What: diff today's `pulse.json` against the previous run and flag lights that changed colour and routes that changed. Why: the second run is where the tool starts earning its keep; a light flipping from yellow to red is the alert. Effort: S.
- **Slack digest.** What: post `pulse.md` to an internal channel after each run, as a draft-first flow. Why: nobody opens an HTML file on Monday. Rule: internal channel only, never external. Effort: S.
- **Harmonic and Fundrbird direct feeds.** What: pull headcount trends (Harmonic) and KPI series (Fundrbird) directly instead of via Jarvis summaries. Why: finer trend detection for the KPI light. Effort: M.

## P3

- **Segment map review cadence.** What: a quarterly reminder to re-curate `config/segments.yaml`; use the `segment_check` field each company worker returns to propose changes automatically. Effort: S.
- **Abeya segment verification.** The curated map guesses `food_ingredients_b2b`; confirm from the Jarvis profile and fix.
- **Fact deduplication across segment and company workers.** The same round can appear in both. Cosmetic today; matters once deltas exist.
