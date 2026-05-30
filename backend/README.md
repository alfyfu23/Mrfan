# Backend

Django 5 + Channels + Daphne backend for the MrFan IM system.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py makemigrations account friend chat
python manage.py migrate
daphne -b 0.0.0.0 -p 8000 im.asgi:application
```

## Testing

```bash
bash test.sh
```

## API Documentation

See [CHAT_API_DOCUMENTATION.md](CHAT_API_DOCUMENTATION.md) for detailed API reference.

### Response Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1001 | Registration failed — missing username or password |
| 1002 | Registration failed — username already taken |
| 1003 | Login failed — username not found |
| 1004 | Login failed — incorrect password |
