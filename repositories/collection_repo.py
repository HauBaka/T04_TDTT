from datetime import datetime, timezone
from google.cloud import firestore as fs

from core.database import get_db
from core.exceptions import AppException, NotFoundError
from schemas.collection_schema import ModifyAction


class CollectionRepository:
    def __init__(self):
        self.collection_name = "collections"

    def _get_db(self):
        return get_db()

    async def create_collection(self, uid: str, collection_request: dict) -> dict:
        """Tạo một collection mới cho người dùng."""
        ref = self._get_db().collection(self.collection_name).document()
        timestamp = datetime.now(timezone.utc)

        data = collection_request.copy()
        data["owner_uid"] = uid
        data["created_at"] = timestamp
        data["updated_at"] = timestamp

        # counters (tuỳ bạn có dùng chỗ khác hay không)
        data["liked_count"] = 0
        data["contributor_count"] = 0
        data["place_count"] = 0

        # structure fields theo schema (Hướng A)
        data["collaborators"] = []
        data["places"] = []
        data["tags"] = data.get("tags") or []

        # liked list theo schema bổ sung
        data["liked"] = []

        await ref.set(data)
        snapshot = await ref.get()
        if not snapshot.exists:
            return {}

        collection_data = snapshot.to_dict()
        if collection_data is None:
            return {}

        collection_data["id"] = ref.id
        return collection_data

    async def update_collection(
        self,
        collection_id: str,
        update_data: dict,
        requester_id: str | None = None,
        collaborator_additions: dict[str, dict] | None = None,
    ) -> dict:
        """Cập nhật một collection của người dùng."""
        ref = self._get_db().collection(self.collection_name).document(collection_id)
        
        collaborator_additions = collaborator_additions or {}

        for field in ("collaborators", "places", "tags"):
            for mod in (update_data.get(field) or []):
                if not isinstance(mod, dict):
                    raise AppException(status_code=400, message="Invalid modification payload")
                if not mod.get("target_id") or not mod.get("action"):
                    raise AppException(status_code=400, message="Invalid modification payload")

        base_payload: dict = {}
        for key in ("name", "description", "visibility", "thumbnail_url"):
            if key in update_data and update_data[key] is not None:
                base_payload[key] = update_data[key]

        has_modifications = any(update_data.get(k) for k in ("collaborators", "places", "tags"))

        if has_modifications:
            transaction = self._get_db().transaction()

            @fs.async_transactional
            async def _run(transaction, ref):
                snapshot = await transaction.get(ref)
                if not snapshot.exists:
                    return None

                current = snapshot.to_dict() or {}
                payload = dict(base_payload)
                now = datetime.now(timezone.utc)

                tag_mods = update_data.get("tags") or []
                if tag_mods:
                    current_tags = current.get("tags") or []
                    if not isinstance(current_tags, list):
                        current_tags = []

                    tags_set = set([t for t in current_tags if isinstance(t, str)])
                    for mod in tag_mods:
                        target_id = str(mod.get("target_id", "")).strip()
                        action = mod.get("action")
                        if not target_id:
                            continue

                        if action == ModifyAction.ADD.value:
                            tags_set.add(target_id)
                        elif action == ModifyAction.REMOVE.value:
                            tags_set.discard(target_id)

                    payload["tags"] = list(tags_set)

                place_mods = update_data.get("places") or []
                if place_mods:
                    current_places = current.get("places") or []
                    if not isinstance(current_places, list):
                        current_places = []
                    current_places = [p for p in current_places if isinstance(p, dict)]

                    def _find_place_idx(place_id: str) -> int:
                        for i, p in enumerate(current_places):
                            if p.get("place_id") == place_id:
                                return i
                        return -1

                    for mod in place_mods:
                        place_id = str(mod.get("target_id", "")).strip()
                        action = mod.get("action")
                        if not place_id:
                            continue

                        idx = _find_place_idx(place_id)

                        if action == ModifyAction.ADD.value:
                            if idx == -1:
                                current_places.append(
                                    {
                                        "place_id": place_id,
                                        "added_at": now,
                                        "added_by": requester_id or "",
                                    }
                                )
                        elif action == ModifyAction.REMOVE.value:
                            if idx != -1:
                                current_places.pop(idx)

                    payload["places"] = current_places
                    payload["place_count"] = len(current_places)

                collaborator_mods = update_data.get("collaborators") or []
                if collaborator_mods:
                    current_collabs = current.get("collaborators") or []
                    if not isinstance(current_collabs, list):
                        current_collabs = []
                    current_collabs = [c for c in current_collabs if isinstance(c, dict)]

                    def _find_collab_idx(uid: str) -> int:
                        for i, c in enumerate(current_collabs):
                            if c.get("uid") == uid:
                                return i
                        return -1

                    owner_uid = str(current.get("owner_uid") or "").strip()

                    for mod in collaborator_mods:
                        target_uid = str(mod.get("target_id", "")).strip()
                        action = mod.get("action")
                        if not target_uid:
                            continue

                        if owner_uid and target_uid == owner_uid:
                            continue

                        idx = _find_collab_idx(target_uid)

                        if action == ModifyAction.ADD.value:
                            if idx == -1:
                                collab_obj = collaborator_additions.get(target_uid)
                                if not isinstance(collab_obj, dict):
                                    raise AppException(
                                        status_code=400,
                                        message=f"Missing collaborator data for uid={target_uid}",
                                    )
                                current_collabs.append(collab_obj)

                        elif action == ModifyAction.REMOVE.value:
                            if idx != -1:
                                current_collabs.pop(idx)

                    payload["collaborators"] = current_collabs
                    payload["contributor_count"] = len(current_collabs)

                payload["updated_at"] = now
                transaction.update(ref, payload)
                return payload

            result = await _run(transaction, ref)
            if result is None:
                raise NotFoundError("Collection not found")

        else:
            snapshot = await ref.get()
            if not snapshot.exists:
                raise NotFoundError("Collection not found")

            if not base_payload:
                data = snapshot.to_dict() or {}
                data["id"] = ref.id
                return data

            base_payload["updated_at"] = datetime.now(timezone.utc)
            await ref.update(base_payload)

        updated = (await ref.get()).to_dict() or {}
        updated["id"] = ref.id
        return updated

    async def delete_collection(self, collection_id: str) -> bool:
        """Xóa một collection của người dùng."""
        ref = self._get_db().collection(self.collection_name).document(collection_id)
        snapshot = await ref.get()
        if not snapshot.exists:
            return False

        await ref.delete()
        return True

    async def get_collection(self, collection_id: str) -> dict:
        """Lấy thông tin của một collection cụ thể."""
        ref = self._get_db().collection(self.collection_name).document(collection_id)
        snapshot = await ref.get()
        if not snapshot.exists:
            return {}

        collection_data = snapshot.to_dict() or {}
        collection_data["id"] = ref.id
        return collection_data


collection_repo = CollectionRepository()