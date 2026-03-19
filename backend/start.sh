# 如果 CLEAR_DB 环境变量为 True，则清空数据库和媒体文件
if [ "$CLEAR_DB" = "True" ]; then
    echo "Clearing database and media..."
    rm -f data/db.sqlite3
    if [ -d "media" ]; then
        rm -rf media/*
    fi
fi

# 确保 data 目录存在
mkdir -p data

python manage.py makemigrations account
python manage.py makemigrations friend
python manage.py makemigrations chat
python manage.py migrate

export DJANGO_SETTINGS_MODULE=im.settings

# 绑定到 0.0.0.0，端口 80
daphne -b 0.0.0.0 -p 80 im.asgi:application