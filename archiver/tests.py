from django.test import TestCase


class SmokeTest(TestCase):
    """기본 동작 확인용 테스트"""

    def test_basic_addition(self):
        """기본 산술 연산 테스트"""
        assert 1 + 1 == 2

    def test_django_setup(self):
        """Django 설정이 제대로 로드되는지 확인"""
        from django.conf import settings

        assert settings.configured is True
