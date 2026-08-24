"""Deterministic-first SMS intent resolution with safe AI fallback."""

from __future__ import annotations

import re

from app.core.config import get_settings
from app.sms.context import SMSContext
from app.sms.conversation import SMSConversationMemory
from app.sms.entity_catalog import EntityCatalog, entity_catalog
from app.sms.entities import extract_traffic_entities
from app.sms.intents import SMSIntent
from app.sms.models import SMSParseResult
from app.sms.providers.mock_provider import MockLLMIntentProvider
from app.sms.providers.provider import AIIntentResult, LLMIntentProvider
from app.sms.synonyms import SMSSynonymDictionary
from app.sms.typo_correction import TypoCorrectionService
from app.services.saved_route_service import SavedRouteService


_VOTE_COMMAND_RE = re.compile(r"P\d+")
_SAVED_LOCATION_INTENTS = {
    "HOME": SMSIntent.TRAFFIC_HOME,
    "WORK": SMSIntent.TRAFFIC_WORK,
    "GYM": SMSIntent.TRAFFIC_GYM,
    "SCHOOL": SMSIntent.TRAFFIC_SCHOOL,
}
_SIMPLE_INTENTS = {
    "HELP": SMSIntent.HELP,
    "START": SMSIntent.START,
    "STOP": SMSIntent.STOP,
    "SUBSCRIBE": SMSIntent.SUBSCRIBE,
    "POLICE": SMSIntent.POLICE_REPORT,
}


