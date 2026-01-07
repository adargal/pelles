import re
import unicodedata
from dataclasses import dataclass

from app.schemas import ProductCandidate, ConfidenceLevel
from app.config import settings


@dataclass
class MatchResult:
    product: ProductCandidate
    score: float
    confidence: ConfidenceLevel
    warning: str | None = None


def normalize_hebrew(text: str) -> str:
    """
    Normalize Hebrew text for comparison.
    - Removes niqqud (vowel marks)
    - Normalizes final letter forms
    - Lowercases
    - Removes extra whitespace
    """
    if not text:
        return ""

    # Remove niqqud and other diacritical marks
    # Hebrew niqqud range: U+0591 to U+05C7
    text = "".join(
        char for char in text if not (0x0591 <= ord(char) <= 0x05C7)
    )

    # Normalize final forms to regular forms
    final_to_normal = {
        "ך": "כ",
        "ם": "מ",
        "ן": "נ",
        "ף": "פ",
        "ץ": "צ",
    }
    for final, normal in final_to_normal.items():
        text = text.replace(final, normal)

    # Unicode normalization
    text = unicodedata.normalize("NFKC", text)

    # Lowercase (for any English mixed in)
    text = text.lower()

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def tokenize(text: str) -> list[str]:
    """Split text into tokens, filtering short ones."""
    normalized = normalize_hebrew(text)
    # Split on whitespace and punctuation
    tokens = re.split(r"[\s\-_,./]+", normalized)
    # Filter tokens shorter than 2 chars
    return [t for t in tokens if len(t) >= 2]


def calculate_match_score(query: str, product_name: str) -> float:
    """
    Calculate how well a product name matches the query.
    Returns a score between 0 and 1.
    """
    query_normalized = normalize_hebrew(query)
    product_normalized = normalize_hebrew(product_name)

    if not query_normalized or not product_normalized:
        return 0.0

    # Exact match bonus
    if query_normalized == product_normalized:
        return 1.0

    # Substring match bonus
    substring_bonus = 0.0
    if query_normalized in product_normalized:
        substring_bonus = 0.3

    # Token-based scoring
    query_tokens = tokenize(query)
    product_tokens = tokenize(product_name)

    if not query_tokens:
        return substring_bonus

    # Count how many query tokens appear in product tokens
    matched_tokens = 0
    for qt in query_tokens:
        for pt in product_tokens:
            # Check for exact token match or if query token is contained in product token
            if qt == pt or qt in pt or pt in qt:
                matched_tokens += 1
                break

    token_coverage = matched_tokens / len(query_tokens)

    # Position bonus: if first token matches first product token
    position_bonus = 0.0
    if query_tokens and product_tokens:
        if query_tokens[0] in product_tokens[0] or product_tokens[0] in query_tokens[0]:
            position_bonus = 0.1

    # Combine scores
    score = min(1.0, token_coverage * 0.7 + substring_bonus + position_bonus)

    return score


def determine_confidence(
    score: float,
    alternatives: list[tuple[ProductCandidate, float]],
) -> ConfidenceLevel:
    """
    Determine confidence level based on match score and alternatives.
    """
    if score >= settings.match_high_threshold:
        # Check if there are close alternatives
        if alternatives:
            second_best_score = alternatives[0][1] if alternatives else 0
            if second_best_score > score * 0.95:
                return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.HIGH

    if score >= settings.match_medium_threshold:
        return ConfidenceLevel.MEDIUM

    return ConfidenceLevel.LOW


def generate_warning(
    query: str,
    product: ProductCandidate,
    score: float,
    confidence: ConfidenceLevel,
    alternatives: list[tuple[ProductCandidate, float]],
) -> str | None:
    """Generate a warning message if needed."""
    warnings = []

    if confidence == ConfidenceLevel.LOW:
        warnings.append("Low confidence match")

    if confidence == ConfidenceLevel.MEDIUM:
        # Check for close alternatives
        if alternatives and alternatives[0][1] > score * 0.9:
            warnings.append("Multiple similar products found")

    # Check for potential substitution indicators
    query_lower = normalize_hebrew(query)
    product_lower = normalize_hebrew(product.name)

    # Common Hebrew words that suggest brand/type differences
    if "%" in product.name and "%" not in query:
        warnings.append("Fat percentage specified in product")

    # Size might be different than expected
    if product.size_descriptor:
        size_lower = product.size_descriptor.lower()
        if any(word in size_lower for word in ["גדול", "קטן", "מיני", "xl", "xxl"]):
            warnings.append(f"Note: {product.size_descriptor}")

    return "; ".join(warnings) if warnings else None


def find_best_match(
    query: str,
    candidates: list[ProductCandidate],
) -> MatchResult | None:
    """
    Find the best matching product for a query from a list of candidates.
    """
    if not candidates:
        return None

    # Score all candidates
    scored = [(product, calculate_match_score(query, product.name)) for product in candidates]

    # Sort by score descending
    scored.sort(key=lambda x: x[1], reverse=True)

    best_product, best_score = scored[0]
    alternatives = scored[1:5]  # Keep top 4 alternatives

    confidence = determine_confidence(best_score, alternatives)
    warning = generate_warning(query, best_product, best_score, confidence, alternatives)

    return MatchResult(
        product=best_product,
        score=best_score,
        confidence=confidence,
        warning=warning,
    )
