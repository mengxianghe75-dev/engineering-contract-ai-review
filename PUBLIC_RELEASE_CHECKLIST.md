# Public Release Checklist

Use this checklist before publishing the repository to GitHub, Gitee, or another public code hosting platform.

## Identity

- [x] Confirm author name in `README.md`.
- [x] Confirm contact details in `COMMERCIAL_LICENSE.md`.
- [x] Confirm copyright holder in `LICENSE`.
- [x] Confirm required notice in `NOTICE`.
- [x] Confirm the frontend author and commercial license text in:
  - `frontend/src/App.vue`
  - `frontend/src/views/LoginPage.vue`

## Sensitive Data

- [ ] Confirm `backend/uploads/` contains no real contracts or customer files.
- [ ] Confirm no `.env` files are committed.
- [ ] Confirm no API keys, database passwords, tokens, private keys, or internal URLs are committed.
- [ ] Confirm no database dumps, local SQLite files, or production logs are committed.

## License

- [ ] Confirm the repository description says: source-available, noncommercial use only.
- [ ] Confirm commercial use requires written authorization.
- [ ] Confirm attribution and copyright notices are retained.

## Product Demo

- [ ] Run `docker compose up --build -d`.
- [ ] Visit `http://127.0.0.1:5173`.
- [ ] Login with `admin / Admin123456`.
- [ ] Visit `http://127.0.0.1:8000/docs`.
- [ ] Run `curl http://127.0.0.1:8000/health`.

## Final Commands

```bash
find . -maxdepth 4 \( -name ".env" -o -name "*.pdf" -o -name "*.db" -o -name "node_modules" -o -name ".venv" \) -print
rg -n "TODO|TODO@example|作者名|Replace with" .
docker compose config
```
