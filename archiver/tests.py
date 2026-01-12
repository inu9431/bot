# archiver/tests.py
from django.test import TestCase


class SmokeTest(TestCase):
    """기본 동작 확인용 테스트"""

    def test_basic_addition(self):
        """기본 산술 연산 테스트"""
        assert 1 + 1 == 2

    # DB 관련 테스트 주석 처리
    # def test_django_setup(self):
    #     from django.conf import settings
    #     assert settings.configured is True
