from scripts.audit_candidate_semantic_contract import final_messages_for_record


class _AdaptivePreviewPipeline:
    active_items = ("v1", "v10")

    def effective_pipeline_for_record(self, record):
        return self, {}

    def contexts_for_record(self, record):
        return ["first source pack", "second source pack"]

    def messages_for_context(self, record, context):
        return [
            {"role": "system", "content": "card"},
            {"role": "user", "content": context},
        ]


def test_candidate_semantic_preview_preserves_every_admitted_context() -> None:
    messages = final_messages_for_record(
        _AdaptivePreviewPipeline(), {"id": "fixture"}, staged_mode=None
    )

    assert [message_set[1]["content"] for message_set in messages] == [
        "first source pack",
        "second source pack",
    ]
