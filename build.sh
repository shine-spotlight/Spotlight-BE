#!/usr/bin/env bash
set -o errexit  # 에러 발생 시 스크립트 중단

pip install -r requirements.txt

python manage.py collectstatic --noinput

python manage.py migrate --noinput

# if [[ $CREATE_SUPERUSER ]]; then
#   echo "🔑 Creating Django superuser..."
#   python manage.py shell <<EOF
# from django.contrib.auth import get_user_model
# User = get_user_model()
# username = "${DJANGO_SUPERUSER_USERNAME}"
# email = "${DJANGO_SUPERUSER_EMAIL}"
# password = "${DJANGO_SUPERUSER_PASSWORD}"
# if not User.objects.filter(username=username).exists():
#     User.objects.create_superuser(username=username, email=email, password=password)
#     print("✅ Superuser created:", username)
# else:
#     print("⚠️ Superuser already exists:", username)
# EOF
# fi
