import sys

with open('f:/Antigrapvity/SEO Website DAFA web/backend/templates/production.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("x-if=\"getParsedMediaUrls()[0].endsWith('.mp4')\"", "x-if=\"getParsedMediaUrls().length > 0 && getParsedMediaUrls()[0].endsWith('.mp4')\"")
content = content.replace("x-if=\"!getParsedMediaUrls()[0].endsWith('.mp4')\"", "x-if=\"getParsedMediaUrls().length > 0 && !getParsedMediaUrls()[0].endsWith('.mp4')\"")

with open('f:/Antigrapvity/SEO Website DAFA web/backend/templates/production.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Replaced successfully")
