from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from time import perf_counter
from typing import Any

from loguru import logger

from externals.GroqLLM import groq_client
from schemas.chatbot_schema import (
    ChatAskRequest,
    ChatAskResponse,
    ChatCitation,
    ChatContextRequest,
    ChatIntent,
    ChatRecommendationItem,
)
from schemas.discover_schema import DiscoverRequest, DiscoverHotel
from schemas.response_schema import ResponseSchema
from externals.VietMapAPI import vietmap_api
from repositories.hotel_repo import hotel_repo
from services.hotel_ranking_service import hotel_ranking_service
from services.semantic_encoder import semantic_text_encoder
from schemas.trip_context_schema import TravelStyle
from services.conversation_service import conversation_service
from schemas.conversation_schema import SendMessageRequest


@dataclass
class RetrievedHotel:
    hotel: DiscoverHotel
    score: float
    snippet: str
    matched_query: str


@dataclass
class RouteDecision:
    intent: ChatIntent
    use_lodging_rag: bool
    requires_more_info: bool
    missing_fields: list[str]
    clarification_question: str | None = None

class ChatbotService:
    CONTEXT_ENRICH_MIN_CONFIDENCE = 0.55
    CONTEXT_ENRICH_LLM_MIN_CONFIDENCE = 0.35
    GEO_CACHE_TTL_SECONDS = 1800 
    GEO_CACHE_MAX_ITEMS = 500  
    MAX_GLOBAL_POOL = 180 
    GLOBAL_POOL_CACHE_TTL_SECONDS = 300  
    NEARBY_POOL_CACHE_TTL_SECONDS = 180  
    NEARBY_POOL_CACHE_MAX_ITEMS = 500  
    LLM_ROUTER_TIMEOUT_SECONDS = 3.0 

    RECOMMENDATION_KEYWORDS = {
        "goi y",
        "gợi ý",
        "khach san",
        "khách sạn",
        "hotel",
        "resort",
        "o dau",
        "ở đâu",
        "du lich",
        "du lịch",
        "dia diem",
        "địa điểm",
    }

    COMPARE_KEYWORDS = {
        "so sanh",
        "so sánh",
        "hon",
        "hơn",
        "nen chon",
        "nên chọn",
    }

    INFO_KEYWORDS = {
        "thoi tiet",
        "thời tiết",
        "gia",
        "giá",
        "tien ich",
        "tiện ích",
        "di chuyen",
        "di chuyển",
        "gan",
        "gần",
    }

    CASUAL_KEYWORDS = {
        "chao",
        "chào",
        "hello",
        "hi",
        "hey",
        "xin chao",
        "xin chào",
        "good morning",
        "good evening",
        "ban ten gi",
        "bạn tên gì",
        "cam on",
        "cảm ơn",
    }

    LODGING_KEYWORDS = {
        "du lich",
        "du lịch",
        "khach san",
        "khách sạn",
        "hotel",
        "resort",
        "check in",
        "check-in",
        "nghi duong",
        "nghỉ dưỡng",
        "dat phong",
        "đặt phòng",
        "budget",
        "luu tru",
        "lưu trú",
        "homestay",
        "hostel",
        "villa",
    }

    # Các từ khóa cảnh báo cho weather/transport/itinerary — nếu xuất hiện, không nên chuyển sang RAG lưu trú
    WEATHER_KEYWORDS = {
        "thoi tiet",
        "thời tiết",
        "mua",
        "nắng",
        "trời",
        "dự báo",
        "dự báo thời tiết",
    }

    TRANSPORT_KEYWORDS = {
        "di chuyen",
        "di chuyển",
        "di lai",
        "vé",
        "tau",
        "tàu",
        "xe",
        "may bay",
        "máy bay",
        "diem den",
        "điểm đến",
        "lịch trình",
        "tham quan",
    }

    NON_LODGING_TOPIC_KEYWORDS = WEATHER_KEYWORDS.union(TRANSPORT_KEYWORDS)

    AMENITY_SYNONYMS: dict[str, tuple[str, ...]] = {
        "ho boi": ("hồ bơi", "ho boi", "swimming pool", "pool", "be boi", "bể bơi"),
        "an sang": ("ăn sáng", "an sang", "breakfast", "bao gom an sang", "buffet sang"),
        "wifi": ("wifi", "wi-fi", "internet", "mang", "mạng"),
        "gym": ("gym", "phòng gym", "phong gym", "fitness", "phòng tập", "phong tap"),
        "cho dau xe": ("chỗ đậu xe", "cho dau xe", "parking", "bãi đỗ", "bai do"),
        "spa": ("spa", "massage", "xong hoi", "xông hơi", "sauna"),
        "gan trung tam": ("gần trung tâm", "gan trung tam", "center", "trung tam"),
        "free huy": ("hủy miễn phí", "huy mien phi", "free cancellation"),
        "tam bien": ("gần biển", "gan bien", "sea view", "bãi biển", "bai bien"),
        "view dep": ("view đẹp", "view dep", "view đẹp", "ban công", "ban cong"),
    }

    INTENT_PROTOTYPES: dict[ChatIntent, tuple[str, ...]] = {
        ChatIntent.RECOMMENDATION: (
            "goi y noi luu tru phu hop ngan sach",
            "de xuat khach san tot cho gia dinh",
            "suggest best hotel options",
        ),
        ChatIntent.COMPARISON: (
            "so sanh hai khach san",
            "khach san nao tot hon",
            "compare hotel options",
        ),
        ChatIntent.INFORMATION: (
            "thong tin gia phong tien ich vi tri",
            "hoi ve dieu kien luu tru",
            "ask for lodging information",
        ),
        ChatIntent.CASUAL: (
            "chao hoi tro chuyen chung",
            "noi chuyen thong thuong",
            "general conversation",
        ),
    }

    def __init__(self):
        self._geo_cache: dict[str, tuple[datetime, str | None, Any]] = {}
        self._global_hotels_cache: tuple[datetime, int, list] | None = None
        self._nearby_hotels_cache: dict[str, tuple[datetime, list]] = {}
        self._groq_last_health_check: datetime | None = None
        self._groq_is_available: bool | None = None
        self._groq_health_ttl_seconds = 45
        self._routing_decision_cache: dict[str, tuple[datetime, RouteDecision, list[str]]] = {}  # Cache routing decisions 5min
        self._routing_cache_ttl_seconds = 300

    def detect_intent(self, message: str) -> ChatIntent:
        """Nhận diện ý định của người dùng một cách nhanh chóng bằng cách quét các từ khóa có sẵn."""
        normalized = self._normalize_space(message).lower()

        if any(word in normalized for word in self.COMPARE_KEYWORDS):
            return ChatIntent.COMPARISON

        if any(word in normalized for word in self.RECOMMENDATION_KEYWORDS):
            return ChatIntent.RECOMMENDATION

        if any(word in normalized for word in self.INFO_KEYWORDS):
            return ChatIntent.INFORMATION

        return ChatIntent.CASUAL

    def _should_expand_search(self, message: str, context: ChatContextRequest | None = None) -> bool:
        """Đánh giá xem câu hỏi có chứa các yếu tố phức tạp đòi hỏi phải mở rộng từ khóa tìm kiếm hay không."""
        normalized = self._normalize_space(message).lower()
        complexity_keywords = (
            "so sánh",
            "compare",
            "khác nhau",
            "nên chọn",
            "rẻ",
            "đắt",
            "gần",
            "gia đình",
            "trẻ em",
            "hồ bơi",
            "bữa sáng",
            "view",
            "phòng",
            "khách sạn",
            "lưu trú",
        )
        if len(normalized) > 60:
            return True
        if context and (context.address or context.ref_id or context.gps):
            return True
        return any(keyword in normalized for keyword in complexity_keywords)

    def _save_chat_logs(self, requester_uid: str | None, chatbot_conv_id: str | None, user_message: str, bot_response: str) -> None:
        """Lưu lại tin nhắn ngầm vào conversation service để không block API."""
        if not requester_uid or not chatbot_conv_id:
            return

        async def _save():
            try:
                await conversation_service.send_message_to_conversation(
                    chatbot_conv_id, requester_uid, SendMessageRequest(content=user_message)
                )
                await conversation_service.send_message_to_conversation(
                    chatbot_conv_id, "chatbot", SendMessageRequest(content=bot_response)
                )
            except Exception as e:
                logger.error(f"Failed to save chat logs: {e}")

        asyncio.create_task(_save())

    async def ask(self, requester_uid: str | None, ask_request: ChatAskRequest) -> ResponseSchema[ChatAskResponse]:
        """Điểm vào chính của Chatbot. Nhận yêu cầu, định tuyến, truy xuất, xếp hạng và sinh câu trả lời."""
        timings: dict[str, float] = {}

        # Lấy lịch sử từ ConversationService nếu có đăng nhập
        chatbot_conv_id = None
        total_start = perf_counter()
        if requester_uid:
            try:
                from services.conversation_service import conversation_service
                conv_res = await conversation_service.get_or_create_default_chatbot_conversation(requester_uid)
                if conv_res.data:
                    chatbot_conv_id = conv_res.data.id
                    msgs_res = await conversation_service.get_recent_messages(chatbot_conv_id, limit=20)
                    if msgs_res.data:
                        # Ghi đè history từ DB (từ cũ đến mới) kèm tiền tố User/Bot
                        formatted_history = []
                        for msg in reversed(msgs_res.data):
                            content = msg.content if hasattr(msg, "content") else msg.get("content", "")
                            sender = msg.sender_uid if hasattr(msg, "sender_uid") else msg.get("sender_uid", "")
                            prefix = "User" if sender == requester_uid else "Bot"
                            formatted_history.append(f"{prefix}: {content}")
                        ask_request.history = formatted_history
            except Exception as e:
                logger.warning(f"Failed to fetch chatbot conversation history: {e}")

        # Đo thời gian từng bước

        stage_start = perf_counter()
        user_message = self._normalize_space(ask_request.message)
        context = ask_request.context or ChatContextRequest()
        timings["normalize"] = perf_counter() - stage_start

        stage_start = perf_counter()

        # Trích xuất thông tin từ tin nhắn và lịch sử trò chuyện
        context, context_confidence = await self._hydrate_context_from_text(
            context=context,
            message=user_message,
            history=ask_request.history,
            allow_llm_enrich=True,
        )
        timings["hydrate_text"] = perf_counter() - stage_start

        # Luôn dùng LLM router và expand queries để tối ưu chất lượng
        stage_start = perf_counter()
        llm_task = asyncio.create_task(
            self._analyze_intent_and_expand(user_message, context, ask_request.history, router_needed=True, expand_needed=True)
        )

        # Lấy thông tin địa lý
        geo_stage_start = perf_counter()
        context = await self._hydrate_geo_context(context)
        timings["hydrate_geo"] = perf_counter() - geo_stage_start

        # Lấy danh sách khách sạn
        pool_stage_start = perf_counter()
        pool_task = asyncio.create_task(self._build_hotel_pool(context))

        # Lấy quyết định định tuyến và mở rộng câu hỏi
        try:
            # Ép timeout cứng cho LLM Router để giữ tổng request dưới 10s
            decision_result, query_variants = await asyncio.wait_for(llm_task, timeout=self.LLM_ROUTER_TIMEOUT_SECONDS)
            decision = decision_result if decision_result is not None else self._heuristic_route_decision(user_message, context)
        except asyncio.TimeoutError:
            logger.warning(f"LLM Router timed out after {self.LLM_ROUTER_TIMEOUT_SECONDS}s. Fallback to heuristic router.")
            decision = self._heuristic_route_decision(user_message, context)
            query_variants = [user_message]
        except Exception as e:
            logger.warning(f"LLM router error: {e}. Fallback to heuristic.")
            decision = self._heuristic_route_decision(user_message, context)
            query_variants = [user_message]

        timings["route_and_expand"] = perf_counter() - stage_start

        # Nếu không sử dụng RAG, trả lời bằng LLM
        if not decision.use_lodging_rag:
            pool_task.cancel()
            stage_start = perf_counter()
            general_answer, used_fallback = await self._build_general_answer(user_message, ask_request.history)
            general_answer = self._embed_clarification_in_answer(
                general_answer,
                decision.clarification_question,
                decision.requires_more_info,
            )
            timings["general_answer"] = perf_counter() - stage_start
            timings["total"] = perf_counter() - total_start
            self._log_stage_timings(timings)
            self._save_chat_logs(requester_uid, chatbot_conv_id, user_message, general_answer)
            return ResponseSchema(
                data=ChatAskResponse(
                    intent=decision.intent,
                    message=user_message,
                    answer=general_answer,
                    recommendations=[],
                    citations=[],
                    missing_fields=decision.missing_fields,
                    requires_more_info=decision.requires_more_info,
                    clarification_question=decision.clarification_question,
                )
            )

        intent = decision.intent

        # Nếu không phải là tìm kiếm khách sạn thì trả lời bằng LLM
        if intent == ChatIntent.CASUAL:
            pool_task.cancel()
            timings["total"] = perf_counter() - total_start
            self._log_stage_timings(timings)
            casual_answer = self._embed_clarification_in_answer(
                self._build_casual_reply(user_message),
                decision.clarification_question,
                False,
            )
            self._save_chat_logs(requester_uid, chatbot_conv_id, user_message, casual_answer)
            return ResponseSchema(
                data=ChatAskResponse(
                    intent=intent,
                    message=user_message,
                    answer=casual_answer,
                    recommendations=[],
                    citations=[],
                    missing_fields=decision.missing_fields,
                    requires_more_info=False,
                    clarification_question=decision.clarification_question,
                )
            )

        # Check thông tin bị thiếu
        missing_fields = decision.missing_fields
        requires_more_info = decision.requires_more_info

        # Check thông tin bị thiếu
        if decision.use_lodging_rag and not context.address and context_confidence < self.CONTEXT_ENRICH_MIN_CONFIDENCE:
            missing_fields = sorted(set([*missing_fields, "address"]))
            requires_more_info = True
        
        if decision.requires_more_info and decision.clarification_question and not context.address:
            requires_more_info = True

        # Lấy danh sách khách sạn
        try:
            pool_hotels = await pool_task
        except asyncio.CancelledError:
            pool_hotels = []
        timings["build_pool"] = perf_counter() - pool_stage_start

        stage_start = perf_counter()
        retrieved = self._retrieve_relevant_hotels(
            message=user_message,
            query_variants=query_variants,
            context=context,
            hotels=pool_hotels,
            limit=max(20, context.max_ranked_hotels * 6),
        )
        timings["retrieve"] = perf_counter() - stage_start

        # Nếu không tìm thấy khách sạn thì nới lỏng điều kiện để tìm lại
        if not retrieved and (context.min_rating is not None or context.required_amenities):
            stage_start = perf_counter()
            relaxed_context = self._build_relaxed_context_for_fallback(context)
            retrieved = self._retrieve_relevant_hotels(
                message=user_message,
                query_variants=query_variants,
                context=relaxed_context,
                hotels=pool_hotels,
                limit=max(20, context.max_ranked_hotels * 6),
            )
            timings["retrieve_relaxed"] = perf_counter() - stage_start
            if retrieved:
                requires_more_info = True
                missing_fields = sorted(set([*missing_fields, "constraints"]))

        # Xếp hạng khách sạn
        stage_start = perf_counter()
        ranked_hotels = await self._rerank_with_internal_ranker(context, requester_uid, retrieved)
        timings["rerank"] = perf_counter() - stage_start

        selected_hotels = ranked_hotels[: context.max_ranked_hotels]
        recommendations = [self._to_recommendation_item(item) for item in selected_hotels]
        citations = [self._to_citation(item, retrieved) for item in selected_hotels]

        stage_start = perf_counter()
        answer, used_fallback = await self._build_answer(
            message=user_message,
            intent=intent,
            context=context,
            recommendations=recommendations,
            history=ask_request.history,
            requires_more_info=requires_more_info,
        )
        answer = self._embed_clarification_in_answer(answer, decision.clarification_question, requires_more_info)
        timings["answer"] = perf_counter() - stage_start

        response = ChatAskResponse(
            intent=intent,
            message=user_message,
            answer=answer,
            recommendations=recommendations,
            citations=citations,
            requires_more_info=requires_more_info,
            missing_fields=missing_fields,
            clarification_question=decision.clarification_question,
        )
        timings["total"] = perf_counter() - total_start
        self._log_stage_timings(timings)
        self._save_chat_logs(requester_uid, chatbot_conv_id, user_message, answer)
        return ResponseSchema(data=response)

    async def _hydrate_context_from_text(
        self,
        context: ChatContextRequest,
        message: str,
        history: list[str],
        allow_llm_enrich: bool = False,
    ) -> tuple[ChatContextRequest, float]:
        """Bóc tách ngữ cảnh (địa điểm, giá cả, số người, tiện ích) từ tin nhắn bằng Regex. Nếu độ tự tin quá thấp, sẽ mượn LLM để trích xuất lại."""
        normalized = self._normalize_space(message).lower()
        score = 0.0

        self._inherit_context_from_history(context, history, normalized)
        if context.address or context.ref_id or context.gps:
            score += 0.10
        if context.min_price != 300000 or context.max_price != 3000000:
            score += 0.06
        if context.min_rating is not None or context.required_amenities:
            score += 0.06
        if context.check_in is not None or context.check_out is not None:
            score += 0.06

        inferred_address = self._extract_destination(message, normalized)
        if inferred_address and not context.address:
            context.address = inferred_address
            score += 0.35

        inferred_budget = self._extract_budget_range(normalized)
        if inferred_budget is not None:
            min_price, max_price = inferred_budget
            context.min_price = min_price
            context.max_price = max_price
            score += 0.25

        inferred_rating = self._extract_min_rating(normalized)
        if inferred_rating is not None and context.min_rating is None:
            context.min_rating = inferred_rating
            score += 0.20

        inferred_amenities = self._extract_required_amenities(normalized)
        if inferred_amenities and not context.required_amenities:
            context.required_amenities = inferred_amenities
            score += min(0.16, 0.08 * len(inferred_amenities))

        inferred_adults, inferred_children = self._extract_party(normalized)
        if inferred_adults is not None:
            context.adults = max(1, min(inferred_adults, 10))
            score += 0.07
        if inferred_children is not None and not context.children:
            context.children = inferred_children
            score += 0.05

        inferred_check_in, inferred_check_out = self._extract_dates(normalized)
        if inferred_check_in and context.check_in is None:
            context.check_in = inferred_check_in
            score += 0.12
        if inferred_check_out and context.check_out is None:
            context.check_out = inferred_check_out
            score += 0.08

        inferred_trip_style = self._extract_trip_style(normalized)
        if inferred_trip_style is not None and context.trip_style == TravelStyle.EXPLORE:
            context.trip_style = inferred_trip_style
            score += 0.08

        confidence = min(0.95, score)

        if allow_llm_enrich and self._should_enrich_context_with_llm(confidence, normalized, context):
            llm_context, llm_confidence = await self._extract_context_with_groq(message, history)
            if llm_context is not None:
                self._merge_inferred_context(context, llm_context)
                extracted_fields = self._count_context_fields(llm_context)
                blended = (0.7 * confidence) + (0.3 * llm_confidence)
                confidence = min(0.98, blended + min(0.12, extracted_fields * 0.02))

        return context, confidence

    def _inherit_context_from_history(self, context: ChatContextRequest, history: list[str], normalized_message: str) -> None:
        """Kế thừa ngữ cảnh từ hội thoại gần nhất để xử lý các câu hỏi mơ hồ kiểu 'ở đó', 'đó', 'chỗ nào'."""
        if not history:
            return

        vague_references = ("đó", "do", "ở đó", "chỗ đó", "khu đó", "nơi đó", "ở đấy", "vậy", "thế")
        has_vague_reference = any(token in normalized_message for token in vague_references)
        if not has_vague_reference and not self._should_expand_search(normalized_message, context):
            return

        recent_items = [self._normalize_space(item) for item in history if item and self._normalize_space(item)]
        for item in reversed(recent_items[-8:]):
            lower_item = item.lower()
            if not context.address:
                candidate_address = self._extract_destination(item, lower_item)
                if candidate_address:
                    context.address = candidate_address
                    break

        if not context.required_amenities:
            for item in reversed(recent_items[-6:]):
                lower_item = item.lower()
                inferred_amenities = self._extract_required_amenities(lower_item)
                if inferred_amenities:
                    context.required_amenities = inferred_amenities[:3]
                    break

        if context.min_rating is None:
            for item in reversed(recent_items[-6:]):
                lower_item = item.lower()
                rating = self._extract_min_rating(lower_item)
                if rating is not None:
                    context.min_rating = rating
                    break

        if context.check_in is None or context.check_out is None:
            for item in reversed(recent_items[-6:]):
                lower_item = item.lower()
                check_in, check_out = self._extract_dates(lower_item)
                if check_in or check_out:
                    if context.check_in is None and check_in is not None:
                        context.check_in = check_in
                    if context.check_out is None and check_out is not None:
                        context.check_out = check_out
                    break

    async def _hydrate_geo_context(self, context: ChatContextRequest) -> ChatContextRequest:
        """Chuyển đổi địa chỉ thành tọa độ GPS thông qua VietMap API một cách bất đồng bộ và lưu cache để tái sử dụng."""
        if context.gps is not None and context.ref_id:
            return context

        now = datetime.now(timezone.utc)

        if context.address:
            cache_key = self._normalize_space(context.address).lower()
            cached = self._geo_cache.get(cache_key)
            if cached is not None:
                cached_at, cached_ref_id, cached_gps = cached
                if (now - cached_at).total_seconds() <= self.GEO_CACHE_TTL_SECONDS:
                    if context.ref_id is None and cached_ref_id:
                        context.ref_id = cached_ref_id
                    if context.gps is None and cached_gps is not None:
                        context.gps = cached_gps
                    return context

            try:
                autocomplete = await vietmap_api.autocomplete(context.address, context.gps)
                if autocomplete and autocomplete.data:
                    place = autocomplete.data[0]
                    if context.ref_id is None and getattr(place, "ref_id", None):
                        context.ref_id = place.ref_id

                    if context.gps is None and context.ref_id:
                        detail = await vietmap_api.get_place_details(context.ref_id)
                        if detail and detail.result and detail.result.gps_coordinates:
                            context.gps = detail.result.gps_coordinates

                    self._geo_cache[cache_key] = (now, context.ref_id, context.gps)
                    if len(self._geo_cache) > self.GEO_CACHE_MAX_ITEMS:
                        overflow = len(self._geo_cache) - self.GEO_CACHE_MAX_ITEMS
                        for key in list(self._geo_cache.keys())[:overflow]:
                            self._geo_cache.pop(key, None)
            except Exception as exc:
                logger.warning(f"Geo hydration failed for chatbot context: {str(exc)}")

        if context.gps is None and context.ref_id:
            try:
                detail = await vietmap_api.get_place_details(context.ref_id)
                if detail and detail.result and detail.result.gps_coordinates:
                    context.gps = detail.result.gps_coordinates
            except Exception as exc:
                logger.warning(f"GPS resolve by ref_id failed: {str(exc)}")

        return context

    def _count_context_fields(self, context: ChatContextRequest) -> int:
        """Đếm số lượng trường thông tin ngữ cảnh đã trích xuất thành công để tính toán điểm cộng độ tin cậy (Bonus Confidence)."""
        count = 0
        if context.address:
            count += 1
        if context.min_price != 300000 or context.max_price != 3000000:
            count += 1
        if context.min_rating is not None:
            count += 1
        if context.required_amenities:
            count += 1
        if context.adults != 2:
            count += 1
        if context.children:
            count += 1
        if context.check_in is not None:
            count += 1
        if context.check_out is not None:
            count += 1
        if context.trip_style != TravelStyle.EXPLORE:
            count += 1
        return count

    def _build_relaxed_context_for_fallback(self, context: ChatContextRequest) -> ChatContextRequest:
        """Tự động nới lỏng các tiêu chí tìm kiếm (giảm sao, bỏ bớt tiện ích bắt buộc) nếu lần truy xuất ban đầu quá khắt khe và không ra kết quả nào."""
        relaxed = context.model_copy(deep=True)
        if relaxed.min_rating is not None:
            relaxed.min_rating = max(0.0, relaxed.min_rating - 0.5)
        if len(relaxed.required_amenities) >= 2:
            relaxed.required_amenities = relaxed.required_amenities[:1]
        return relaxed

    def _log_stage_timings(self, timings: dict[str, float]) -> None:
        """Ghi nhận (Log) lại độ trễ của từng bước thực thi để theo dõi, đo lường và phát hiện các điểm nghẽn hiệu năng (Bottlenecks) trong thực tế."""
        metrics = ", ".join(f"{name}={value:.3f}s" for name, value in timings.items())
        logger.info(f"Chatbot latency | {metrics}")

    def _can_use_groq(self) -> bool:
        """Kiểm tra nhanh xem Groq LLM có sẵn sàng không. Kết quả được cache lại trong vài giây để tránh nghẽn timeout."""
        now = datetime.now(timezone.utc)
        if self._groq_last_health_check is not None and self._groq_is_available is not None:
            elapsed = (now - self._groq_last_health_check).total_seconds()
            if elapsed <= self._groq_health_ttl_seconds:
                return self._groq_is_available

        is_available = False
        try:
            # Kiểm tra xem groq_client đã được khởi tạo
            is_available = groq_client is not None
        except OSError:
            is_available = False

        self._groq_is_available = is_available
        self._groq_last_health_check = now
        return is_available

    def _should_enrich_context_with_llm(
        self,
        confidence: float,
        normalized_message: str,
        context: ChatContextRequest,
    ) -> bool:
        """Chỉ gọi LLM khi câu hỏi còn mơ hồ và thật sự liên quan đến lưu trú."""
        if confidence >= self.CONTEXT_ENRICH_MIN_CONFIDENCE:
            return False
        if not self._can_use_groq():
            return False
        if confidence >= 0.40:
            return False

        has_explicit_context = any(
            [
                context.address,
                context.min_rating is not None,
                context.required_amenities,
                context.check_in is not None,
                context.check_out is not None,
            ]
        )
        if has_explicit_context:
            return False

        return self._is_lodging_related(normalized_message, context) or confidence < self.CONTEXT_ENRICH_LLM_MIN_CONFIDENCE

    async def _extract_context_with_groq(self, message: str, history: list[str]) -> tuple[ChatContextRequest | None, float]:
        """Sử dụng Groq LLM để đọc hiểu tin nhắn và trích xuất ra các trường ngữ cảnh (địa chỉ, giá, số người) có cấu trúc chuẩn JSON."""
        if not self._can_use_groq():
            return None, 0.0

        prompt = (
            "Trả về ĐÚNG MỘT JSON object với các key: address, min_price, max_price, min_rating, required_amenities, adults, children, check_in, check_out, trip_style, confidence.\\n"
            "- address: string hoặc null.\\n"
            "- min_price/max_price: số VND hoặc null.\\n"
            "- min_rating: số từ 0 đến 5 hoặc null.\\n"
            "- required_amenities: list string tiện ích cần có hoặc [].\\n"
            "- adults: integer 1..10 hoặc null.\\n"
            "- children: list tuổi 1..17 hoặc null.\\n"
            "- check_in/check_out: ngày dạng YYYY-MM-DD hoặc null.\\n"
            "- trip_style: một trong [nghi_duong, gia_dinh, cong_tac, kham_pha, lang_man, sang_trong, tiet_kiem] hoặc null.\\n"
            "- confidence: số từ 0 đến 1.\\n"
            "Không bịa thông tin nếu không chắc. Chỉ trả JSON, không markdown.\\n\\n"
            f"Lịch sử hội thoại gần đây: {self._history_text(history)}\\n"
            f"Tin nhắn người dùng: {message}"
        )

        try:
            raw = await asyncio.to_thread(groq_client.generate_content, prompt)
            parsed: dict[str, Any] = json.loads(raw)
        except Exception as exc:
            logger.warning(f"LLM context extraction failed: {str(exc)}")
            return None, 0.0

        candidate = ChatContextRequest()

        address = parsed.get("address")
        if isinstance(address, str) and self._normalize_space(address):
            candidate.address = self._normalize_space(address)

        min_price = parsed.get("min_price")
        max_price = parsed.get("max_price")
        if isinstance(min_price, (int, float)) and isinstance(max_price, (int, float)):
            candidate.min_price = max(0, int(min(min_price, max_price)))
            candidate.max_price = max(candidate.min_price, int(max(min_price, max_price)))

        min_rating = parsed.get("min_rating")
        if isinstance(min_rating, (int, float)):
            candidate.min_rating = max(0.0, min(5.0, float(min_rating)))

        required_amenities = parsed.get("required_amenities")
        if isinstance(required_amenities, list):
            amenity_values = [self._normalize_amenity(str(item)) for item in required_amenities if str(item).strip()]
            candidate.required_amenities = [item for item in amenity_values if item]

        adults = parsed.get("adults")
        if isinstance(adults, (int, float)):
            candidate.adults = max(1, min(int(adults), 10))

        children = parsed.get("children")
        if isinstance(children, list):
            normalized_children = [int(age) for age in children if isinstance(age, (int, float))]
            candidate.children = self._sanitize_children(normalized_children)

        check_in_raw = parsed.get("check_in")
        check_out_raw = parsed.get("check_out")
        check_in = self._parse_iso_date(check_in_raw)
        check_out = self._parse_iso_date(check_out_raw)
        if check_in is not None:
            candidate.check_in = check_in
        if check_out is not None:
            candidate.check_out = check_out

        trip_style_raw = parsed.get("trip_style")
        if isinstance(trip_style_raw, str):
            style = self._map_trip_style(trip_style_raw)
            if style is not None:
                candidate.trip_style = style

        confidence_raw = parsed.get("confidence", 0.0)
        try:
            confidence = float(confidence_raw)
        except (TypeError, ValueError):
            confidence = 0.0

        return candidate, max(0.0, min(1.0, confidence))

    def _merge_inferred_context(self, target: ChatContextRequest, source: ChatContextRequest) -> None:
        """Hợp nhất ngữ cảnh do AI/Regex vừa suy luận ra vào trong ngữ cảnh cũ, bảo đảm không ghi đè những dữ liệu mà người dùng đã thiết lập từ trước."""
        if source.address and not target.address:
            target.address = source.address

        if source.min_price > 0 and source.max_price >= source.min_price:
            if target.min_price == 300000 and target.max_price == 3000000:
                target.min_price = source.min_price
                target.max_price = source.max_price

        if source.min_rating is not None and target.min_rating is None:
            target.min_rating = source.min_rating

        if source.required_amenities and not target.required_amenities:
            target.required_amenities = source.required_amenities

        if source.adults and target.adults == 2:
            target.adults = source.adults

        if source.children and not target.children:
            target.children = source.children

        if source.check_in and target.check_in is None:
            target.check_in = source.check_in
        if source.check_out and target.check_out is None:
            target.check_out = source.check_out

        if source.trip_style != TravelStyle.EXPLORE and target.trip_style == TravelStyle.EXPLORE:
            target.trip_style = source.trip_style

    def _extract_destination(self, original_message: str, normalized_message: str) -> str | None:
        """Trích xuất tên địa điểm du lịch phổ biến (ví dụ: Đà Nẵng, Phú Quốc) từ tin nhắn của người dùng dựa trên bộ Regex."""
        city_aliases = {
            "ha noi": "Hà Nội",
            "hà nội": "Hà Nội",
            "ho chi minh": "TP. Hồ Chí Minh",
            "hồ chí minh": "TP. Hồ Chí Minh",
            "sai gon": "TP. Hồ Chí Minh",
            "sài gòn": "TP. Hồ Chí Minh",
            "da nang": "Đà Nẵng",
            "đà nẵng": "Đà Nẵng",
            "nha trang": "Nha Trang",
            "da lat": "Đà Lạt",
            "đà lạt": "Đà Lạt",
            "phu quoc": "Phú Quốc",
            "phú quốc": "Phú Quốc",
            "hoi an": "Hội An",
            "hội an": "Hội An",
            "ha long": "Hạ Long",
            "hạ long": "Hạ Long",
            "vung tau": "Vũng Tàu",
            "vũng tàu": "Vũng Tàu",
            "quy nhon": "Quy Nhơn",
            "quy nhơn": "Quy Nhơn",
        }
        for alias, canonical in city_aliases.items():
            if alias in normalized_message:
                return canonical

        match = re.search(r"(?:o|ở|tai|tại|khu\s*vuc|khu\s*vực|gan|gần)\s+([A-Za-zÀ-ỹ0-9\s\-]{3,50})", original_message, flags=re.IGNORECASE)
        if not match:
            return None

        location = self._normalize_space(match.group(1))
        location = re.split(r"[,.;!?]|\b(gia|giá|tu|từ|den|đến|check|ngay|ngày)\b", location, maxsplit=1, flags=re.IGNORECASE)[0].strip()
        return location if len(location) >= 3 else None

    def _extract_budget_range(self, normalized_message: str) -> tuple[int, int] | None:
        """Trích xuất yêu cầu về khoảng giá (ngân sách) từ văn bản, hỗ trợ các định dạng như '1tr-2tr', 'dưới 1.5 triệu', 'trên 200k'."""
        if not self._has_money_signal(normalized_message):
            return None

        money_pattern = r"([0-9][0-9.,]*\s*(?:tr|triệu|trieu|k|nghìn|nghin|ngàn|ngan|vnd|đ))"
        number_pattern = r"([0-9][0-9.,]*)"

        # cả hai đều có đơn vị (từ 1tr đến 2tr)
        full_range_patterns = [
            rf"(?:tu|từ)\s*{money_pattern}\s*(?:den|đến|toi|tới|-)\s*{money_pattern}",
            rf"{money_pattern}\s*(?:-|–|~|to|den|đến)\s*{money_pattern}",
        ]
        for pattern in full_range_patterns:
            match = re.search(pattern, normalized_message, flags=re.IGNORECASE)
            if not match:
                continue
            low = self._parse_money(match.group(1))
            high = self._parse_money(match.group(2))
            if low is None or high is None:
                continue
            return min(low, high), max(low, high)

        # số đầu không có đơn vị (từ 1 đến 2tr)
        partial_range_patterns = [
            rf"(?:tu|từ)\s*{number_pattern}\s*(?:den|đến|toi|tới|-)\s*{money_pattern}",
            rf"{number_pattern}\s*(?:-|–|~|to|den|đến)\s*{money_pattern}",
        ]
        for pattern in partial_range_patterns:
            match = re.search(pattern, normalized_message, flags=re.IGNORECASE)
            if not match:
                continue
            high_raw = match.group(2)
            high = self._parse_money(high_raw)
            if high is None:
                continue
            
            unit = 1
            if any(t in high_raw.lower() for t in ("tr", "triệu", "trieu")):
                unit = 1_000_000
            elif any(t in high_raw.lower() for t in ("nghìn", "nghin", "ngàn", "ngan", "k")):
                unit = 1_000
            
            low_raw = match.group(1).replace(",", ".")
            try:
                low = int(float(low_raw) * unit)
            except ValueError:
                low = None
                
            if low is not None and low > 0:
                return min(low, high), max(low, high)

        max_match = re.search(rf"(?:duoi|dưới|toi\s*da|tối\s*đa|max|khong\s*qua|không\s*quá)\s*{money_pattern}", normalized_message, flags=re.IGNORECASE)
        if max_match:
            max_value = self._parse_money(max_match.group(1))
            if max_value is not None:
                return max(0, int(max_value * 0.4)), max_value

        min_match = re.search(rf"(?:tren|trên|min)\s*{money_pattern}", normalized_message, flags=re.IGNORECASE)
        if min_match:
            min_value = self._parse_money(min_match.group(1))
            if min_value is not None:
                return min_value, int(min_value * 2.5)

        standalone_amounts = re.findall(r"\b\d+(?:[.,]\d+)?\s*(?:tr|triệu|trieu|k|nghìn|nghin|ngàn|ngan|vnd|đ|d)\b|\b\d{6,}\b", normalized_message, flags=re.IGNORECASE)
        values = [self._parse_money(item) for item in standalone_amounts]
        values = [value for value in values if value is not None]
        if len(values) >= 2:
            return min(values), max(values)
        if len(values) == 1:
            value = values[0]
            return int(value * 0.7), int(value * 1.3)

        return None

    def _has_money_signal(self, normalized_message: str) -> bool:
        """Kiểm tra nhanh xem tin nhắn có chứa các từ khóa liên quan đến tiền bạc (giá, vnd, k, củ, triệu) hay không trước khi chạy Regex nặng."""
        if re.search(r"\b\d+(?:[.,]\d+)?\s*(tr|triệu|trieu|k|nghìn|nghin|ngàn|ngan|vnd|đ)\b", normalized_message, flags=re.IGNORECASE):
            return True
        budget_keywords = (
            "ngan sach",
            "ngân sách",
            "gia",
            "giá",
            "chi phi",
            "chi phí",
            "duoi",
            "dưới",
            "tren",
            "trên",
        )
        return any(keyword in normalized_message for keyword in budget_keywords)

    def _parse_money(self, raw_value: str) -> int | None:
        """Chuyển đổi chuỗi tiền tệ (như '1.5tr', '500k') thành con số nguyên (Integer) theo đơn vị VNĐ."""
        value = self._normalize_space(raw_value).lower().replace(" ", "")
        if not value:
            return None

        unit = 1
        if any(token in value for token in ("tr", "triệu", "trieu")):
            unit = 1_000_000
            value = value.replace("triệu", "").replace("trieu", "").replace("tr", "")
        elif any(token in value for token in ("nghìn", "nghin", "ngàn", "ngan", "k")):
            unit = 1_000
            value = value.replace("nghìn", "").replace("nghin", "").replace("ngàn", "").replace("ngan", "").replace("k", "")
        else:
            value = value.replace("vnd", "").replace("đ", "").replace("d", "")

        cleaned = value.replace(",", ".")
        if cleaned.count(".") > 1:
            cleaned = cleaned.replace(".", "")

        try:
            amount = float(cleaned)
        except ValueError:
            return None

        parsed = int(amount * unit)
        return parsed if parsed > 0 else None

    def _extract_party(self, normalized_message: str) -> tuple[int | None, list[int] | None]:
        """Trích xuất số lượng người lớn và số lượng/độ tuổi trẻ em đi cùng từ tin nhắn của người dùng."""
        adults = None
        children = None

        adults_match = re.search(r"(\d{1,2})\s*(?:nguoi\s*lon|người\s*lớn|adult|adults)", normalized_message, flags=re.IGNORECASE)
        if adults_match:
            adults = int(adults_match.group(1))
        else:
            people_match = re.search(r"(\d{1,2})\s*(?:nguoi|người|khach|khách)", normalized_message, flags=re.IGNORECASE)
            if people_match:
                adults = int(people_match.group(1))

        child_count_match = re.search(r"(\d{1,2})\s*(?:tre\s*em|trẻ\s*em|be|bé|child|children)", normalized_message, flags=re.IGNORECASE)
        age_matches = re.findall(r"(\d{1,2})\s*tuoi", normalized_message, flags=re.IGNORECASE)

        if age_matches:
            ages = [int(age) for age in age_matches]
            children = self._sanitize_children(ages)
        elif child_count_match:
            child_count = int(child_count_match.group(1))
            if child_count > 0:
                children = self._sanitize_children([8 for _ in range(min(child_count, 6))])

        return adults, children

    def _extract_min_rating(self, normalized_message: str) -> float | None:
        """Trích xuất tiêu chuẩn chất lượng tối thiểu (số sao, rating) mà người dùng yêu cầu (ví dụ: 'resort 5 sao', 'khách sạn 4*')."""
        star_match = re.search(r"\b([1-5](?:[.,]\d)?)\s*(?:sao|star)\b", normalized_message, flags=re.IGNORECASE)
        if star_match:
            return max(0.0, min(5.0, float(star_match.group(1).replace(",", "."))))

        plus_match = re.search(r"\b([1-5])\s*\+\b", normalized_message)
        if plus_match:
            return float(plus_match.group(1))

        luxury_keywords = ("cao cap", "cao cấp", "sang trong", "sang trọng", "5 sao")
        if any(keyword in normalized_message for keyword in luxury_keywords):
            return 4.5

        return None

    def _extract_required_amenities(self, normalized_message: str) -> list[str]:
        """Trích xuất danh sách các tiện ích bắt buộc (như hồ bơi, wifi, bữa sáng) dựa trên bộ từ điển đồng nghĩa (Synonyms Dictionary)."""
        results: list[str] = []
        for canonical, aliases in self.AMENITY_SYNONYMS.items():
            if any(alias in normalized_message for alias in aliases):
                results.append(canonical)
        deduped: list[str] = []
        for item in results:
            if item not in deduped:
                deduped.append(item)
        return deduped

    def _extract_dates(self, normalized_message: str) -> tuple[datetime | None, datetime | None]:
        """Trích xuất ngày bắt đầu nhận phòng (check-in) và trả phòng (check-out) hoặc khoảng thời gian (số đêm) lưu trú."""
        now = datetime.now(timezone.utc)
        today = now.date()

        explicit_dates: list[tuple[str, str, str | None]] = []
        for match in re.finditer(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b", normalized_message):
            left_bound = max(0, match.start() - 3)
            right_bound = min(len(normalized_message), match.end() + 3)
            neighborhood = normalized_message[left_bound:right_bound]
            if re.search(r"(tr|triệu|trieu|k|nghìn|nghin|ngàn|ngan|vnd|đ)", neighborhood, flags=re.IGNORECASE):
                continue
            explicit_dates.append((match.group(1), match.group(2), match.group(3)))

        parsed_dates: list[datetime] = []
        for day_raw, month_raw, year_raw in explicit_dates:
            try:
                day = int(day_raw)
                month = int(month_raw)
                year = int(year_raw) if year_raw else today.year
                if year < 100:
                    year += 2000
                candidate = datetime(year, month, day, tzinfo=timezone.utc)
                if candidate.date() < today and not year_raw:
                    candidate = datetime(year + 1, month, day, tzinfo=timezone.utc)
                parsed_dates.append(candidate)
            except ValueError:
                continue

        nights_match = re.search(r"(\d{1,2})\s*(?:dem|đêm)", normalized_message, flags=re.IGNORECASE)
        nights = int(nights_match.group(1)) if nights_match else None

        check_in = None
        if re.search(r"\bngày\s*mai\b|\bmai\b", normalized_message, flags=re.IGNORECASE):
            check_in = datetime.combine(today + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
        elif re.search(r"\bhôm\s*nay\b|\bhom\s*nay\b", normalized_message, flags=re.IGNORECASE):
            check_in = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)

        if parsed_dates:
            check_in = parsed_dates[0]
            if len(parsed_dates) >= 2:
                check_out = parsed_dates[1]
                if check_out <= check_in:
                    check_out = check_in + timedelta(days=1)
                return check_in, check_out

        if check_in and nights:
            return check_in, check_in + timedelta(days=max(1, nights))
        if parsed_dates and nights:
            return parsed_dates[0], parsed_dates[0] + timedelta(days=max(1, nights))

        return check_in, None

    def _extract_trip_style(self, normalized_message: str) -> TravelStyle | None:
        """Phân tích và suy luận phong cách du lịch (Nghỉ dưỡng, Công tác, Gia đình...) dựa vào các từ khóa trong câu nói."""
        style_keywords = {
            TravelStyle.RELAX: ("nghi duong", "nghỉ dưỡng", "thu gian", "thư giãn", "resort"),
            TravelStyle.FAMILY: ("gia dinh", "gia đình", "tre em", "trẻ em", "con nho", "con nhỏ"),
            TravelStyle.WORK: ("cong tac", "công tác", "business", "hoi hop", "hội họp"),
            TravelStyle.ROMANTIC: ("lang man", "lãng mạn", "cap doi", "cặp đôi", "honeymoon"),
            TravelStyle.LUXURY: ("sang trong", "sang trọng", "5 sao", "cao cap", "cao cấp"),
            TravelStyle.BUDGET: ("tiet kiem", "tiết kiệm", "gia re", "giá rẻ", "binh dan", "bình dân"),
        }
        for style, keywords in style_keywords.items():
            if any(keyword in normalized_message for keyword in keywords):
                return style
        return None

    def _normalize_amenity(self, value: str) -> str:
        """Chuẩn hóa tên gọi của các tiện ích về một từ khóa thống nhất (Canonical Key) để bộ lọc tìm kiếm hoạt động chính xác."""
        normalized = self._normalize_space(value).lower()
        for canonical, aliases in self.AMENITY_SYNONYMS.items():
            if normalized == canonical:
                return canonical
            for alias in aliases:
                if re.search(rf"\b{re.escape(alias)}\b", normalized):
                    return canonical
        return normalized

    def _parse_iso_date(self, raw_value: Any) -> datetime | None:
        """Phân tích chuỗi thời gian định dạng ISO 8601 và chuyển đổi thống nhất về múi giờ chuẩn UTC."""
        if not isinstance(raw_value, str):
            return None
        value = self._normalize_space(raw_value)
        if not value:
            return None
        try:
            if len(value) == 10:
                parsed = datetime.strptime(value, "%Y-%m-%d")
                return parsed.replace(tzinfo=timezone.utc)
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            return None

    def _map_trip_style(self, raw_style: str) -> TravelStyle | None:
        """Chuyển đổi chuỗi ký tự phong cách du lịch thành kiểu Enum TravelStyle tương ứng."""
        normalized = self._normalize_space(raw_style).lower()
        style_map = {
            "nghi_duong": TravelStyle.RELAX,
            "gia_dinh": TravelStyle.FAMILY,
            "cong_tac": TravelStyle.WORK,
            "kham_pha": TravelStyle.EXPLORE,
            "lang_man": TravelStyle.ROMANTIC,
            "sang_trong": TravelStyle.LUXURY,
            "tiet_kiem": TravelStyle.BUDGET,
        }
        return style_map.get(normalized)

    async def _analyze_intent_and_expand(
        self, message: str, context: ChatContextRequest, history: list[str], router_needed: bool, expand_needed: bool
    ) -> tuple[RouteDecision | None, list[str]]:
        """Sử dụng LLM để gộp chung 2 việc: Phân tích định tuyến ý định và Mở rộng/Viết lại câu hỏi chỉ trong 1 lần gọi, giúp giảm độ trễ."""
        if not self._can_use_groq():
            return None, [message]

        # Check routing cache để bypass Groq call cho repeated queries
        if router_needed:
            cache_key = self._normalize_space(message).lower()
            now = datetime.now(timezone.utc)
            cached = self._routing_decision_cache.get(cache_key)
            if cached is not None:
                cached_at, cached_decision, cached_queries = cached
                if (now - cached_at).total_seconds() <= self._routing_cache_ttl_seconds:
                    logger.debug(f"Routing cache HIT for message: {cache_key[:50]}")
                    return cached_decision, cached_queries

        json_keys = []
        if router_needed:
            json_keys.extend(["intent", "use_lodging_rag", "requires_more_info", "missing_fields", "clarification_question"])
        if expand_needed:
            json_keys.append("queries")
            
        keys_str = ", ".join(json_keys)
        
        prompt = f"Trả về ĐÚNG MỘT JSON object có các key: {keys_str}.\\n"
        
        if router_needed:
            prompt += (
                "intent chỉ được là: recommendation, comparison, information, casual.\\n"
                "use_lodging_rag = true khi người dùng cần truy vấn/gợi ý/so sánh liên quan đến lưu trú, khách sạn, đặt phòng, vị trí ở.\\n"
                "requires_more_info = true nếu cần thêm dữ liệu để tối ưu (ví dụ thiếu địa điểm khi cần gợi ý nơi ở cụ thể).\\n"
                "missing_fields là mảng string, có thể rỗng.\\n"
                "clarification_question là câu hỏi ngắn bằng tiếng Việt, hoặc null nếu không cần hỏi thêm.\\n"
            )
        if expand_needed:
            prompt += (
                "queries là list tối đa 2 câu viết lại ngắn gọn của người dùng (chỉ cần nếu use_lodging_rag = true). Giữ nguyên ý nghĩa.\\n"
            )
            
        prompt += (
            "Chỉ trả JSON, không markdown.\\n\\n"
            f"Tin nhắn người dùng: {message}\\n"
            f"Lịch sử gần đây: {self._history_text(history)}\\n"
            f"Địa chỉ trong context: {context.address}\\n"
            f"Phong cách chuyến đi: {context.trip_style.value}"
        )

        try:
            raw = await asyncio.to_thread(groq_client.generate_content, prompt)
            parsed: dict[str, Any] = json.loads(raw)

            decision = None
            if router_needed:
                intent_value = str(parsed.get("intent", "casual")).strip().lower()
                intent_map = {
                    "recommendation": ChatIntent.RECOMMENDATION,
                    "comparison": ChatIntent.COMPARISON,
                    "information": ChatIntent.INFORMATION,
                    "casual": ChatIntent.CASUAL,
                }
                intent = intent_map.get(intent_value, ChatIntent.CASUAL)
                use_lodging_rag = bool(parsed.get("use_lodging_rag", False))
                requires_more_info = bool(parsed.get("requires_more_info", False))
                missing_fields_raw = parsed.get("missing_fields", [])
                missing_fields = [str(item).strip() for item in missing_fields_raw if str(item).strip()] if isinstance(missing_fields_raw, list) else []
                clarification_question = parsed.get("clarification_question")
                clarification_text = str(clarification_question).strip() if clarification_question else None

                decision = RouteDecision(
                    intent=intent,
                    use_lodging_rag=use_lodging_rag,
                    requires_more_info=requires_more_info,
                    missing_fields=missing_fields,
                    clarification_question=clarification_text,
                )

            queries = [message]
            if expand_needed:
                query_list = parsed.get("queries", [])
                if isinstance(query_list, list):
                    for item in query_list:
                        val = self._normalize_space(str(item))
                        if val and val not in queries:
                            queries.append(val)
                queries = self._augment_query_variants_locally(queries, message, context, history)

            # Cache routing decision
            if router_needed and decision:
                cache_key = self._normalize_space(message).lower()
                self._routing_decision_cache[cache_key] = (datetime.now(timezone.utc), decision, queries)
                
            return decision, queries
        except Exception as exc:
            logger.warning(f"Combined LLM logic failed: {str(exc)}")
            return None, self._augment_query_variants_locally([message], message, context, history)

    def _augment_query_variants_locally(self, base_queries: list[str], message: str, context: ChatContextRequest, history: list[str]) -> list[str]:
        """Mở rộng truy vấn bằng biến thể local để bắt nhiều cách nhập câu hơn mà không cần gọi thêm LLM."""
        queries: list[str] = []
        seen: set[str] = set()

        def append_query(value: str) -> None:
            normalized_value = self._normalize_space(value)
            if not normalized_value:
                return
            lowered = normalized_value.lower()
            if lowered in seen:
                return
            seen.add(lowered)
            queries.append(normalized_value)

        for query in base_queries:
            append_query(query)

        append_query(message)

        query_seed_parts = [message]
        if context.address:
            query_seed_parts.append(f"khach san o {context.address}")
            query_seed_parts.append(f"luu tru tai {context.address}")
        if context.min_price != 300000 or context.max_price != 3000000:
            query_seed_parts.append(f"ngan sach {context.min_price} den {context.max_price}")
        if context.min_rating is not None:
            query_seed_parts.append(f"toi thieu {context.min_rating} sao")
        if context.required_amenities:
            query_seed_parts.append(" ".join(context.required_amenities))
        if context.trip_style != TravelStyle.EXPLORE:
            query_seed_parts.append(context.trip_style.value)

        recent_hint = self._last_history_address(history)
        if recent_hint and not context.address:
            query_seed_parts.append(f"o {recent_hint}")

        for seed in query_seed_parts:
            tokens = self._normalize_space(seed).lower()
            if not tokens:
                continue
            if tokens == self._normalize_space(message).lower():
                continue
            append_query(tokens)

        if len(queries) > 4:
            queries = queries[:4]
        return queries

    def _last_history_address(self, history: list[str]) -> str | None:
        """Lấy địa điểm gần nhất từ lịch sử để phục vụ các câu hỏi tham chiếu như 'đó', 'chỗ đó'."""
        if not history:
            return None

        for item in reversed(history[-8:]):
            normalized_item = self._normalize_space(item)
            if not normalized_item:
                continue
            lower_item = normalized_item.lower()
            candidate = self._extract_destination(normalized_item, lower_item)
            if candidate:
                return candidate
        return None

    def _heuristic_route_decision(self, message: str, context: ChatContextRequest) -> RouteDecision:
        """Phương án dự phòng (Fallback) phân tích ý định bằng từ khóa và vector ngữ nghĩa (Semantic) khi LLM Router bị lỗi."""
        normalized = self._normalize_space(message).lower()
        intent = self.detect_intent(normalized)
        semantic_intent = self._intent_from_semantic(normalized)
        if semantic_intent is not None:
            intent = semantic_intent

        has_non_lodging_topic = any(keyword in normalized for keyword in self.NON_LODGING_TOPIC_KEYWORDS)
        has_lodging_signal = self._has_lodging_signal(normalized)
        
        if has_lodging_signal:
            is_lodging = True
        elif has_non_lodging_topic:
            is_lodging = False
        else:
            is_lodging = self._is_lodging_related(normalized, context, intent, has_non_lodging_topic, has_lodging_signal)

        requires_more_info = False
        missing_fields: list[str] = []
        clarification_question = None

        if is_lodging and intent in {ChatIntent.RECOMMENDATION, ChatIntent.COMPARISON} and not context.address:
            requires_more_info = True
            missing_fields = ["address"]
            clarification_question = "Bạn muốn ưu tiên khu vực nào để mình gợi ý lưu trú chính xác hơn?"

        return RouteDecision(
            intent=intent,
            use_lodging_rag=is_lodging,
            requires_more_info=requires_more_info,
            missing_fields=missing_fields,
            clarification_question=clarification_question,
        )

    async def _build_hotel_pool(self, context: ChatContextRequest) -> list:
        """Lấy ra danh sách khách sạn tiềm năng (Candidate Pool) từ cơ sở dữ liệu dựa trên khoảng cách địa lý (Nearby) và toàn cầu (Global)."""
        nearby_task = asyncio.create_task(self._get_nearby_hotels(context))
        global_task = asyncio.create_task(self._get_global_hotels_cached(self.MAX_GLOBAL_POOL))
        nearby_hotels, global_hotels = await asyncio.gather(nearby_task, global_task)

        if len(nearby_hotels) >= 25:
            return nearby_hotels

        merged: dict[str, object] = {}

        for hotel in nearby_hotels + global_hotels:
            key = getattr(hotel, "property_token", None) or getattr(hotel, "name", "")
            if key:
                merged[key] = hotel

        return list(merged.values())

    async def _get_global_hotels_cached(self, limit: int) -> list:
        """Lấy danh sách toàn bộ khách sạn từ bộ nhớ đệm (Cache) để giảm tải và hạn chế việc query liên tục vào Firestore."""
        now = datetime.now(timezone.utc)
        if self._global_hotels_cache is not None:
            cached_at, cached_limit, cached_hotels = self._global_hotels_cache
            if (now - cached_at).total_seconds() <= self.GLOBAL_POOL_CACHE_TTL_SECONDS and cached_limit >= limit:
                return cached_hotels[:limit]

        hotels = await hotel_repo.list_hotels(limit=limit)
        self._global_hotels_cache = (now, limit, hotels)
        return hotels

    async def _get_nearby_hotels(self, context: ChatContextRequest) -> list:
        """Truy vấn danh sách các khách sạn nằm gần vị trí được chỉ định (tọa độ GPS, Ref ID hoặc tên địa chỉ)."""
        if context.gps is None and context.ref_id is None and context.address:
            hydrated = await self._hydrate_geo_context(context)
        else:
            hydrated = context
        gps = hydrated.gps

        nearby_key = self._nearby_cache_key(hydrated)
        now = datetime.now(timezone.utc)
        if nearby_key:
            cached = self._nearby_hotels_cache.get(nearby_key)
            if cached is not None:
                cached_at, hotels = cached
                if (now - cached_at).total_seconds() <= self.NEARBY_POOL_CACHE_TTL_SECONDS:
                    return hotels

        if not gps:
            return []

        try:
            hotels = await hotel_repo.search_hotels(gps.latitude, gps.longitude)
            if nearby_key:
                self._nearby_hotels_cache[nearby_key] = (now, hotels)
                if len(self._nearby_hotels_cache) > self.NEARBY_POOL_CACHE_MAX_ITEMS:
                    overflow = len(self._nearby_hotels_cache) - self.NEARBY_POOL_CACHE_MAX_ITEMS
                    for key in list(self._nearby_hotels_cache.keys())[:overflow]:
                        self._nearby_hotels_cache.pop(key, None)
            return hotels
        except Exception as exc:
            logger.warning(f"Cannot search nearby hotels for chatbot RAG: {str(exc)}")
            return []

    def _nearby_cache_key(self, context: ChatContextRequest) -> str | None:
        """Tạo ra một chuỗi định danh (Cache Key) duy nhất để lưu trữ kết quả tìm kiếm khách sạn lân cận vào bộ nhớ đệm."""
        if context.ref_id:
            return f"ref:{context.ref_id}"
        if context.gps is not None:
            return f"gps:{round(context.gps.latitude, 3)}:{round(context.gps.longitude, 3)}"
        if context.address:
            return f"addr:{self._normalize_space(context.address).lower()}"
        return None

    def _retrieve_relevant_hotels(
        self,
        message: str,
        query_variants: list[str],
        context: ChatContextRequest,
        hotels: list,
        limit: int,
    ) -> list[RetrievedHotel]:
        """Truy xuất kết hợp (Hybrid Retrieval): Áp dụng cả so khớp từ khóa (Lexical), so khớp vector ngữ nghĩa (Semantic) và độ khớp ngân sách để chọn ra các KS tốt nhất."""
        if not hotels:
            return []

        merged_queries = [self._build_query_text(message, context)]
        for variant in query_variants:
            text = self._build_query_text(variant, context)
            if text not in merged_queries:
                merged_queries.append(text)

        query_terms_list = [self._tokenize(query) for query in merged_queries]
        profile_texts = [self._hotel_profile_text(hotel) for hotel in hotels]

        shortlist_candidates: list[tuple[int, float]] = []
        for idx, hotel in enumerate(hotels):
            if not self._matches_hard_filters(hotel, context):
                continue
            profile_terms = self._tokenize(profile_texts[idx])
            lexical_best = 0.0
            for query_terms in query_terms_list:
                lexical_best = max(lexical_best, self._lexical_overlap(query_terms, profile_terms))

            # Quick score để shortlist trước khi encode semantic toàn bộ pool.
            quick_score = (0.72 * lexical_best) + (0.18 * self._price_fit(getattr(hotel, "price", 0.0), context.min_price, context.max_price)) + (0.10 * self._amenity_fit(hotel, context.required_amenities))
            shortlist_candidates.append((idx, quick_score))

        if not shortlist_candidates:
            return []

        shortlist_candidates.sort(key=lambda item: item[1], reverse=True)
        shortlist_size = self._semantic_shortlist_limit(limit)
        shortlisted_indexes = [idx for idx, _ in shortlist_candidates[:shortlist_size]]

        query_vectors: list[tuple[float, ...] | None] = [None for _ in merged_queries]
        profile_vectors: dict[int, tuple[float, ...] | None] = {idx: None for idx in shortlisted_indexes}
        if semantic_text_encoder.is_available():
            encoded_queries = semantic_text_encoder.encode(merged_queries)
            if encoded_queries and len(encoded_queries) == len(merged_queries):
                query_vectors = list(encoded_queries)

            shortlist_texts = [profile_texts[idx] for idx in shortlisted_indexes]
            encoded_profiles = semantic_text_encoder.encode(shortlist_texts)
            if encoded_profiles and len(encoded_profiles) == len(shortlist_texts):
                for idx, vec in zip(shortlisted_indexes, encoded_profiles):
                    profile_vectors[idx] = vec

        retrieved: list[RetrievedHotel] = []

        for idx in shortlisted_indexes:
            hotel = hotels[idx]

            profile_text = profile_texts[idx]
            snippet = self._hotel_snippet(hotel)

            profile_terms = self._tokenize(profile_text)
            best_score = 0.0
            best_query = merged_queries[0]

            for query_idx, query_text in enumerate(merged_queries):
                lexical_score = self._lexical_overlap(query_terms_list[query_idx], profile_terms)
                semantic_score = None

                query_vec = query_vectors[query_idx]
                profile_vec = profile_vectors.get(idx)
                if query_vec is not None and profile_vec is not None:
                    semantic_score = semantic_text_encoder.cosine_similarity(query_vec, profile_vec)

                combined = (0.65 * (semantic_score if semantic_score is not None else lexical_score)) + (0.35 * lexical_score)
                if combined > best_score:
                    best_score = combined
                    best_query = query_text

            price_fit = self._price_fit(getattr(hotel, "price", 0.0), context.min_price, context.max_price)
            amenity_fit = self._amenity_fit(hotel, context.required_amenities)
            rating_fit = self._rating_fit(hotel, context.min_rating)
            final_score = (0.65 * best_score) + (0.15 * price_fit) + (0.12 * amenity_fit) + (0.08 * rating_fit)

            if final_score <= 0:
                continue

            retrieved.append(
                RetrievedHotel(
                    hotel=hotel,
                    score=final_score,
                    snippet=snippet,
                    matched_query=best_query,
                )
            )

        retrieved.sort(key=lambda item: item.score, reverse=True)
        return retrieved[: max(1, limit)]

    def _semantic_shortlist_limit(self, limit: int) -> int:
        """Giới hạn số lượng ứng viên khách sạn tối đa được phép chạy qua bộ mã hóa vector (Semantic Encoding) - giảm từ 180 xuống 120 để tốc độ."""
        return min(limit, 120)

    async def _rerank_with_internal_ranker(
        self,
        context: ChatContextRequest,
        requester_uid: str | None,
        retrieved: list[RetrievedHotel],
    ) -> list:
        """Xếp hạng lại (Rerank) các khách sạn đã lọc bằng dịch vụ chấm điểm nội bộ, kết hợp thêm yếu tố thời tiết và hồ sơ cá nhân hóa của người dùng."""
        if not retrieved:
            return []

        now = datetime.now(timezone.utc)
        check_in = context.check_in or (now + timedelta(days=7))
        check_out = context.check_out or (check_in + timedelta(days=2))

        if check_in.tzinfo is None:
            check_in = check_in.replace(tzinfo=timezone.utc)
        if check_out.tzinfo is None:
            check_out = check_out.replace(tzinfo=timezone.utc)
        if check_out <= check_in:
            check_out = check_in + timedelta(days=2)

        safe_children = self._sanitize_children(context.children)

        # Dùng cùng payload chuẩn để tận dụng logic personal ranking đã có sẵn.
        payload = DiscoverRequest(
            language=context.language,
            address=context.address or "Việt Nam",
            gps=context.gps,
            ref_id=context.ref_id,
            check_in=check_in,
            check_out=check_out,
            min_price=min(context.min_price, context.max_price),
            max_price=max(context.min_price, context.max_price),
            children=safe_children,
            adults=context.adults,
            personality=context.personality,
            trip_style=context.trip_style,
            max_ranked_hotels=max(1, min(context.max_ranked_hotels * 2, 20)),
        )

        hotels = [item.hotel for item in retrieved]

        # Skip weather loading để giảm latency (weather không critical cho ranking)
        weather_by_identity: dict[str, list] = {}

        try:
            return await hotel_ranking_service.rank_discovered_hotels(
                places=hotels,
                payload=payload,
                weather_by_identity=weather_by_identity,
                requester_uid=requester_uid,
            )
        except Exception as exc:
            logger.warning(f"Internal ranking failed in chatbot RAG: {str(exc)}")
            return hotels

    async def _build_answer(
        self,
        message: str,
        intent: ChatIntent,
        context: ChatContextRequest,
        recommendations: list[ChatRecommendationItem],
        history: list[str],
        requires_more_info: bool,
    ) -> tuple[str, bool]:
        """Sử dụng Groq LLM để sinh ra đoạn văn bản tư vấn và lý giải vì sao chọn các khách sạn này. Có sẵn cơ chế fallback nếu model sập."""
        if not recommendations:
            if requires_more_info:
                return (
                    "Mình có thể tư vấn theo nhiều phong cách khác nhau, nhưng để gợi ý sát nhất bạn cho mình điểm đến cụ thể nhé. "
                    "Ví dụ: Đà Lạt, Nha Trang hoặc một khu vực bạn muốn ở.",
                    True,
                )
            return (
                "Mình chưa tìm được khách sạn phù hợp ngay lúc này. Bạn thử nới rộng ngân sách hoặc đổi khu vực tìm kiếm nhé.",
                True,
            )

        context_lines = []
        for idx, item in enumerate(recommendations, start=1):
            context_lines.append(
                f"[{idx}] {item.name} | Giá: {int(item.price):,} VND | Điểm AI: {item.ai_score if item.ai_score is not None else 'N/A'} | Địa chỉ: {item.address or 'N/A'}"
            )

        history_text = self._history_text(history)

        if not self._can_use_groq():
            fallback_lines = ["Mình gợi ý nhanh top lựa chọn phù hợp nhất hiện tại:"]
            for idx, item in enumerate(recommendations[:3], start=1):
                fallback_lines.append(
                    f"{idx}. {item.name} - khoảng {int(item.price):,} VND/đêm, phù hợp vì giá và tổng điểm đang tốt trong khu vực."
                )
            if requires_more_info:
                fallback_lines.append("Bạn muốn mình chốt lại theo địa điểm cụ thể nào để gợi ý chính xác hơn?")
            else:
                fallback_lines.append("Bạn muốn mình lọc tiếp theo tiêu chí gần trung tâm, có hồ bơi hay phù hợp gia đình?")
            return "\n".join(fallback_lines), True

        prompt = (
            "Trả về ĐÚNG MỘT JSON object có key duy nhất là answer.\\n"
            "Không markdown, không text ngoài JSON.\\n"
            "Bạn là trợ lý tư vấn du lịch cao cấp cho người Việt.\\n"
            "Nhiệm vụ: trả lời ngắn gọn, thực dụng, đúng dữ liệu gợi ý đầu vào, giữ giọng tự nhiên.\\n"
            "Bắt buộc bám sát các khách sạn đã được ranking sẵn. Không tự bịa thêm khách sạn mới.\\n"
            "Nêu rõ vì sao khách sạn phù hợp theo ngân sách, phong cách chuyến đi và số người.\\n"
            "Nếu thiếu dữ liệu thì vẫn tư vấn ở mức tổng quát và đặt 1 câu hỏi làm rõ.\\n"
            "Kết thúc bằng một câu hỏi gợi mở để tiếp tục hội thoại.\\n\\n"
            f"Ý định: {intent.value}\\n"
            f"Cần hỏi thêm thông tin: {requires_more_info}\\n"
            f"Câu hỏi người dùng: {message}\\n"
            f"Lịch sử hội thoại gần đây: {history_text}\\n"
            f"Địa điểm: {context.address}\\n"
            f"Khoảng ngân sách: {context.min_price}-{context.max_price} VND\\n"
            f"Rating tối thiểu: {context.min_rating if context.min_rating is not None else 'không yêu cầu'}\n"
            f"Tiện ích bắt buộc: {context.required_amenities or []}\n"
            f"Phong cách chuyến đi: {context.trip_style.value}\\n"
            f"Người lớn: {context.adults}, Trẻ em: {context.children or []}\\n\\n"
            "Danh sách khách sạn đã xếp hạng:\\n"
            + "\\n".join(context_lines)
        )

        try:
            generated = await asyncio.to_thread(groq_client.generate_content, prompt)
            if generated and generated.strip():
                parsed = json.loads(generated)
                answer = str(parsed.get("answer", "")).strip()
                if answer:
                    return answer, False
        except Exception as exc:
            logger.warning(f"Chatbot Groq generation failed: {str(exc)}")

        fallback_lines = ["Mình gợi ý nhanh top lựa chọn phù hợp nhất hiện tại:"]
        for idx, item in enumerate(recommendations[:3], start=1):
            fallback_lines.append(
                f"{idx}. {item.name} - khoảng {int(item.price):,} VND/đêm, phù hợp vì giá và tổng điểm đang tốt trong khu vực."
            )
        if requires_more_info:
            fallback_lines.append("Bạn muốn mình chốt lại theo địa điểm cụ thể nào để gợi ý chính xác hơn?")
        else:
            fallback_lines.append("Bạn muốn mình lọc tiếp theo tiêu chí gần trung tâm, có hồ bơi hay phù hợp gia đình?")
        return "\n".join(fallback_lines), True

    async def _build_general_answer(self, message: str, history: list[str]) -> tuple[str, bool]:
        """Dùng Groq LLM sinh ra câu trả lời cho những câu hỏi tổng quát, tư vấn thông thường không đòi hỏi luồng trích xuất dữ liệu khách sạn (Lodging RAG)."""
        if not self._can_use_groq():
            return self._build_fast_general_answer(message), True

        prompt = (
            "Trả về ĐÚNG MỘT JSON object có key duy nhất là answer.\\n"
            "Không markdown, không text ngoài JSON.\\n"
            "Bạn là chatbot tổng quát cho một web gợi ý nơi lưu trú.\\n"
            "Hãy linh hoạt: vừa trả lời câu hỏi đời thường, vừa hỗ trợ khi user chuyển chủ đề sang lưu trú/du lịch.\\n"
            "Nếu user hỏi thông tin chung: trả lời rõ ràng, không lan man.\\n"
            "Nếu user trò chuyện xã giao: thân thiện, tự nhiên.\\n"
            "Nếu user có dấu hiệu cần tư vấn lưu trú: gợi ý bước tiếp theo bằng 1 câu hỏi làm rõ nhu cầu.\\n"
            "Tránh cứng nhắc, không ép user theo form.\\n\\n"
            f"Lịch sử hội thoại gần đây: {self._history_text(history)}\\n"
            f"Tin nhắn người dùng: {message}"
        )

        try:
            generated = await asyncio.to_thread(groq_client.generate_content, prompt)
            if generated and generated.strip():
                parsed = json.loads(generated)
                answer = str(parsed.get("answer", "")).strip()
                if answer:
                    return answer, False
        except Exception as exc:
            logger.warning(f"General chatbot generation failed: {str(exc)}")

        return (
            "Mình hiểu ý bạn. Nếu bạn muốn, mình có thể hỗ trợ từ trao đổi thông tin chung đến tư vấn kế hoạch du lịch cụ thể.",
            True,
        )

    def _to_recommendation_item(self, hotel) -> ChatRecommendationItem:
        """Chuyển đổi (Map) dữ liệu từ Model Khách sạn thành cấu trúc Schema chuẩn (Recommendation Item) để gửi về cho ứng dụng Frontend."""
        reasons: list[str] = []
        hotel_rating = self._hotel_rating(hotel)
        if hotel_rating is not None:
            reasons.append(f"Rating hiện tại {hotel_rating:.1f}/5")
        if hotel.ai_sentiment and hotel.ai_sentiment.ai_score is not None:
            reasons.append(f"Điểm cảm nhận khách hàng {hotel.ai_sentiment.ai_score:.1f}/5")
        if hotel.amenities:
            reasons.append(f"Tiện ích nổi bật: {', '.join(hotel.amenities[:3])}")
        if hotel.nearby_places:
            reasons.append(f"Gần {hotel.nearby_places[0].name}")

        return ChatRecommendationItem(
            name=hotel.name,
            property_token=hotel.property_token,
            price=hotel.price,
            ai_score=hotel.ai_sentiment.ai_score if hotel.ai_sentiment else None,
            address=hotel.address,
            reasons=reasons,
        )

    def _to_citation(self, hotel, retrieved: list[RetrievedHotel]) -> ChatCitation:
        """Đóng gói các thông tin trích dẫn (Citation) nhằm cung cấp lý do minh bạch cho người dùng hiểu tại sao hệ thống lại gợi ý khách sạn đó."""
        summary_parts = []
        retrieval_score = self._retrieval_score(hotel, retrieved)
        if retrieval_score is not None:
            summary_parts.append(f"retrieval={retrieval_score:.3f}")
        matched_query = self._matched_query(hotel, retrieved)
        if matched_query:
            summary_parts.append(f"query={matched_query[:120]}")
        if hotel.ai_sentiment and hotel.ai_sentiment.ai_score is not None:
            summary_parts.append(f"ai_score={hotel.ai_sentiment.ai_score:.1f}")
        if hotel.price is not None:
            summary_parts.append(f"price={int(hotel.price):,} VND")
        if hotel.amenities:
            summary_parts.append(f"amenities={', '.join(hotel.amenities[:3])}")

        return ChatCitation(
            source_type="hotel_ranking_pipeline",
            source_id=hotel.property_token,
            title=hotel.name,
            snippet="; ".join(summary_parts) if summary_parts else "Ranked hotel result",
        )

    def _retrieval_score(self, hotel, retrieved: list[RetrievedHotel]) -> float | None:
        """Lấy ra điểm số truy xuất (Retrieval Score) của một khách sạn cụ thể từ trong danh sách kết quả đã tìm thấy."""
        token = getattr(hotel, "property_token", None)
        for item in retrieved:
            current_token = getattr(item.hotel, "property_token", None)
            if token and current_token == token:
                return item.score
        return None

    def _matched_query(self, hotel, retrieved: list[RetrievedHotel]) -> str | None:
        """Tìm ra biến thể câu hỏi (Query Variant) nào đã khớp điểm cao nhất với thông tin của khách sạn này."""
        token = getattr(hotel, "property_token", None)
        for item in retrieved:
            current_token = getattr(item.hotel, "property_token", None)
            if token and current_token == token:
                return item.matched_query
        return None

    def _build_query_text(self, message: str, context: ChatContextRequest) -> str:
        """Hợp nhất tin nhắn ban đầu với các ngữ cảnh ẩn (VD: địa điểm) thành một chuỗi truy vấn hoàn chỉnh để máy tìm kiếm hiểu sâu hơn."""
        parts = [message]
        if context.address:
            parts.append(f"dia diem {context.address}")
        parts.append(f"gia tu {context.min_price} den {context.max_price}")
        if context.min_rating is not None:
            parts.append(f"rating toi thieu {context.min_rating}")
        if context.required_amenities:
            parts.append(f"tien ich bat buoc {' '.join(context.required_amenities)}")
        parts.append(f"phong cach {context.trip_style.value}")
        parts.append(f"nguoi lon {context.adults}")
        if context.children:
            parts.append(f"tre em {' '.join(str(age) for age in context.children)}")
        return " ".join(parts)

    def _hotel_profile_text(self, hotel) -> str:
        """Biến đổi toàn bộ thông tin của khách sạn (tên, tiện ích, mô tả) thành một đoạn văn bản tóm tắt (Profile Text) để nạp vào bộ tìm kiếm Vector ngữ nghĩa."""
        nearby_names = ", ".join(place.name for place in getattr(hotel, "nearby_places", [])[:5])
        amenities = ", ".join(getattr(hotel, "amenities", [])[:10])
        sentiment = ""
        if getattr(hotel, "ai_sentiment", None) and hotel.ai_sentiment.ai_score is not None:
            sentiment = f" diem danh gia {hotel.ai_sentiment.ai_score}"

        return " ".join(
            part
            for part in [
                getattr(hotel, "name", ""),
                getattr(hotel, "description", "") or "",
                getattr(hotel, "address", "") or "",
                nearby_names,
                amenities,
                sentiment,
            ]
            if part
        )

    def _hotel_snippet(self, hotel) -> str:
        """Tạo ra một đoạn mã tóm tắt ngắn (Snippet) về khách sạn để phục vụ in log (debug) hoặc hiển thị nội dung vắn tắt."""
        top_amenities = ", ".join(getattr(hotel, "amenities", [])[:3])
        return f"{getattr(hotel, 'name', '')} | {getattr(hotel, 'address', '') or 'N/A'} | {top_amenities}"

    def _tokenize(self, text: str) -> set[str]:
        """Cắt nhỏ chuỗi văn bản thành các từ đơn (Tokens) cơ bản để phục vụ thuật toán so khớp từ khóa (Lexical Overlap)."""
        terms = re.findall(r"\w+", self._normalize_space(text).lower())
        return {term for term in terms if len(term) >= 2}

    def _lexical_overlap(self, left: set[str], right: set[str]) -> float:
        """Tính toán mức độ trùng lặp từ khóa (Token Overlap Score) giữa câu truy vấn của người dùng và tài liệu mô tả khách sạn."""
        if not left or not right:
            return 0.0
        return len(left.intersection(right)) / len(left)

    def _price_fit(self, price: float, min_price: int, max_price: int) -> float:
        """Chấm điểm (Scoring) xem mức giá của khách sạn này phù hợp đến đâu so với khoảng ngân sách mà người dùng yêu cầu."""
        if price <= 0:
            return 0.0

        lower = min(min_price, max_price)
        upper = max(min_price, max_price)
        if lower <= price <= upper:
            return 1.0
        if price < lower:
            diff = (lower - price) / max(1, lower)
        else:
            diff = (price - upper) / max(1, upper)
        return max(0.0, 1.0 - diff)

    def _rating_fit(self, hotel, min_rating: float | None) -> float:
        """Chấm điểm mức độ đáp ứng của khách sạn dựa trên yêu cầu tối thiểu về số sao hoặc điểm đánh giá (Rating) từ người dùng."""
        if min_rating is None:
            return 1.0
        rating = self._hotel_rating(hotel)
        if rating is None:
            return 0.0
        if rating >= min_rating:
            return 1.0
        return max(0.0, 1.0 - ((min_rating - rating) / max(1.0, min_rating)))

    def _amenity_fit(self, hotel, required_amenities: list[str]) -> float:
        """Chấm điểm tỷ lệ đáp ứng các tiện ích bắt buộc (Hồ bơi, bữa sáng, wifi...) của khách sạn so với đòi hỏi của người dùng."""
        if not required_amenities:
            return 1.0
        hotel_amenities = self._hotel_amenities_canonical(hotel)
        matched = sum(1 for amenity in required_amenities if amenity in hotel_amenities)
        return matched / len(required_amenities)

    def _matches_hard_filters(self, hotel, context: ChatContextRequest) -> bool:
        """Thực hiện bộ lọc cứng (Hard Filter) loại bỏ thẳng tay các khách sạn thiếu tiện ích hoặc thiếu sao, giúp giảm sự phụ thuộc rủi ro vào AI Prompt."""
        if context.min_rating is not None:
            rating = self._hotel_rating(hotel)
            if rating is None or rating < context.min_rating:
                return False

        if context.required_amenities:
            hotel_amenities = self._hotel_amenities_canonical(hotel)
            # Normalize incoming required amenities before checking against hotel's canonical set
            required_norm = [self._normalize_amenity(str(item)) for item in context.required_amenities if str(item).strip()]
            if any(amenity not in hotel_amenities for amenity in required_norm):
                return False

        return True

    def _hotel_rating(self, hotel) -> float | None:
        """Lấy ra chỉ số sao hoặc điểm đánh giá (Rating) đại diện cho khách sạn từ nhiều nguồn dữ liệu hiện có."""
        ai_sentiment = getattr(hotel, "ai_sentiment", None)
        ai_score = getattr(ai_sentiment, "ai_score", None) if ai_sentiment else None
        raw_rating = getattr(hotel, "raw_rating", None)

        ai_value = float(ai_score) if isinstance(ai_score, (int, float)) and ai_score > 0 else None
        raw_value = float(raw_rating) if isinstance(raw_rating, (int, float)) and raw_rating > 0 else None

        if ai_value is None and raw_value is None:
            return None

        if ai_value is not None and raw_value is not None:
            weighted = (0.6 * ai_value) + (0.4 * raw_value)
            return max(0.0, min(5.0, weighted))

        fallback = ai_value if ai_value is not None else raw_value
        if fallback is None:
            return None
        return max(0.0, min(5.0, float(fallback)))

    def _hotel_amenities_canonical(self, hotel) -> set[str]:
        """Chuyển toàn bộ danh sách tiện ích của khách sạn về dạng chuẩn hóa từ khóa thống nhất (Canonical) để so khớp thuật toán cực nhanh."""
        values = getattr(hotel, "amenities", []) or []
        normalized = [self._normalize_amenity(str(item)) for item in values if str(item).strip()]
        return {item for item in normalized if item}

    def _has_lodging_signal(self, normalized_message: str) -> bool:
        """Nhận diện tín hiệu lưu trú rõ ràng để tránh đẩy nhầm câu hỏi đa ý vào RAG khách sạn."""
        if any(keyword in normalized_message for keyword in self.LODGING_KEYWORDS):
            return True
        if any(word in normalized_message for word in self.RECOMMENDATION_KEYWORDS):
            return True
        if any(word in normalized_message for word in self.COMPARE_KEYWORDS):
            return True
        return False

    def _is_lodging_related(
        self,
        normalized_message: str,
        context: ChatContextRequest,
        intent: ChatIntent | None = None,
        has_non_lodging_topic: bool = False,
        has_lodging_signal: bool = False,
    ) -> bool:
        """Xác định nhanh xem câu hỏi hiện tại có liên quan đến việc đặt phòng, lưu trú, khách sạn hay không dựa trên từ vựng."""
        # Câu hỏi có chủ đề rõ ràng ngoài lưu trú thì ưu tiên trả lời tổng quát, không đẩy vào RAG khách sạn.
        if has_non_lodging_topic and not has_lodging_signal:
            return False

        if has_lodging_signal:
            return True

        semantic_lodging_intent = self._intent_from_semantic(normalized_message)
        if semantic_lodging_intent in {ChatIntent.RECOMMENDATION, ChatIntent.COMPARISON}:
            return True

        # Với intent INFORMATION chỉ vào RAG khi có thêm ngữ cảnh địa điểm rõ ràng.
        if semantic_lodging_intent == ChatIntent.INFORMATION:
            return bool(context.address or context.ref_id or context.gps)

        # Có địa điểm nhưng không có tín hiệu lưu trú rõ ràng thì giữ ở luồng general để tránh nhầm sang khách sạn.
        if context.address or context.ref_id or context.gps:
            return False

        return False

    def _intent_from_semantic(self, message: str) -> ChatIntent | None:
        """Suy luận ý định (Intent) của câu hỏi bằng cách đo khoảng cách Cosine Vector so với các câu mẫu (Prototypes) đã được nạp sẵn."""
        if not semantic_text_encoder.is_available():
            return None

        prototype_texts: list[str] = []
        prototype_intents: list[ChatIntent] = []
        for intent, examples in self.INTENT_PROTOTYPES.items():
            for example in examples:
                prototype_texts.append(example)
                prototype_intents.append(intent)

        vectors = semantic_text_encoder.encode([message, *prototype_texts])
        if not vectors or len(vectors) != len(prototype_texts) + 1:
            return None

        message_vec = vectors[0]
        intent_scores: dict[ChatIntent, float] = {
            ChatIntent.RECOMMENDATION: 0.0,
            ChatIntent.COMPARISON: 0.0,
            ChatIntent.INFORMATION: 0.0,
            ChatIntent.CASUAL: 0.0,
        }

        for idx, intent in enumerate(prototype_intents, start=1):
            score = semantic_text_encoder.cosine_similarity(message_vec, vectors[idx])
            if score > intent_scores[intent]:
                intent_scores[intent] = score

        best_intent = max(intent_scores, key=intent_scores.get)
        if intent_scores[best_intent] < 0.30:
            return None
        return best_intent



    def _build_fast_general_answer(self, message: str) -> str:
        """Trả lời tự động với tốc độ cực nhanh (bằng các mẫu câu sẵn có) cho các trường hợp hỏi linh tinh mà không cần huy động đến LLM."""
        normalized = self._normalize_space(message).lower()
        if any(keyword in normalized for keyword in self.CASUAL_KEYWORDS):
            return "Chào bạn, mình luôn sẵn sàng hỗ trợ. Bạn cần mình tư vấn gì ngay bây giờ?"
        return (
            "Mình có thể hỗ trợ cả trao đổi thông tin chung lẫn tư vấn chỗ ở. "
            "Nếu bạn đang tìm nơi lưu trú, hãy cho mình điểm đến và ngân sách để mình gợi ý nhanh nhất."
        )

    def _sanitize_children(self, children: list[int] | None) -> list[int] | None:
        """Sàng lọc lại độ tuổi của trẻ em đi cùng, loại bỏ các độ tuổi phi lý dựa trên các ràng buộc nghiệp vụ hợp lệ."""
        if not children:
            return None
        safe_values = [age for age in children if 1 <= age <= 17]
        return safe_values or None


    def _normalize_space(self, text: str) -> str:
        """Làm sạch văn bản bằng cách chuẩn hóa, loại bỏ các khoảng trắng dư thừa giúp thao tác chuỗi ổn định và không bị lỗi."""
        return re.sub(r"\s+", " ", text).strip()

    def _history_text(self, history: list[str]) -> str:
        """Lấy ra một số lượng tin nhắn trong quá khứ gần nhất (Lịch sử chat) để nhúng vào Prompt làm ngữ cảnh giao tiếp cho LLM."""
        if not history:
            return "(no history)"
        normalized_items = [self._normalize_space(item) for item in history if item and self._normalize_space(item)]
        recent_items = normalized_items[-6:]
        return " | ".join(recent_items) if recent_items else "(no history)"

    def _build_casual_reply(self, message: str) -> str:
        """Trả về câu trả lời vui vẻ theo mẫu có sẵn để phản hồi nhanh cho các tình huống chào hỏi, cảm ơn, khen ngợi mang tính xã giao."""
        normalized = self._normalize_space(message).lower()

        if any(keyword in normalized for keyword in self.CASUAL_KEYWORDS):
            return (
                "Chào bạn, mình là trợ lý thông minh của nền tảng lưu trú. Mình có thể trò chuyện tổng quát hoặc "
                "hỗ trợ tìm nơi ở phù hợp theo nhu cầu của bạn."
            )

        return (
            "Mình luôn sẵn sàng hỗ trợ bạn. Nếu bạn muốn tìm nơi lưu trú, chỉ cần cho mình điểm đến và ưu tiên của bạn."
        )

    def _embed_clarification_in_answer(self, answer: str, clarification_question: str | None, requires_more_info: bool) -> str:
        """Gộp câu hỏi làm rõ vào nội dung trả lời để FE chỉ cần render `answer`."""
        if not requires_more_info:
            return answer

        question = self._normalize_space(clarification_question or "")
        if not question:
            return answer

        normalized_answer = self._normalize_space(answer)
        if question in normalized_answer:
            return answer

        separator = "\n\n" if "\n" not in answer else "\n"
        return f"{answer}{separator}{question}"


chatbot_service = ChatbotService()
