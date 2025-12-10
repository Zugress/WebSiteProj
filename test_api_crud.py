import requests
import json

BASE_URL = "http://localhost:5000/api"


# print("=========1 Создаем статью:=========")
# response = requests.post(f"{BASE_URL}/articles", json={
#     "title": "TESTOVAYA STATIA",
#     "text": "THI IS TESTOVAYA FOR TEST TEST 1 JUST CREATED",
#     "category": "technology"
# })
# print(json.dumps(response.json(), indent=2))


# print("\n=========2 Получаем все статьи:=========")
# response = requests.get(f"{BASE_URL}/articles")
# data = response.json()
# print(f"Найдено статей: {data['count']}")


# if data['count'] > 0:
#     article_id = data['articles'][0]['id']
#     print(f"\n=========3 Обновляем статью ID={article_id}:=========")
#     response = requests.put(f"{BASE_URL}/articles/{article_id}", json={
#         "title": "UPDATED STATYA",
#         "text": "TEST OF THE UPDATE STATYA"
#     })
#     print(json.dumps(response.json(), indent=2))

# article_id = 8
# print("=========4 Удаляем статью:=========")
# response = requests.delete(f"{BASE_URL}/articles/{article_id}")
# print(json.dumps(response.json(), indent=2))