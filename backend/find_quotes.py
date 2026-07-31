lines = open("f:/Antigrapvity/SEO Website DAFA web/backend/templates/production.html", encoding="utf-8").readlines()
import sys; sys.stdout.reconfigure(encoding="utf-8")
for i, l in enumerate(lines):
    if i > 20 and i < 700 and '"' in l and 'x-data' not in l:
        print(f"{i}: {l.strip()}")
