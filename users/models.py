from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager


class UserManager(BaseUserManager):
    def create_user(self, kakao_id=None, username=None, role=None, phone_number=None, password=None, **extra_fields):
        if not kakao_id and not username:
            raise ValueError("Users must have a kakao_id or username")

        user = self.model(
            kakao_id=kakao_id,
            username=username or kakao_id,  # ✅ username 자동 채우기
            role=role,
            phone_number=phone_number,
            **extra_fields,
        )
        user.set_password(password or self.make_random_password())
        user.save(using=self._db)
        return user

    def create_superuser(self, kakao_id=None, username=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        return self.create_user(
            kakao_id=kakao_id,
            username=username or kakao_id,
            password=password,
            **extra_fields,
        )


class User(AbstractBaseUser, PermissionsMixin):
    kakao_id = models.CharField(max_length=255, unique=True)  # 카카오 로그인 ID
    username = models.CharField(max_length=150, unique=True, null=True, blank=True)  # ✅ Django 호환용 username

    role = models.CharField(
        max_length=10,
        choices=[('artist', 'Artist'), ('space', 'Space')],
        null=True, blank=True,
    )
    phone_number = models.CharField(max_length=15, null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    # Django 인증 기본 필드
    USERNAME_FIELD = "kakao_id"     # ✅ 로그인은 여전히 kakao_id 기준
    REQUIRED_FIELDS = ["username"]  # ✅ superuser 생성 시 username 필드 요구

    def __str__(self):
        return self.username or str(self.kakao_id)
