# Per-user data isolation

An AI Desk process may serve many users. Each user's mail, files, and
calendar are a **partition**. A partition has exactly one owner. There
is no shared inbox, no default desk, and no "admin view" that unions
partitions.

## Identity

`user_id` is the partition key. In this starter it is an email-shaped
string (`demo@atlas.local`). Authentication is out of scope here; the
demo has no passwords. Whatever login you add later must resolve to
one `user_id` before any read or write.

## Records

Every stored record carries `owner_id`. A request may read or write a
record only when `owner_id == request.user_id`.

Surfaces that must be partitioned:

| Surface | Record |
| --- | --- |
| Mail | message |
| Files | path + body |
| Calendar | event |
| Drop | raw ingest, then the three artifacts above |

Drop is an *input*. The artifacts it produces are written only to the
target user's mail, files, and calendar.

## Bot writes

Night Desk is a bot, not a user. It has no desk of its own.

A bot write is `(target_user, artifacts)`. `target_user` is explicit.
The store attaches `owner_id = target_user` to every artifact. If
`target_user` is missing, the write is rejected.

A bot must not:

- infer the target from "the other logged-in user"
- write to every partition
- write to a global or null owner

## The two-user proof

This is the acceptance test for any implementation, including the
demo in this repo.

1. Create users `A` and `B`. Both desks start empty.
2. Run Night Desk ingest with `target_user = A` and any non-empty job
   text.
3. `A` has one mail item, one file, and one calendar event.
4. `B`'s mail, files, and calendar are still empty.

If step 4 fails, isolation is broken. Do not ship that store.

The same proof applies after you add a real login: log in as `B` and
render the desk. You must not see `A`'s artifacts. The desk API returns
only the current user's bodies. The demo may show **counts** for the two
built-in demo ids so you can see that the other partition stayed at
zero. Do not return another user's mail, files, or events.

## Implementation notes

- Store shape: `desks[user_id] -> {mail, files, calendar}`. Look up
  by `user_id` first; do not scan all rows and filter last.
- Do not put artifacts in a list and "also" tag them with a user.
  The list *is* the user's list.
- Cross-user queries are a bug, not a feature. Add an explicit
  export tool later if you need a backup; do not reuse the desk API.
- Session cookies or tokens name one user. Switching users replaces
  the session; it does not merge stores.
- Tests live in `tests/test_isolation.py`. Keep them green.

## What this spec does not cover

Encryption at rest, tenant billing, SSO, and provider OAuth. Those
can wrap this model. They must not replace the partition key.
