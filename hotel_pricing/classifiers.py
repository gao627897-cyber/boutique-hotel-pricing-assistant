"""Non-AI event baseline and an explicitly unavailable classifier.

No stage 2 class makes API calls or pretends to be an LLM. The keyword baseline
is deliberately limited; stage 3/4 will measure its semantic weaknesses.
"""

import re

from .domain import ClassificationAttempt, ClassificationError, EventContext


class KeywordClassifier:
    name = "keyword_baseline"
    version = "keywords-0.2"
    mode = "non_ai_baseline"
    HIGH = (r"\bf1\b", r"\bformula\s*1\b", r"\binternational concert\b", r"\binternational convention\b", r"国际大型")
    MEDIUM = (r"\bregional festival\b", r"\btrade fair\b", r"\bexhibition\b", r"区域节庆", r"展览")
    LOW = (r"\bcommunity fair\b", r"\bneighbou?rhood market\b", r"\bno (?:local )?events\b", r"社区市集", r"无活动")
    UNCERTAIN = (
        r"\bcancell?ed\b", r"\bpostponed\b", r"\brumou?r\b", r"\bunconfirmed\b",
        r"取消", r"传言", r"未确认", r"忽略.{0,12}(?:规则|指令)",
        r"\bignore.{0,30}(?:instruction|rule)", r"\bsystem prompt\b",
    )

    def classify(self, context: EventContext) -> ClassificationAttempt:
        text = context.event_description.casefold()
        if any(re.search(pattern, text) for pattern in self.UNCERTAIN):
            result = {"impact": "uncertain", "reason": "Keyword baseline found an uncertainty or instruction marker; verify the supplied text."}
        else:
            matches = [
                label for label, patterns in (
                    ("high", self.HIGH), ("medium", self.MEDIUM), ("low", self.LOW)
                ) if any(re.search(pattern, text) for pattern in patterns)
            ]
            if len(matches) == 1:
                result = {"impact": matches[0], "reason": f"Keyword baseline matched {matches[0]} activity terms; it has not verified the event."}
            else:
                result = {"impact": "uncertain", "reason": "Keyword baseline found no single unambiguous category."}
        return ClassificationAttempt(result)


class UnavailableClassifier:
    name = "unavailable"
    version = "stage2"
    mode = "unavailable"

    def classify(self, context: EventContext) -> ClassificationAttempt:
        raise ClassificationError(
            "CLASSIFIER_UNAVAILABLE",
            "No activity classifier is connected. Stage 4 must connect and evaluate a real LLM.",
        )
