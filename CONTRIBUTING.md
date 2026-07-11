# Contributing to Next PMS

Thanks for your interest in improving Next PMS. This is a Frappe v15 app; contributions follow standard Frappe conventions.

## Getting set up

```bash
# in an existing frappe-bench (v15)
bench get-app https://github.com/sayanthns/next_pms.git
bench --site <your-site> install-app next_pms

# frontend (Vue 3 SPA)
cd apps/next_pms/frontend
yarn install
yarn dev          # dev server on :8081, proxies /api to :8000
# production build (commit the output — see below)
yarn build        # writes to next_pms/public/frontend
```

The SPA lives at `/next-pms`. See [docs/DEVELOPER.md](docs/DEVELOPER.md) for architecture, the API map, the metrics engine, and the deploy runbook.

## Ground rules

- **Follow Frappe conventions.** No f-string SQL (use `frappe.qb` or parameterised `frappe.db.sql`); coerce input with `cint`/`flt`/`cstr`/`getdate`; wrap user-facing errors in `frappe.throw(_())`; gate whitelisted methods that expose cross-user data.
- **Tests.** Backend logic ships with `FrappeTestCase` tests under `next_pms/api/test_*.py` or the doctype folder. Run:
  ```bash
  bench --site <site> run-tests --app next_pms
  ```
- **Built frontend assets are committed** (`next_pms/public/frontend`). If you change the SPA, run `yarn build` and commit the result in the same PR.
- **DocType changes** must survive migration — add a patch under `next_pms/patches/` for renames, and keep `docs/DEVELOPER.md` in sync when you touch the metrics engine or scheduler.
- **Keep the guide honest.** User-facing changes should be reflected in `next_pms/www/pms-guide.html` (served at `/pms-guide`).

## Pull requests

1. Branch from `main`.
2. Keep the change focused; describe what and why.
3. Ensure `run-tests` passes and `yarn build` is committed if the SPA changed.
4. Open the PR against `sayanthns/next_pms`.

## License

By contributing you agree your contributions are licensed under the [MIT License](LICENSE).
