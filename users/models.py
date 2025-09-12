from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager


class UserManager(BaseUserManager):
    def create_user(self, kakao_id, role=None, phone_number=None, password=None, **extra_fields):
        if not kakao_id:
            raise ValueError("Users must have a kakao_id")
        user = self.model(
            kakao_id=kakao_id,
            role=role,
            phone_number=phone_number,
            **extra_fields,
        )
        # 비밀번호 없는 경우 랜덤 패스워드
        user.set_password(password or self.make_random_password())
        user.save(using=self._db)
        return user   # ✅ 반드시 User 인스턴스 반환

    def create_superuser(self, kakao_id, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(kakao_id, password=password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    kakao_id = models.CharField(max_length=255, unique=True)  # 카카오 로그인 ID
    role = models.CharField(
        max_length=10,
        choices=[('artist', 'Artist'), ('space', 'Space')],
        null=True, blank=True
    )
    phone_number = models.CharField(max_length=15, null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "kakao_id"
    REQUIRED_FIELDS = []  # 이메일, 비번 안 씀

    def __str__(self):
        return f"{self.kakao_id} ({self.role})"
