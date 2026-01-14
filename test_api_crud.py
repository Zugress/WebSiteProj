

# регистрация через API с получением токена
curl -X POST http://localhost:5000/auth/register -H "Content-Type: application/json" -d '{"name":"Test User","email":"test@example.com","password":"test123"}'

# вход того же пользователя
curl -X POST http://localhost:5000/auth/login -H "Content-Type: application/json" -d '{"email":"test@example.com","password":"test123"}'

# создание статьи с JWT токеном
curl -X POST http://localhost:5000/api/articles -H "Content-Type: application/json" -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoyLCJ1c2VybmFtZSI6IlRlc3QgVXNlciIsImV4cCI6MTc2ODI3NDMyOSwiaWF0IjoxNzY4MjczNDI5LCJ0eXBlIjoiYWNjZXNzIn0.R6Yr2NpUgUts6iWb8_7oTlgBbo-Po0ID3Uk60rev7ck" -d '{"title":"My First Protected Article","text":"This article was created using JWT authentication","category":"technology"}'

# получение нового токена
curl -X POST http://localhost:5000/auth/refresh -H "Content-Type: application/json" -d '{"refresh_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoyLCJ1c2VybmFtZSI6IlRlc3QgVXNlciIsImV4cCI6MTc2ODg3ODIyOSwiaWF0IjoxNzY4MjczNDI5LCJ0eXBlIjoicmVmcmVzaCJ9.T9E3SHtKrjknMYSfncPtHoU4olXe282IOkl4xi-xTHc"}'

# выход из системы
curl -X POST http://localhost:5000/auth/logout -H "Content-Type: application/json" -d '{"refresh_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoyLCJ1c2VybmFtZSI6IlRlc3QgVXNlciIsImV4cCI6MTc2ODg3ODIyOSwiaWF0IjoxNzY4MjczNDI5LCJ0eXBlIjoicmVmcmVzaCJ9.T9E3SHtKrjknMYSfncPtHoU4olXe282IOkl4xi-xTHc"}'

# проверка без токена
curl -X POST http://localhost:5000/api/articles -H "Content-Type: application/json" -d '{"title":"Test Without Token","text":"Should fail","category":"general"}'
