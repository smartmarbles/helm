# Contributing

## Git hooks (optional, one-time opt-in)

This repo ships a `pre-push` git hook in `.githooks/` that re-runs the
manifest-drift check also enforced in CI. It is not installed by default —
git only looks in `.githooks/` if you tell it to. To opt in, once per clone:

```sh
git config core.hooksPath .githooks
```

With that set, `git push` will run the manifest-drift check locally and
block the push if it fails, so you catch the error before it reaches
GitHub instead of waiting on CI.

This is purely a convenience. It's optional, and CI remains the enforced
backstop regardless of whether you opt in.