class SMSIntentResolver:
    """Choose the final SMS intent without letting AI bypass known commands."""

    def __init__(
        self,
        *,
        provider: LLMIntentProvider | None = None,
        synonym_dictionary: SMSSynonymDictionary | None = None,
        entity_catalog_instance: EntityCatalog | None = None,
        typo_correction_service: TypoCorrectionService | None = None,
        conversation_memory: SMSConversationMemory | None = None,
        confidence_threshold: float | None = None,
    ):
        """Configure replaceable fallback components and acceptance policy."""

        settings = get_settings()
        self._provider = provider or MockLLMIntentProvider()
        self._entity_catalog = entity_catalog_instance or entity_catalog
        self._synonym_dictionary = synonym_dictionary or SMSSynonymDictionary(
            self._entity_catalog
        )
        self._typo_correction_service = (
            typo_correction_service
            or TypoCorrectionService(
                max_edit_distance=settings.typo_correction_max_edit_distance,
                confidence_threshold=settings.typo_correction_threshold,
            )
        )
        self._conversation_memory = conversation_memory or SMSConversationMemory(
            settings.sms_conversation_ttl_seconds
        )
        self._confidence_threshold = (
            settings.llm_intent_confidence_threshold
            if confidence_threshold is None
            else confidence_threshold
        )

    async def resolve(self, context: SMSContext) -> SMSIntent:
        """Return the final intent after deterministic and fallback evaluation."""

        correction = self._typo_correction_service.correct(context.normalized_text)
        context.metadata["typo_correction_confidence"] = correction.confidence
        if correction.applied:
            context.metadata["typo_corrected"] = {
                "from": correction.original_command,
                "to": correction.corrected_command,
                "distance": correction.edit_distance,
            }
        if correction.rejected:
            context.metadata["typo_correction_rejected"] = True
            return self._return_unknown(context)

        if self._is_explicit_saved_route_command(correction.corrected_text):
            context.resolved_text = correction.corrected_text
        elif self._is_existing_saved_route_reference(context, correction.corrected_text):
            context.resolved_text = correction.corrected_text
        elif not self._apply_catalog_resolution(context, correction.corrected_text):
            context.metadata["unresolved_entities"] = list(
                self._entity_catalog.resolve(context.resolved_text or "").unresolved_targets
            )
            return self._return_unknown(context)
        context.conversation = self._conversation_memory.get(
            context.phone_number,
            context.timestamp,
        )

        deterministic_intent = self.resolve_deterministic(
            self._parse_resolved_text(context)
        )
        if deterministic_intent is not None:
            return self._finalize(
                context,
                deterministic_intent,
                source="deterministic",
            )

        conversation_resolution = self._conversation_memory.resolve_follow_up(
            phone_number=context.phone_number,
            normalized_text=context.resolved_text,
            timestamp=context.timestamp,
        )
        if conversation_resolution is not None:
            context.entities.update(conversation_resolution.entities)
            if not self._apply_catalog_resolution(
                context,
                conversation_resolution.command_text,
            ):
                return self._return_unknown(context)
            return self._finalize(
                context,
                conversation_resolution.intent,
                source="conversation",
            )

        ai_result = await self._provider.resolve(context)
        context.ai_result = ai_result
        context.entities.update(ai_result.entities)
        if self._accept_ai_result(ai_result):
            if self._apply_catalog_resolution(context, ai_result.command_text):
                candidate_intent = self.resolve_deterministic(
                    self._parse_resolved_text(context)
                )
                if candidate_intent is not None:
                    return self._finalize(
                        context,
                        candidate_intent,
                        source="ai",
                    )

        if ai_result.entities:
            context.conversation = self._conversation_memory.record(
                phone_number=context.phone_number,
                command_text=ai_result.command_text,
                entities=context.entities,
                timestamp=context.timestamp,
            )
        return self._return_unknown(context, ai_confidence=ai_result.confidence)

    def resolve_deterministic(self, parsed: SMSParseResult) -> SMSIntent | None:
        """Return a high-confidence deterministic intent or ``None``."""

        if not parsed.tokens:
            return None

        command = parsed.tokens[0]
        simple_intent = _SIMPLE_INTENTS.get(command)
        if simple_intent is not None:
            return simple_intent
        if command == "TRAFFIC":
            return self._resolve_traffic(parsed.arguments)
        if command == "ROUTE" and parsed.arguments:
            return SMSIntent.TRAFFIC_SAVED_ROUTE
        if command == "SAVE" and parsed.arguments[:1] == ("ROUTE",):
            return SMSIntent.SAVE_ROUTE
        if command == "ROUTES" or (command == "LIST" and parsed.arguments == ("ROUTES",)):
            return SMSIntent.LIST_ROUTES
        if command in {"DELETE", "REMOVE"} and parsed.arguments[:1] == ("ROUTE",) and len(parsed.arguments) > 1:
            return SMSIntent.DELETE_ROUTE
        if _VOTE_COMMAND_RE.fullmatch(command) and len(parsed.arguments) == 1:
            return SMSIntent.POLICE_VOTE
        return None

    @staticmethod
    def _resolve_traffic(arguments: tuple[str, ...]) -> SMSIntent | None:
        if not arguments:
            return SMSIntent.TRAFFIC
        if arguments[0] == "ROUTE" and len(arguments) > 1:
            return SMSIntent.TRAFFIC_SAVED_ROUTE
        if arguments[0] == "FROM":
            return None
        route_separator_count = arguments.count("TO")
        if route_separator_count == 1:
            route_separator_index = arguments.index("TO")
            if route_separator_index == 0 or route_separator_index == len(arguments) - 1:
                return None
            return SMSIntent.TRAFFIC_ROUTE
        if route_separator_count > 1:
            return None
        return _SAVED_LOCATION_INTENTS.get(arguments[0], SMSIntent.TRAFFIC_ROUTE)

    @staticmethod
    def _is_explicit_saved_route_command(text: str) -> bool:
        """Keep route-management commands out of the geographic entity catalog."""

        tokens = text.split()
        return bool(
            (tokens[:1] == ["ROUTE"] and len(tokens) > 1)
            or (tokens[:2] == ["TRAFFIC", "ROUTE"] and len(tokens) > 2)
            or tokens[:2] == ["SAVE", "ROUTE"]
            or tokens[:1] == ["ROUTES"]
            or tokens[:2] == ["LIST", "ROUTES"]
            or (tokens[:2] in (["DELETE", "ROUTE"], ["REMOVE", "ROUTE"]) and len(tokens) > 2)
        )

    @staticmethod
    def _is_existing_saved_route_reference(context: SMSContext, text: str) -> bool:
        """Allow implicit ``TRAFFIC <alias>`` only when that private alias exists."""

        if context.user is None or not hasattr(context.db, "scalar"):
            return False
        tokens = text.split()
        if tokens[:1] != ["TRAFFIC"] or len(tokens) < 2 or "TO" in tokens:
            return False
        if tokens[1] in _SAVED_LOCATION_INTENTS or tokens[1] == "ROUTE":
            return False
        return SavedRouteService(context.db).get_by_alias(
            context.user.id, " ".join(tokens[1:]), sms_only=True
        ) is not None

    def _apply_catalog_resolution(
        self,
        context: SMSContext,
        text: str,
    ) -> bool:
        """Apply catalog aliases and reject deterministic traffic unknowns."""

        synonym_resolution = self._synonym_dictionary.resolve(text)
        context.resolved_text = synonym_resolution.normalized_text
        context.entities.update(synonym_resolution.entities)
        entity_resolution = self._entity_catalog.resolve(context.resolved_text)
        context.resolved_text = entity_resolution.normalized_text
        context.entities.update(entity_resolution.entities)
        return not entity_resolution.unresolved_targets

    @staticmethod
    def _return_unknown(
        context: SMSContext,
        *,
        ai_confidence: float | None = None,
    ) -> SMSIntent:
        """Set the stable unknown outcome without bypassing resolver authority."""

        context.metadata["intent_source"] = "unknown"
        if ai_confidence is not None:
            context.metadata["ai_confidence"] = ai_confidence
        context.intent = SMSIntent.UNKNOWN
        return SMSIntent.UNKNOWN

    def _finalize(
        self,
        context: SMSContext,
        intent: SMSIntent,
        *,
        source: str,
    ) -> SMSIntent:
        """Record an accepted traffic interpretation and expose its source."""

        context.intent = intent
        context.metadata["intent_source"] = source
        if context.resolved_text:
            context.entities.update(extract_traffic_entities(context.resolved_text))
        if intent in {
            SMSIntent.TRAFFIC,
            SMSIntent.TRAFFIC_HOME,
            SMSIntent.TRAFFIC_WORK,
            SMSIntent.TRAFFIC_GYM,
            SMSIntent.TRAFFIC_SCHOOL,
            SMSIntent.TRAFFIC_ROUTE,
        }:
            context.conversation = self._conversation_memory.record(
                phone_number=context.phone_number,
                command_text=context.resolved_text,
                entities=context.entities,
                timestamp=context.timestamp,
            )
        return intent

    def _accept_ai_result(self, result: AIIntentResult) -> bool:
        """Accept only complete, high-confidence, typed AI candidates."""

        return bool(
            result.detected_intent is not None
            and result.command_text
            and result.confidence >= self._confidence_threshold
        )

    @staticmethod
    def _parse_resolved_text(context: SMSContext) -> SMSParseResult:
        """Expose synonym or AI canonical text to deterministic intent rules."""

        normalized_text = context.resolved_text or context.normalized_text
        tokens = tuple(normalized_text.split()) if normalized_text else ()
        return SMSParseResult(
            raw_text=context.raw_text,
            normalized_text=normalized_text,
            tokens=tokens,
            arguments=tokens[1:],
        )
