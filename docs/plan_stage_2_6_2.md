# Plan Stage 2.6.2

## Baseline

- `git pull origin main`: up to date at `080ff3f`.
- `pytest`: 85 passed.
- `python -m src.game.validate_manifest`: ok, main deck physical count 124.
- `python -m src.game.effect_coverage`: ok, `implemented_with_tests = 12`.
- Simulations in strict=False pass for 2/3/5 players.
- Replay write baseline passes.

## Confirmed Problems

- Dead wizard tokens are scored as `-1 VP`; rules require `-3 VP`.
- Healing has no 25 health cap.
- Death reset is already configurable at 20, but logs still carry a rule-clarification TODO.
- Damage source is modeled mostly as `source_player_id`; legend group attacks and market mayhems can look like player damage.
- Trophy ownership is absent.
- Group attack can open a defense window during end-turn legend reveal; this lifecycle must preserve the pending window and resume turn advancement afterward.
- Market mayhem and player-triggered mayhem need source metadata and replay visibility.
- Coverage still has only `partial`, not `partial_safe`/`partial_unsafe`.

## Modules To Change

- `src/game/models.py`: `SourceKind`, richer `EffectRequest`, `GameConfig.max_health`, trophy state and continuation metadata.
- `src/game/effects.py`: health cap, source-aware damage/death/trophy handling, redirect rules.
- `src/game/engine.py`: source metadata for attacks and group attacks, trophy end-turn draw/discard, group-attack continuation.
- `src/game/mayhem.py`: source-aware mayhem damage and setup/gameplay semantics where safe.
- `src/game/setup.py`: initial market mayhem behavior must remain non-resolving.
- `src/game/scoring.py`: `-3 VP` and existing tie-breaker by fewer tokens.
- `src/game/effect_coverage.py`: add `partial_safe`/`partial_unsafe` and missing-mechanic summaries.
- `src/game/replay.py`, `src/game/replay_summary.py`: source_kind, trophy, defense, mayhem and group attack diagnostics.
- Tests in `tests/` for the rule fixes and regressions.

## Tests To Add Or Update

- Dead wizard token penalty and tie-breaker tests.
- Heal cap tests.
- Death reset/log/end-pending tests.
- SourceKind tests for player-card, legend group attack, market mayhem and player mayhem.
- Trophy award/no-award tests and end-turn trophy draw/discard behavior.
- Group attack lifecycle tests around defense windows and redirect.
- Mayhem setup/gameplay pipeline tests.
- Coverage strict-mode tests for `partial_safe`/`partial_unsafe`.
- Replay summary tests for source kinds, trophy and defense/mayhem/group counters.

## Risks

- The current phase model assumes `end_turn` finishes synchronously; preserving a defense window during legend reveal needs careful continuation state.
- Full pending choices for destroy/discard/gain can broaden the engine significantly; if time is tight, mark unsupported choices as `partial_unsafe` instead of guessing.
- Stage 2.7 should not start unless Stage 2.6.2 DoD is actually met.

## Out Of Scope

- RL, Gymnasium/PettingZoo, FastAPI, UI, network play.
- Full implementation of all unique card effects.
- Full replay playback.
- Scripted agents unless Stage 2.6.2 is complete.
