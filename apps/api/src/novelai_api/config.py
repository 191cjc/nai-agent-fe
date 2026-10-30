"""Backend-only configuration."""

import os
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit


def _has_whitespace_or_control(value: str) -> bool:
    return any(
        character.isspace() or unicodedata.category(character) in {"Cc", "Cf"}
        for character in value
    )


def validate_codex_base_url(value: str | None) -> str | None:
    if value is None:
        return None
    message = "NAI_CODEX_BASE_URL must be an HTTPS API base URL of at most 2048 characters"
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 2048
        or _has_whitespace_or_control(value)
        or any(character in value for character in "\\?#")
    ):
        raise ValueError(message)
    try:
        parsed = urlsplit(value)
        valid = (
            parsed.scheme == "https"
            and bool(parsed.hostname)
            and parsed.username is None
            and parsed.password is None
            and not parsed.query
            and not parsed.fragment
        )
        _ = parsed.port  # Validate malformed and out-of-range explicit ports.
    except ValueError:
        raise ValueError(message) from None
    if not valid:
        raise ValueError(message)
    return value


def validate_codex_model(value: str | None) -> str | None:
    if value is None:
        return None
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 200
        or _has_whitespace_or_control(value)
    ):
        raise ValueError(
            "NAI_CODEX_MODEL must be a nonblank identifier of at most 200 characters "
            "without whitespace or control characters"
        )
    return value


@dataclass(frozen=True)
class Settings:
    sqlite_path: Path
    public_origin: str
    tag_search_url: str = "https://sakizuki-danboorusearch.hf.space/api"
    tag_search_key: str | None = None
    novelai_mcp_url: str = "https://www.fsstudy.com.cn/novel-ai-v5"
    novelai_mcp_token: str | None = None
    codex_api_key: str | None = field(default=None, repr=False)
    codex_base_url: str | None = field(default=None, repr=False)
    codex_model: str | None = field(default=None, repr=False)
    gpt_image_api_key: str | None = field(default=None, repr=False)
    gpt_image_base_url: str | None = field(default=None, repr=False)
    gpt_image_model: str = field(default="gpt-image-2.5-flare", repr=False)

    def __post_init__(self) -> None:
        validate_codex_base_url(self.codex_base_url)
        validate_codex_model(self.codex_model)
        validate_codex_base_url(self.gpt_image_base_url)
        validate_codex_model(self.gpt_image_model)

    @property
    def gpt_image_endpoint(self) -> str | None:
        """GPT image calls use their own base, else the advice relay base."""
        return self.gpt_image_base_url or self.codex_base_url

    @classmethod
    def from_env(cls) -> "Settings":
        sqlite_value = os.environ.get("NAI_SQLITE_PATH") or "./var/data/novelai.sqlite3"
        if "://" in sqlite_value:
            raise ValueError("NAI_SQLITE_PATH must be a file path, not a database URL")
        sqlite_path = Path(sqlite_value)
        public_origin = os.environ.get("NAI_PUBLIC_ORIGIN") or "https://localhost:8000"
        parsed_origin = urlsplit(public_origin)
        if (
            parsed_origin.scheme != "https"
            or not parsed_origin.hostname
            or parsed_origin.username
            or parsed_origin.password
            or parsed_origin.path
            or parsed_origin.query
            or parsed_origin.fragment
            or public_origin.endswith("/")
        ):
            raise ValueError("NAI_PUBLIC_ORIGIN must be an exact HTTPS origin")
        tag_search_url = os.environ.get("NAI_DANBOORU_SEARCH_API_URL") or (
            "https://sakizuki-danboorusearch.hf.space/api"
        )
        parsed_search_url = urlsplit(tag_search_url)
        if (
            parsed_search_url.scheme != "https"
            or not parsed_search_url.hostname
            or parsed_search_url.username
            or parsed_search_url.password
            or parsed_search_url.query
            or parsed_search_url.fragment
        ):
            raise ValueError("NAI_DANBOORU_SEARCH_API_URL must be an HTTPS API base URL")
        tag_search_key = os.environ.get("NAI_DANBOORU_SEARCH_API_KEY") or None
        novelai_mcp_url = os.environ.get("NAI_NOVELAI_MCP_URL") or (
            "https://www.fsstudy.com.cn/novel-ai-v5"
        )
        parsed_mcp_url = urlsplit(novelai_mcp_url)
        if (
            parsed_mcp_url.scheme != "https"
            or not parsed_mcp_url.hostname
            or parsed_mcp_url.username
            or parsed_mcp_url.password
            or parsed_mcp_url.query
            or parsed_mcp_url.fragment
        ):
            raise ValueError("NAI_NOVELAI_MCP_URL must be an HTTPS MCP endpoint")
        return cls(
            sqlite_path=sqlite_path,
            public_origin=public_origin,
            tag_search_url=tag_search_url,
            tag_search_key=tag_search_key,
            novelai_mcp_url=novelai_mcp_url,
            novelai_mcp_token=os.environ.get("NAI_NOVELAI_MCP_TOKEN") or None,
            codex_api_key=os.environ.get("NAI_CODEX_API_KEY") or None,
            codex_base_url=os.environ.get("NAI_CODEX_BASE_URL") or None,
            codex_model=os.environ.get("NAI_CODEX_MODEL") or None,
            gpt_image_api_key=os.environ.get("NAI_GPT_IMAGE_API_KEY") or None,
            gpt_image_base_url=os.environ.get("NAI_GPT_IMAGE_BASE_URL") or None,
            gpt_image_model=os.environ.get("NAI_GPT_IMAGE_MODEL") or "gpt-image-2.5-flare",
        )
