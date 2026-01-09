import pytest
from django.contrib.auth.models import User

@pytest.mark.django_db
def test_user_creation():
    # 장고 DB가 정상적으로 연결되어 유저가 생성되는지 확인하는 기초 테스트
user = User.objects.create_user(username="testuser", password="password")
assert user.username ==  "testuser"
assert User.objects.count() == 1