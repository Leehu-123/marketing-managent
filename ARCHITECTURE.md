# Project Architecture Notes

## VPS Layout (`45.117.177.80`)

### Active Apps

| App | Directory | Docker Container | Port | Domain |
|-----|-----------|-----------------|------|--------|
| **DAFA Glass** (this repo) | `/var/www/marketing-management/` | `dafa_glass_backend` | 3007 → 8000 | `ldhuy.name.vn` |
| **Dakifa Marketing** | `/var/www/dakifa-marketing/` | `dakifa_backend` | 3006 → 8000 | `dakifamarketing.ldhuy.name.vn` |

### Important Rules

1. **Seeding feature** (chiến dịch seeding, seeding accounts, seeding tasks) belongs **ONLY** to the DAFA Glass app (`marketing-management` repo). Do NOT add or modify seeding code in Dakifa.

2. **Dakifa Marketing** is a completely separate app with its own database (`dakifa.db`). It does NOT have seeding functionality.

3. **DAFA Glass** uses `dafa_glass.db` as its database, mounted at `/app/dafa_glass.db` inside the container.

4. When making template changes inside `x-data="..."` attributes, **never use double quotes `"`** inside the attribute value. Use single quotes `'` instead, as `"` will break the HTML attribute boundary and crash Alpine.js.

5. The `dafa_glass_backend` container uses volume mounts for `/app/app`, `/app/templates`, `/app/static`, so code changes via `git pull` take effect immediately without rebuilding the image. A restart is only needed for Python code changes (not template changes).

6. **Multi-language Translation**: DAFA Glass app publishes ONLY in Vietnamese (Tiếng Việt). Do NOT add multi-language auto-translation, translations dependency, or Polylang multi-language linking to DAFA Glass (that feature belongs exclusively to Dakifa). NEVER touch or modify any code of Dakifa app.

