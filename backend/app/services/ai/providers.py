from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol


class NarrativeProvider(Protocol):
    def rewrite_json(
        self,
        *,
        system_prompt: str,
        facts: dict[str, Any],
    ) -> dict[str, Any]:
        """Return a JSON-compatible rewritten report payload."""


@dataclass(frozen=True)
class OpenAICompatibleNarrativeProvider:
    api_key: str
    base_url: str
    model: str
    timeout_seconds: int = 45

    def rewrite_json(
        self,
        *,
        system_prompt: str,
        facts: dict[str, Any],
    ) -> dict[str, Any]:
        request_body = {
            "model": self.model,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        "Rewrite the report sections as JSON. Return exactly these keys: "
                        "title, dataset_overview, executive_summary, key_findings, risks, "
                        "opportunities, recommendations, data_quality_notes. Preserve list "
                        "lengths for every list field. Here are the deterministic facts:\n"
                        + json.dumps(facts, ensure_ascii=True, sort_keys=True)
                    ),
                },
            ],
        }
        payload = json.dumps(request_body).encode("utf-8")
        request = urllib.request.Request(
            self.base_url,
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"AI provider returned HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"AI provider request failed: {exc}") from exc

        parsed = json.loads(response_body)
        content = parsed["choices"][0]["message"]["content"]
        rewritten = json.loads(content)
        if not isinstance(rewritten, dict):
            raise ValueError("AI provider returned JSON, but the top-level value was not an object.")
        return rewritten
