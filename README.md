# Living Record

Organizations record everything — meetings, calls, shows, working sessions — and can ask that record almost nothing. When a question matters, the answer is asserted from memory, or invented by a tool that retrieves a few passages and guesses the rest.

Living Record is built for the owners of those recording estates: companies whose own recorded work is an asset they cannot query, and who need answers they can check. Its first buyer shape is the mid-market owner of a recording estate with a receipts problem — the answer has to be right, and it has to show its work.

## The difference

This is not a basic RAG application. A Living Record answer arrives in one of three states, and the state is part of the answer:

1. **Computed** — counts, enumerations, and other questions the record can settle are computed deterministically over the record itself. No model is in this path.
2. **Reasoned, through a fabrication gate** — questions that need synthesis are answered by Muse Wonder (Meta Model API) only over retrieved, citable evidence, and the system's evaluation batteries test exactly this path for fabrication.
3. **Refused** — when the record does not support an answer, the system says so, as a product state: *"Not in the record yet."* A refusal is a correct output, not an error.

One routing sentence: deterministic computation first, Wonder reasoning through the fabrication gate second, refusal third — in that order, every time.

## What it does

*Ingest on Demand:* point the system at a corpus of recordings it has never seen and it consumes it live — ingest, transcription and indexing, entity resolution — until the corpus can be asked questions and answer in the three states above. Ask a question before the ingest and it is refused; ask the same question after, and it is answered with citations to the second.

Every answer carries its evidence: the citation, the path that produced it (computed or reasoned — and whether a model was in that path), and its provenance. The full build record — method, evaluation evidence, tooling, and cost, receipt by receipt — is documented in the companion, *Anatomy of a System — Powered by Quanticomp*, which lives on Quanticomp's own surface. This repository is the public layer of that record, not the whole of it.

## What was built when — identification

This project was built for the Meta AI Developer Hackathon (Cerebral Valley), Startup track, during the event window **October 26 – November 4, 2026**. In keeping with the organizers' direction to startups building on an existing product, what follows distinguishes the three classes plainly, with honest dates.

**Built during the event (in-window).** The contest composition assembled for this entry: the Ingest-on-Demand harness in this repository (ingest, query, and synthesis tiers; entity stage; fixture and refusal batteries; failover drill; tier configuration), the three-state answer path as implemented here, the demo-surface machinery, and the in-window ingestion of the public demo corpora (public videos from Stripe Developers and Google Cloud Tech, ingested as data during the window). The demo film and the *Anatomy of a System* companion are also in-window work; they live outside this repository.

**Pre-existing product and corpora (not built during the event).** Quanticomp operates a production archive service that predates this event. Its reference proof — a searchable, citation-verified archive of the Kill Tony catalog (596 of 645 episodes with transcripts) — is pre-existing product evidence. It appears in this project only as identified proof and context, by manifest pointers; it is not demo substance, and its source, data, and production code are not in this repository.

**Preparation before the window (not claimed as in-window build).** On October 25, 2026, before the event window opened, the team prepared scaffolding, telemetry schemas, evaluation designs, and corpus screening for this entry. That preparation is identified here as preparation; nothing in it is claimed as work built during the event. The build record's own dates are the identification instrument, and they are kept honestly.

**Not in this repository.** Credentials and API keys, server configuration, production corpora and production source, and any other project's record. Components shared with the production product are described by method and telemetry in *Anatomy of a System*; their source does not publish here.

## Repository contents

- `harness/` — the contest build: `ingest.py` and `vtt.py` (corpus intake), `query.py` and `synthesize.py` (the three-state answer path and the synthesis tier), `entities.py` (entity stage), `tiers.json` (tier configuration: deterministic → Muse Wonder primary → open-weights overflow → local GPU), `fixtures*.json` with `run_fixtures.py` (the fixture instruments), `mode_refusal_battery.py` (the refusal battery), `failover_drill.py` (the overflow failover drill), `check_evidence.py` (evidence checks), `telemetry_run.py` (per-run telemetry and cost lines), `pointers.json` (manifest pointers to identified pre-existing proof).

## Built with

Meta Model API — Muse Wonder (reasoning tier) and Muse Spark (volume tier) — composed behind a deterministic layer, with an open-weights overflow tier (Muse Spark Open via partner inference) and a local open-weights transcription tier. Every metered run is recorded, with its cost, in the project's finance ledger, and every feature carries an entry in the companion's tooling ledger: what it does, its evidence, and its finance line.

— Quanticomp

## Running it

The deterministic tiers run on Python 3 (standard library only). The synthesis tier is off unless explicitly enabled.

Ingest a corpus of WebVTT transcripts:

```
python3 harness/ingest.py build --source vtt-dir --dir <transcript-dir> --out corpora/<name>
```

Ingest from a corpus manifest (the adapter derives enumeration state, settle status, pointers, and provenance from the manifest):

```
python3 harness/ingest.py build --source manifest --manifest <manifest.json> --out corpora/<name>
```

Ask a question — every answer carries its class, its display badge (including whether a model was in the path), its citations, and its source currency:

```
python3 harness/query.py corpora/<name> "how many mentions of <term> in the corpus"
```

Verify the build against its instruments:

```
python3 harness/run_fixtures.py corpora/<name>
python3 harness/mode_refusal_battery.py
python3 harness/check_evidence.py
```

Synthesis (Wonder tier) runs only after the deterministic classes and the retrieval gate; it requires `META_API_KEY` in the environment and `HARNESS_SYNTHESIS=live`:

```
python3 harness/synthesize.py corpora/<name> "your question"
```
