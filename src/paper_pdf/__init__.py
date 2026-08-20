"""Silent, verified retrieval and optional conversion of research-paper PDFs."""

from .models import PaperResult, RetrievalStatus, VerificationReport

__all__ = ["PaperResult", "RetrievalStatus", "VerificationReport"]
__version__ = "0.1.0"
