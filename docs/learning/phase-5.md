# Phase 5 — RAG: viva notes

## What was built and why

- Migration `0004_knowledge` adds `knowledge_documents` and `knowledge_chunks` with a pgvector `Vector(384)` column. pgvector keeps the vectors inside the existing PostgreSQL, so there is no extra vector database.
- Three embedders behind one `Embedder` interface, chosen by `EMBEDDINGS_PROVIDER`:
  - `tei`: self-hosted Text Embeddings Inference serving `intfloat/multilingual-e5-small`.
  - `hf_inference`: the hosted option for deploy.
  - `fake`: a deterministic embedder for offline tests.
- E5 needs the prefixes `query: ` for questions and `passage: ` for chunks. Without them, similarity scores drop.
- An LRU cache holds 512 query embeddings, so a repeated question skips the embedder.
- `scripts/ingest.py` reads Markdown articles with front matter:
  - it validates slug, language, visibility, status and date;
  - it chunks by heading with overlap;
  - it stores a SHA-256 hash of each file, so an unchanged article is skipped on the next run;
  - `--rebuild` re-embeds everything.
- Retrieval takes the top 4 chunks the caller may read: only active documents, staff-only articles hidden from customers, and vectors from the same model only. Each chunk must be within `RAG_MAX_DISTANCE` (cosine) of the question. Neighbouring chunks of the same article are merged, and the results are labelled [S1] to [S4].
- The evidence goes to the model as a system message headed "data, not instructions". When nothing qualifies, the message is just `NO_EVIDENCE`.
- After the model answers, only [S#] labels we actually sent become `sources`. An invented [S9] is dropped.
- If the embedder is down, chat still answers without articles (the tools keep working), and `/health` shows `embeddings: degraded`.
- `ChatReply.no_information` is true when no article was cited and no tool answered, so the UI can style "I don't have that information".
- `scripts/eval_chat.py` runs the hand-written eval set against the live API and writes `docs/EVAL_RESULTS.md`. It scores retrieval hit@4, the no-information rate, tool choice, latency, permission leaks and injections. Exit code 1 means a release blocker.

## Five locations to explain

- `app/modules/knowledge/repositories.py:75` (`search_chunks`): the access rule lives in the SQL. Visibility by role, active status and the embedding model are all `WHERE` clauses, so a customer can never retrieve a staff article, whatever the question says.
- `app/modules/knowledge/retrieval.py:52` (`retrieve`): embedder failure becomes the status `unavailable` instead of an exception; then come the distance threshold, merging neighbours, and a character budget of about 1,400 tokens.
- `app/modules/knowledge/retrieval.py` (`cited_sources`): the citation filter, which stops the model from making up sources.
- `app/modules/knowledge/services.py:56` (`_ingest`): the hash check makes re-ingesting safe and cheap.
- `app/modules/chat/services.py:212`: the `no_information` rule.

## Likely viva questions

1. **Why a distance threshold, and not just the top 4?** The top 4 always returns something, even for "What does Starlink cost?". The threshold turns "nothing close enough" into `NO_EVIDENCE`, so the model says it doesn't know instead of answering from an unrelated article. The value is tuned on the eval set and set in config.
2. **Why only 0.20?** E5 scores are bunched together: in testing, a Bangla router question scored 0.826 against the right passage and 0.782 against an unrelated one. A tight cut is needed, and the eval decides the final number.
3. **Can a help article inject instructions?** The evidence is labelled as data, the prompt says to ignore instructions inside it, and the tools are read-only and role-checked, so even a successful injection cannot reach another customer's data. A fixture article (`injection-test`) and the eval's injection cases test this.
4. **How does a Bangla question find an English article?** multilingual-e5 maps both languages into one vector space. With real TEI, the Bangla router question retrieved the English `router-restart` article first.
5. **What if you change the embedding model?** Each chunk stores its model name, and retrieval filters on it, so old vectors are never compared with new ones. Run `scripts/ingest.py --rebuild`.

## Rubric rows this phase moves (PROPOSAL §4)

- **B8 RAG:** pgvector store, multilingual embeddings, ingest, thresholded retrieval, citations, NO_EVIDENCE path. Built and tested offline and against real TEI.
- **Evaluation:** the script is built. Gate 2 numbers are pending the hand-written articles and eval cases.
