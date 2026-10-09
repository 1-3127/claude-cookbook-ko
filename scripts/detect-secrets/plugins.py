import re

from detect_secrets.core.log import log
from detect_secrets.plugins.base import BasePlugin


class AnthropicSecretsDetector(BasePlugin):
    """Notebook에서 일반적인 API key와 credential을 검사합니다."""

    log.info("Running Anthropic Secrets Detector")
    secret_type = "API Credentials"  # type: ignore  # noqa: S105

    denylist = [
        # Anthropic API key (sk-ant-api03-...)
        re.compile(r"sk-ant-api03-[A-Za-z0-9_-]{95,}"),
        # 기타 API key (sk-...)
        re.compile(r"sk-[A-Za-z0-9]{48,}"),
        re.compile(r"pa-[A-Za-z0-9]{48,}"),
        # 일반적인 API key pattern
        re.compile(r'api[_-]?key[\'"\s]*[:=][\'"\s]*[A-Za-z0-9_\-]{20,}', re.IGNORECASE),
        re.compile(r'apikey[\'"\s]*[:=][\'"\s]*[A-Za-z0-9_\-]{20,}', re.IGNORECASE),
    ]
