"""Trello REST API & Offline Local File Kanban Adapters with Secret Sanitization."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
import httpx
from pydantic import BaseModel, Field

from factory.journal.task_ledger import SecretRedactor


class KanbanCard(BaseModel):
    card_id: str
    feature_id: str
    title: str
    description: str
    column: str
    labels: List[str] = Field(default_factory=list)
    last_modified_by: str = "system"
    comments: List[str] = Field(default_factory=list)


class LocalKanbanAdapter:
    """File-backed Kanban board adapter (default when Trello credentials are not yet set)."""

    def __init__(self, state_file: str | Path = ".factory/local_kanban.json") -> None:
        self.state_file = Path(state_file)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._cards: Dict[str, KanbanCard] = {}
        self._load()

    def _load(self) -> None:
        if self.state_file.exists():
            raw = json.loads(self.state_file.read_text(encoding="utf-8"))
            self._cards = {
                cid: KanbanCard.model_validate(data) for cid, data in raw.items()
            }

    def _save(self) -> None:
        payload = {
            cid: card.model_dump(mode="json") for cid, card in sorted(self._cards.items())
        }
        self.state_file.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    def upsert_card(self, card: KanbanCard) -> KanbanCard:
        card.title = SecretRedactor.sanitize(card.title)
        card.description = SecretRedactor.sanitize(card.description)
        self._cards[card.feature_id] = card
        self._save()
        return card

    def get_card(self, feature_id: str) -> Optional[KanbanCard]:
        return self._cards.get(feature_id)

    def list_cards(self, column: Optional[str] = None) -> List[KanbanCard]:
        cards = list(self._cards.values())
        if column:
            return [c for c in cards if c.column == column]
        return cards

    def add_comment(self, feature_id: str, comment: str) -> None:
        card = self._cards.get(feature_id)
        if not card:
            raise KeyError(f"Card '{feature_id}' not found on Kanban board.")
        card.comments.append(SecretRedactor.sanitize(comment))
        self._save()


class TrelloKanbanAdapter(LocalKanbanAdapter):
    """Live Trello REST API client with automatic local state mirroring and secret redaction."""

    BASE_URL = "https://api.trello.com/1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        token: Optional[str] = None,
        board_id: Optional[str] = None,
        state_file: str | Path = ".factory/local_kanban.json",
    ) -> None:
        super().__init__(state_file=state_file)
        self.api_key = api_key or os.environ.get("TRELLO_API_KEY", "")
        self.token = token or os.environ.get("TRELLO_TOKEN", "")
        self.board_id = board_id or os.environ.get("TRELLO_BOARD_ID", "")

    @property
    def is_live_configured(self) -> bool:
        return bool(
            self.api_key
            and self.token
            and self.board_id
            and "your_trello" not in self.api_key
        )

    def sync_card_to_trello_remote(self, card: KanbanCard) -> Dict[str, str]:
        """Pushes sanitized card state to Trello REST API if credentials are configured."""
        sanitized_card = self.upsert_card(card)
        if not self.is_live_configured:
            return {"mode": "local_mirror", "card_id": sanitized_card.card_id}

        # Explicit 10.0s timeout on external HTTP calls to prevent production hangs
        with httpx.Client(timeout=10.0) as client:
            lists_resp = client.get(
                f"{self.BASE_URL}/boards/{self.board_id}/lists",
                params={"key": self.api_key, "token": self.token},
            )
            lists_resp.raise_for_status()
            board_lists = {lst["name"]: lst["id"] for lst in lists_resp.json()}
            target_list_id = board_lists.get(sanitized_card.column)
            if not target_list_id:
                create_lst = client.post(
                    f"{self.BASE_URL}/boards/{self.board_id}/lists",
                    params={
                        "key": self.api_key,
                        "token": self.token,
                        "name": sanitized_card.column,
                    },
                )
                create_lst.raise_for_status()
                target_list_id = create_lst.json()["id"]

            card_resp = client.post(
                f"{self.BASE_URL}/cards",
                params={
                    "key": self.api_key,
                    "token": self.token,
                    "idList": target_list_id,
                    "name": sanitized_card.title,
                    "desc": sanitized_card.description,
                },
            )
            card_resp.raise_for_status()
            remote_id = card_resp.json()["id"]
            sanitized_card.card_id = remote_id
            self.upsert_card(sanitized_card)
            return {"mode": "trello_remote", "card_id": remote_id}
