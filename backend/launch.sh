#!/bin/zsh

mkdir -p data

python manage.py makemigrations
python manage.py migrate

# 启动 Django 项目在本地调试
echo "Starting Django development server..."

mkdir -p data

# 先迁移数据库
python manage.py migrate --noinput

export DJANGO_SETTINGS_MODULE=im.settings
daphne im.asgi:application
