import os

html = open("f:/Antigrapvity/SEO Website DAFA web/backend/templates/production.html", encoding="utf-8").read()
start = html.find("x-data=\"{")
end = html.find("\">", start)

js = html[start+8:end]
js = "({" + js + "})"

with open("f:/Antigrapvity/SEO Website DAFA web/backend/test_prod.js", "w", encoding="utf-8") as f:
    f.write(js)

os.system("node -c \"f:/Antigrapvity/SEO Website DAFA web/backend/test_prod.js\"")
