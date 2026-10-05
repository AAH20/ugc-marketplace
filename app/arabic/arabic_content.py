"""Basic Arabic content generation for the MENA market.

Minimal scope: Arabic detection, RTL wrapping, template-based marketing
copy, and a FastAPI endpoint. No dialect awareness, cultural context, or
typography rules.
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/arabic", tags=["arabic"])

# Arabic Unicode block: U+0600–U+06FF (plus common extensions U+0750–U+077F,
# U+08A0–U+08FF, U+FB50–U+FDFF, U+FE70–U+FEFF).
_ARABIC_RANGES = (
    (0x0600, 0x06FF),
    (0x0750, 0x077F),
    (0x08A0, 0x08FF),
    (0xFB50, 0xFDFF),
    (0xFE70, 0xFEFF),
)

# Simple Arabic marketing templates. {prompt} is replaced with user input.
_TEMPLATES = (
    "اكتشف {prompt} الآن! عروض حصرية لفترة محدودة — اطلب اليوم واستفد من أفضل الأسعار.",
    "لا تفوت الفرصة! {prompt} بين يديك مع جودة عالية وخدمة متميزة. تواصل معنا الآن.",
    "يسعدنا أن نقدم لك {prompt}. تجربة استثنائية بانتظارك — سجل الآن واستمتع بالمزايا.",
)


def is_arabic(text: str) -> bool:
    """Return True if text contains at least one Arabic-script character."""
    if not text:
        return False
    return any(
        any(start <= ord(ch) <= end for start, end in _ARABIC_RANGES)
        for ch in text
    )


def wrap_rtl(text: str) -> str:
    """Wrap text in an HTML span with dir=rtl and lang=ar."""
    return f'<span dir="rtl" lang="ar">{text}</span>'


def generate_marketing_copy(prompt: str) -> str:
    """Generate Arabic marketing copy from a prompt using a simple template.

    Raises ValueError if the prompt is empty or whitespace-only.
    """
    if not prompt or not prompt.strip():
        raise ValueError("prompt must not be empty")
    # Deterministic template choice based on prompt length.
    template = _TEMPLATES[len(prompt) % len(_TEMPLATES)]
    return template.format(prompt=prompt.strip())


class GenerateRequest(BaseModel):
    """Request body for the generate endpoint."""

    prompt: str = Field(..., min_length=1, description="Prompt to base the copy on")


class GenerateResponse(BaseModel):
    """Response body for the generate endpoint."""

    prompt: str
    content: str
    is_arabic: bool
    rtl_html: str


@router.post("/generate", response_model=GenerateResponse)
def generate(request: GenerateRequest):
    """Generate Arabic marketing copy for the given prompt."""
    try:
        content = generate_marketing_copy(request.prompt)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    return GenerateResponse(
        prompt=request.prompt,
        content=content,
        is_arabic=is_arabic(content),
        rtl_html=wrap_rtl(content),
    )
