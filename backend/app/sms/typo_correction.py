"""Deterministic typo correction for TrafficSMS command words only."""

from __future__ import annotations

from dataclasses import dataclass


COMMAND_DICTIONARY = (
    "TRAFFIC",
    "HELP",
    "START",
    "STOP",
    "SUBSCRIBE",
    "POLICE",
)

EXACT_MANAGEMENT_COMMANDS = {
    "SAVE", "ROUTE", "ROUTES", "LIST", "DELETE", "REMOVE",
}


@dataclass(frozen=True)
class TypoCorrectionResult:
    """The command-word correction decision for a normalized inbound message."""

    corrected_text: str
    original_command: str | None
    corrected_command: str | None
    edit_distance: int | None
    confidence: float
    applied: bool
    rejected: bool


class TypoCorrectionService:
    """Correct only high-confidence first-token command spelling mistakes."""

    def __init__(
        self,
        *,
        max_edit_distance: int,
        confidence_threshold: float,
        command_dictionary: tuple[str, ...] = COMMAND_DICTIONARY,
    ):
        """Configure deterministic correction policy and valid command words."""

        self._max_edit_distance = max_edit_distance
        self._confidence_threshold = confidence_threshold
        self._command_dictionary = command_dictionary

    def correct(self, normalized_text: str) -> TypoCorrectionResult:
        """Return a correction only when the nearest command is unambiguous."""

        tokens = normalized_text.split()
        if not tokens:
            return TypoCorrectionResult(
                corrected_text=normalized_text,
                original_command=None,
                corrected_command=None,
                edit_distance=None,
                confidence=0.0,
                applied=False,
                rejected=False,
            )

        command = tokens[0]
        if command in self._command_dictionary or command in EXACT_MANAGEMENT_COMMANDS:
            return TypoCorrectionResult(
                corrected_text=normalized_text,
                original_command=command,
                corrected_command=command,
                edit_distance=0,
                confidence=1.0,
                applied=False,
                rejected=False,
            )

        candidate, distance = self._nearest_command(command)
        confidence = self._confidence(command, candidate, distance)
        within_edit_limit = distance <= self._max_edit_distance
        accepted = within_edit_limit and confidence >= self._confidence_threshold
        rejected = within_edit_limit and not accepted

        if accepted:
            tokens[0] = candidate

        return TypoCorrectionResult(
            corrected_text=" ".join(tokens) if accepted else normalized_text,
            original_command=command,
            corrected_command=candidate,
            edit_distance=distance,
            confidence=confidence,
            applied=accepted,
            rejected=rejected,
        )

    def _nearest_command(self, command: str) -> tuple[str, int]:
        """Return the stable nearest dictionary command by edit distance."""

        scored = sorted(
            (
                damerau_levenshtein_distance(command, candidate),
                candidate,
            )
            for candidate in self._command_dictionary
        )
        distance, candidate = scored[0]
        return candidate, distance

    @staticmethod
    def _confidence(command: str, candidate: str, distance: int) -> float:
        """Score correction quality relative to the longer compared command."""

        length = max(len(command), len(candidate), 1)
        return max(0.0, 1.0 - (distance / length))


def damerau_levenshtein_distance(source: str, target: str) -> int:
    """Compute unrestricted Damerau-Levenshtein distance using dynamic programming."""

    source_length = len(source)
    target_length = len(target)
    matrix_size = source_length + target_length
    distances = [[0] * (target_length + 2) for _ in range(source_length + 2)]
    distances[0][0] = matrix_size

    for source_index in range(source_length + 1):
        distances[source_index + 1][0] = matrix_size
        distances[source_index + 1][1] = source_index
    for target_index in range(target_length + 1):
        distances[0][target_index + 1] = matrix_size
        distances[1][target_index + 1] = target_index

    last_seen: dict[str, int] = {}
    for source_index in range(1, source_length + 1):
        last_matching_index = 0
        for target_index in range(1, target_length + 1):
            previous_source_index = last_seen.get(target[target_index - 1], 0)
            previous_target_index = last_matching_index
            substitution_cost = 0
            if source[source_index - 1] == target[target_index - 1]:
                last_matching_index = target_index
            else:
                substitution_cost = 1

            distances[source_index + 1][target_index + 1] = min(
                distances[source_index][target_index]
                + substitution_cost,
                distances[source_index + 1][target_index] + 1,
                distances[source_index][target_index + 1] + 1,
                distances[previous_source_index][previous_target_index]
                + (source_index - previous_source_index - 1)
                + 1
                + (target_index - previous_target_index - 1),
            )
        last_seen[source[source_index - 1]] = source_index

    return distances[source_length + 1][target_length + 1]
