"""Tune quiz selection here; weights are recalculated from saved answer counts."""

import math

CORRECT_MULTIPLIER = 0.8
INCORRECT_MULTIPLIER = 1.5
# Keep every word selectable and avoid numeric overflow after long histories.
MIN_WEIGHT = 0.000001
MAX_WEIGHT = 1000000.0

def _word_weight(correct: int = 0, incorrect: int = 0) -> float:
    if incorrect > 0:
        return 1.0
    else:
        return 0

def word_weight(correct: int = 0, incorrect: int = 0) -> float:
    """Start at 1; multiply by 0.8 per correct and 1.5 per incorrect answer.

    Edit this function or the constants above to tune future quizzes. Counts
    include this profile's answers for the word across all quiz levels.
    """
    if correct < 0 or incorrect < 0:
        raise ValueError("Answer counts cannot be negative.")
    log_weight = (correct * math.log(CORRECT_MULTIPLIER)
                  + incorrect * math.log(INCORRECT_MULTIPLIER))
    return math.exp(max(math.log(MIN_WEIGHT), min(math.log(MAX_WEIGHT), log_weight)))
