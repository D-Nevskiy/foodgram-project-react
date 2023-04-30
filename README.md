[![foodgram workflow](https://github.com/D-Nevskiy/foodgram-project-react/actions/workflows/main.yml/badge.svg)](https://github.com/D-Nevskiy/foodgram-project-react/actions/workflows/main.yml)
# Foodgram – Продуктовый помощник

На этом сервисе пользователи смогут публиковать рецепты, подписываться на публикации других пользователей, добавлять понравившиеся рецепты в список «Избранное», а перед походом в магазин скачивать сводный список продуктов, необходимых для приготовления одного или нескольких выбранных блюд.

### Запуск проекта в контейнерах
- Клонирование удаленного репозитория
```
git clone git@github.com:D-Nevskiy/foodgram-project-react.git
cd infra
```
- В директории /infra создайте файл .env, с переменными окружения:
```
SECRET_KEY=secret_key # Секретный ключ приложения Django для обеспечения безопасности.
DB_ENGINE=django.db.backends.postgresql # Тип используемой базы данных.
DB_NAME=test # Название базы данных, в которой будут храниться данные приложения.
POSTGRES_USER=test # Имя пользователя, используемое для подключения к базе данных PostgreSQL.
POSTGRES_PASSWORD=test # Пароль пользователя, используемый для подключения к базе данных PostgreSQL.
DB_HOST=db # Адрес хоста базы данных.
DB_PORT=5432 # Порт, который будет использоваться для подключения к базе данных.
```
- Сборка и развертывание контейнеров
```
docker-compose up -d --build
```
- Выполните миграции, соберите статику, создайте суперпользователя
```
docker-compose exec backend python manage.py makemigrations
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py collectstatic --no-input
docker-compose exec backend python manage.py createsuperuser
```
Проект доступен по адресу: http://cookwithdanya.sytes.net/