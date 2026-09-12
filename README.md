# AI Desk

An AI Desk is a per-user workspace with four surfaces:

| Surface | Role |
| --- | --- |
| Mail | Messages the owner (or a bot writing *as* that owner) can read |
| Files | Markdown notes and job briefs |
| Calendar | Events and due blocks |
| Drop | Inbox for raw text. Night Desk turns a drop into mail + a file + a calendar event |

This repo is a starter: a reusable ingest prompt, a short isolation spec, and a tiny local demo. It is not a hosted product. It does not talk to real mail or calendar providers.

## Why isolation matters

Two people can share one process. They must not share one desk.

If Night Desk writes a job for user A, user B's mail, files, and calendar stay empty. The demo encodes that rule: the store is keyed by user id, and a bot write takes an explicit target user. There is no shared inbox and no default desk.

See [docs/isolation.md](docs/isolation.md).

## Layout

- [`prompts/night-desk.md`](prompts/night-desk.md) — paste into any LLM. Raw job text in; JSON with mail, markdown file, and calendar event out.
- [`docs/isolation.md`](docs/isolation.md) — per-user partition rules you can implement in any language.
- [`demo/`](demo/) — stdlib Python server. No API keys, no passwords, no outbound network calls.
- [`examples/sample-job.txt`](examples/sample-job.txt) — dummy job text for the prompt or the demo Drop.
- [`tests/test_isolation.py`](tests/test_isolation.py) — two users, one write, the other partition stays empty.

## Local demo

Requires Python 3.9+.

```bash
git clone https://github.com/CaliXVibe/ai-desk.git
cd ai-desk
python3 -m demo
```

Open http://127.0.0.1:8765

1. You start as `demo@atlas.local`. The other login is `other@atlas.local`. Neither has a password.
2. Paste the contents of `examples/sample-job.txt` into Drop and submit.
3. Mail, Files, and Calendar for `demo@atlas.local` fill in. The ingest is a local heuristic (no LLM, no keys). Use `prompts/night-desk.md` when you want a model to do the same job.
4. Switch to `other@atlas.local`. That desk is still empty.

```bash
python3 -m unittest discover -s tests -v
```

## Using the Night Desk prompt

1. Copy `prompts/night-desk.md`.
2. Set `target_user` and `now`, then append the raw job text.
3. Send that to your model.
4. Write the JSON artifacts into the *target user's* partition only.

## Contribute

- Open an issue before a large change.
- Keep the demo free of secrets, `.env` files, and real credentials.
- New surfaces are fine if they stay per-user. Do not add a global inbox.
- Isolation tests must stay green: a write for user A never appears in user B.
- Docs and prompts are the product. Prefer a small, readable patch.

MIT. See [LICENSE](LICENSE).

A paid done-for-you install exists at https://calixion.gumroad.com/l/rxbkts
