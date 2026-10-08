"""Backend-only configuration."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Settings:
    sqlite_path: Path
    public_origin: str
    tag_search_url: str = "https://sakizuki-danboorusearch.hf.space/api"
    tag_search_key: str | None = None
    novelai_mcp_url: str = "https://www.fsstudy.com.cn/novel-ai-v5"
    novelai_mcp_token: str | None = None
    codex_api_key: str | None = field(default=None, repr=False)

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
        )
