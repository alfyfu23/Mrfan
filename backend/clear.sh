#!/bin/zsh

# 谨慎使用，此程序会删除所有数据和迁移文件
# 应该仅仅用于开发阶段程序崩溃时

printf "WARNING: This will delete all the database and migration files. Only run in development.\nContinue? [Y/n]"
read -r response 
if [[ "$response" != "Y" && "$response" != "y" ]]; then
	echo "Aborted by user. No changes made."
	exit 1
fi

rm db.sqlite3
find . -path "*/migrations/*.py" ! -name "__init__.py" -delete
find . -path "*/migrations/*.pyc" -delete

python manage.py makemigrations
python manage.py migrate
