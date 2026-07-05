from pathlib import Path

STACK_SOURCE = (
    Path(__file__).resolve().parents[1] / "cdk" / "stacks" / "novelty_stack.py"
).read_text()


def test_novelty_worker_can_retry_and_consume_user_docmodel() -> None:
    assert '"DOCSURI_DOCMODEL_BUCKET"' in STACK_SOURCE
    assert '"DOCSURI_DOCMODEL_BUILD_QUEUE_URL"' in STACK_SOURCE
    assert "docsuri-docmodel-queue" in STACK_SOURCE

    assert "queue.grant_send_messages(task_def.task_role)" in STACK_SOURCE
    assert 'actions=["sqs:SendMessage"]' in STACK_SOURCE
    assert "docsuri-docmodel-queue" in STACK_SOURCE

    assert 'actions=["s3:GetObject"]' in STACK_SOURCE
    assert '/doc-model/*"' in STACK_SOURCE
