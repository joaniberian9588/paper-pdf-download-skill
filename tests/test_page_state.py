from paper_pdf.page_state import PageState, assess_page


def test_challenge_beats_generic_page_text() -> None:
    assessment = assess_page(
        "Just a moment...", "https://publisher.example/article", "Verify you are human"
    )
    assert assessment.state == PageState.CHALLENGE_REQUIRED


def test_auth_is_detected_from_identity_url_not_sign_in_header() -> None:
    assert (
        assess_page("Article", "https://idp.example.edu/login", "Welcome").state
        == PageState.AUTH_REQUIRED
    )
    assert (
        assess_page("Article", "https://publisher.example/article", "Sign in | Download PDF").state
        == PageState.READY
    )


def test_block_and_not_found_states() -> None:
    assert assess_page("Access denied", "https://x.example", "").state == PageState.BLOCKED
    assert (
        assess_page("Article", "https://x.example", "Article not found").state
        == PageState.NOT_FOUND
    )
