import json
from typing import Any, Dict, Optional

import httpx
from pydantic import BaseSettings, Field

from infrahub_client.types import HTTPMethod
from infrahub_client.utils import generate_request_filename


class JSONPlayback(BaseSettings):
    directory: str = Field(default=".", description="Directory to read recorded files from")

    async def async_request(
        self, url: str, method: HTTPMethod, headers: Dict[str, Any], timeout: int, payload: Optional[Dict] = None
    ) -> httpx.Response:
        return self._read_request(url=url, method=method, headers=headers, payload=payload, timeout=timeout)

    def sync_request(
        self, url: str, method: HTTPMethod, headers: Dict[str, Any], timeout: int, payload: Optional[Dict] = None
    ) -> httpx.Response:
        return self._read_request(url=url, method=method, headers=headers, payload=payload, timeout=timeout)

    def _read_request(
        self,
        url: str,
        method: HTTPMethod,
        headers: Dict[str, Any],
        timeout: int,  # pylint: disable=unused-argument
        payload: Optional[Dict] = None,
    ) -> httpx.Response:
        content: Optional[bytes] = None
        if payload:
            content = str(json.dumps(payload)).encode("UTF-8")
        request = httpx.Request(method=method.value, url=url, headers=headers, content=content)

        filename = generate_request_filename(request)
        with open(f"{self.directory}/{filename}.json", "r", encoding="UTF-8") as fobj:
            data = json.load(fobj)

        response = httpx.Response(
            status_code=data["status_code"],
            content=data["response_content"],
            request=request,
        )
        return response

    class Config:
        env_prefix = "INFRAHUB_SDK_PLAYBACK_"
        case_sensitive = False