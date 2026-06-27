# Plan Stage 2.6.3

## Baseline

- `git fetch origin`, `git checkout main`, `git pull origin main`: up to date at `80071ec`.
- Parallel baseline found an infrastructure issue: commands that call `load_card_database()` concurrently race while rewriting `data/processed/cards_full.json`, producing `PermissionError` on Windows.
- Before changing game rules, fix database loading so read-only game commands do not rewrite derived JSON on every load.

## Confirmed Problems

- Trophy end-turn discard is still an automatic discard in production flow.
- `PendingChoice` exists only for attack target and defense windows; it is not generic enough for trophy discard, destroy/discard/gain and mayhem choices.
- `беспредел_10` is `not_implemented` and blocks strict mode.
- Some mayhem effects still bypass richer choice semantics or remain opaque `not_implemented`.
- Replay summary lacks detailed counters for pending choice creation/resolution, auto choices and mayhem handlers.
- Coverage distinguishes `partial_safe`/`partial_unsafe`, but it does not yet report mayhem and pending-choice blockers explicitly enough.

## Modules To Change

- `src/game/data.py`: avoid rewriting `cards_full.json` from normal database loads.
- `src/game/models.py`: extend `PendingChoice` to carry ids, options, source metadata and min/max choice counts while preserving existing uses.
- `src/game/legal_actions.py`: generate actions from generic pending options.
- `src/game/engine.py`: resolve generic pending choices; replace trophy auto-discard with pending choice; keep end-turn continuation safe.
- `src/game/effects.py`: move destroy/discard/gain effects that require a choice to pending choices.
- `src/game/mayhem.py`: introduce handler registry and implement `беспредел_10` through market attack primitives and source_kind `MARKET_MAYHEM`.
- `src/game/replay_summary.py`: add pending-choice, auto-choice and mayhem-handler counters.
- `src/game/effect_coverage.py`: report mayhem and pending-choice blockers.
- Tests and docs for Stage 2.6.3.

## Tests To Add

- Pending choice serialization, legal actions from options, random-agent resolution, logging and illegal option rejection.
- Trophy discard pending choice: creation, legal hand-card options, resolution, continuation and no production auto-discard.
- `беспредел_10`: attack detection in market, attack-only resolution, no main text, market source kind, no trophy, defense, ignored redirect, target pending choice and strict behavior for unparseable attacks.
- Destroy/discard/gain pending choices.
- Replay summary pending-choice and mayhem-handler counters.
- Coverage blockers for mayhem and pending choices.

## Risks

- The current `Action` model is compact; adding generic pending options must not break existing attack target and defense tests.
- `беспредел_10` can chain attacks and defense windows; keep the first pass deterministic and conservative.
- If a market attack is too complex, strict should fail clearly rather than applying guessed behavior.

## Out Of Scope

- Stage 2.7 scripted agents.
- RL, Gymnasium, PettingZoo, FastAPI, UI, network play.
- Full replay playback.
- Full implementation of every unique card effect.
