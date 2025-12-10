import requests
import json

BASE_URL = "http://localhost:5000/api"


# ===========================================================

4.1
curl "http://localhost:5000/api/articles"
curl "http://localhost:5000/api/articles/5"

4.2
curl -X POST "http://localhost:5000/api/articles" -H "Content-Type: application/json" -d '{"title": "DEMO CREATE ARTICLE", "text": "JUST CREATED ARTICLE", "category": "technology"}'
curl -X PUT "http://localhost:5000/api/articles/7" -H "Content-Type: application/json" -d '{"title": "UPDATED UPDATED UPDATED", "text": "ARTICLE IS UPDATED NOW"}'
curl -X DELETE "http://localhost:5000/api/articles/7"

4.3
curl "http://localhost:5000/api/articles/category/technology"
curl "http://localhost:5000/api/articles?category=technology"
curl "http://localhost:5000/api/articles?sort=date"
curl "http://localhost:5000/api/articles?category=technology&sort=date&limit=2"


4.4
curl "http://localhost:5000/api/comments"
curl -X POST "http://localhost:5000/api/comments" -H "Content-Type: application/json" -d '{"text": "JUST CREATED COMMENT", "author_name": "bot", "article_id": 6}'
curl "http://localhost:5000/api/comments/1"
curl -X DELETE "http://localhost:5000/api/comments/1"
