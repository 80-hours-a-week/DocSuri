"""Regression tests for PR2 user doc-model coordinator fixes (review of #392)."""

from __future__ import annotations

from urllib.parse import unquote

from backend.modules.user_docmodel import UserDocModelCoordinator, user_docmodel_ref


def _ref():
    return user_docmodel_ref(
        owner_id="acct-1",
        scope_id="scope-1",
        attachment_id="att-1",
        object_key="uploads/evidence/acct-1/scope-1/att-1/doc.pdf",
        module="evidence",
    )


class _RaisingReader:
    def get_doc_model(self, paper_id, version):
        raise RuntimeError("simulated AccessDenied / throttle / parse error")


class _CapturingS3:
    def __init__(self):
        self.calls: list[dict] = []

    def put_object(self, **kwargs):
        self.calls.append(kwargs)


def test_poll_doc_model_degrades_when_reader_raises() -> None:
    # get_doc_model raises on non-miss S3 errors; readiness polling must degrade to None,
    # never propagate and 500 the async evidence/research request paths (best-effort contract).
    coord = UserDocModelCoordinator(
        bucket="b",
        s3_client=_CapturingS3(),
        doc_model_reader=_RaisingReader(),
        poll_timeout_seconds=0.0,
        poll_interval_seconds=0.01,
    )

    assert coord.poll_doc_model(_ref()) is None


def test_upload_pdf_metadata_is_ascii_for_unicode_filename() -> None:
    # S3 object metadata must be US-ASCII; a Korean filename must not make put_object throw.
    s3 = _CapturingS3()
    coord = UserDocModelCoordinator(bucket="b", s3_client=s3)

    coord.upload_pdf(_ref(), b"%PDF-1.4 body", file_name="논문 초안.pdf")

    file_name_meta = s3.calls[0]["Metadata"]["file-name"]
    assert file_name_meta.isascii()
    assert unquote(file_name_meta) == "논문 초안.pdf"
