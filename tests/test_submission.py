from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

from src.pipeline import judgment_to_row
from src.schema import ITEMS
from src.submission import validate_submission, write_submission


def _record() -> dict:
    return {
        "id": "PPS-TEST",
        "docs": [{"doc_id": "D0", "type": "공고문", "text": "원문 근거 문장"}],
        "meta": {},
        "dropped_doc_counts": {},
        "input_completeness": {"fully_observed": True},
        "anon_applied": True,
        "assembly_policy_version": "test",
    }


def _row() -> dict:
    judgment = {item: {"위반여부": 0, "근거문구": ""} for item in ITEMS}
    judgment["v1"] = {"위반여부": 1, "근거문구": "원문 근거"}
    return judgment_to_row("PPS-TEST", judgment)


def test_valid_submission_passes(tmp_path) -> None:
    path = tmp_path / "submission.csv"
    write_submission([_row()], path)
    result = validate_submission(path, [_record()])
    assert result.passed
    assert not result.warnings


def test_non_source_evidence_fails(tmp_path) -> None:
    row = _row()
    row["e1"] = "요약된 근거"
    path = tmp_path / "submission.csv"
    write_submission([row], path)
    result = validate_submission(path, [_record()])
    assert not result.passed
    assert any("exact source substring" in error for error in result.errors)


def test_submission_retries_a_malformed_structured_candidate() -> None:
    script_path = Path(__file__).resolve().parents[1] / "submission" / "script.py"
    spec = importlib.util.spec_from_file_location("submission_script_for_test", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    valid = json.dumps(
        {item: {"위반여부": 0, "근거문구": None} for item in ITEMS},
        ensure_ascii=False,
    )

    class Client:
        calls = 0

        def complete_batch(self, batch, response_schema):
            del response_schema
            self.calls += 1
            if self.calls == 2:
                return [module.Completion(valid, "test", 0.0, {}) for _ in batch]
            return [module.Completion("not JSON", "test", 0.0, {}) for _ in batch]

    outputs, retries = module._complete_group_with_json_retries(
        Client(), [[{"role": "user", "content": "공고"}]], {}, batch_retries=0
    )

    assert retries == 1
    assert outputs[0].content == valid


def test_submission_retries_a_transient_batch_failure() -> None:
    script_path = Path(__file__).resolve().parents[1] / "submission" / "script.py"
    spec = importlib.util.spec_from_file_location("submission_script_batch_retry", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    valid = module.Completion("{}", "test", 0.0, {})

    class Client:
        calls = 0

        def complete_batch(self, batch, response_schema):
            del response_schema
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("temporary vLLM failure")
            return [valid for _ in batch]

    outputs = module._complete_batch_with_retries(
        Client(), [[{"role": "user", "content": "공고"}]], {}, batch_retries=1
    )
    assert outputs == [valid]


def test_submission_mock_client_has_a_full_split_admission_counter() -> None:
    script_path = Path(__file__).resolve().parents[1] / "submission" / "script.py"
    spec = importlib.util.spec_from_file_location("submission_script_mock_counter", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    assert module.MockClient().count_tokens([{"content": "가나다"}]) == 3


def test_submission_normalizes_disabled_quantization_without_importing_vllm() -> None:
    script_path = Path(__file__).resolve().parents[1] / "submission" / "script.py"
    spec = importlib.util.spec_from_file_location("submission_script_quantization", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    assert module._normalized_quantization("none") is None
    assert module._normalized_quantization(" NONE ") is None
    assert module._normalized_quantization("") is None
    assert module._normalized_quantization(None) is None
    assert module._normalized_quantization("int8_per_channel_weight_only") == (
        "int8_per_channel_weight_only"
    )
    assert "quantization" not in module._vllm_init_options("/model", "none")
    assert module._vllm_init_options("/model", "int8")["quantization"] == "int8"


def test_submission_runtime_uses_documented_batch_128_default() -> None:
    runtime_path = Path(__file__).resolve().parents[1] / "submission" / "runtime_config.json"
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    assert runtime["runtime"]["batch_size"] == 128


def test_submission_group_json_retry_uses_the_group_item_subset() -> None:
    script_path = Path(__file__).resolve().parents[1] / "submission" / "script.py"
    spec = importlib.util.spec_from_file_location("submission_script_group_subset", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    content = json.dumps({"v10": {"위반여부": 0, "근거문구": None}}, ensure_ascii=False)

    class Client:
        calls = 0

        def complete_batch(self, batch, response_schema):
            del response_schema
            self.calls += 1
            return [module.Completion(content, "test", 0.0, {}) for _ in batch]

    client = Client()
    outputs, retries = module._complete_group_with_json_retries(
        client, [[{"role": "user", "content": "공고"}]], {}, batch_retries=0, items=("v10",)
    )
    assert retries == 0
    assert client.calls == 1
    assert outputs[0].content == content


def test_submission_runtime_forwards_official_baseline_metadata_style() -> None:
    script_path = Path(__file__).resolve().parents[1] / "submission" / "script.py"
    spec = importlib.util.spec_from_file_location("submission_script_prompt_contract", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    item_table = {
        item: {"항목명": item, "부재탐지": False, "비고": ""}
        for item in ITEMS
    }
    pipeline = module.build_submission_pipeline(
        item_table=item_table,
        client=module.MockClient(),
        decision_cards=None,
        competition_products=None,
    )
    record = _record()
    record["meta"] = {"적용계약법": "국가계약법", "배정예산금액": None}
    message = pipeline.messages_for_context(record, None)[1]["content"]
    assert "- 적용계약법: 국가계약법" in message
    assert "- 배정예산금액: 미기재" in message
    assert '"적용계약법"' not in message


def test_submission_runtime_forwards_corrected_semantic_input_modes(
    monkeypatch,
) -> None:
    script_path = Path(__file__).resolve().parents[1] / "submission" / "script.py"
    spec = importlib.util.spec_from_file_location(
        "submission_script_semantic_input_contract", script_path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    monkeypatch.setitem(
        module.PROMPT_CONFIG,
        "competition_product_context_mode",
        "conditions_and_provenance_v2",
    )
    monkeypatch.setitem(
        module.PROMPT_CONFIG,
        "organizer_input_semantics_mode",
        "anonymization_v1",
    )
    monkeypatch.setitem(
        module.PROMPT_CONFIG,
        "metadata_style",
        "official_lines_human_v2",
    )
    item_table = {
        item: {"항목명": item, "부재탐지": False, "비고": ""}
        for item in ITEMS
    }
    products = {
        "9015189001": {
            "세부품명": "축제기획및대행서비스",
            "제품명번호": "901518",
            "제품명": "축제",
            "특이사항": "추정가격 3억원 미만에 한함",
        }
    }
    pipeline = module.build_submission_pipeline(
        item_table=item_table,
        client=module.MockClient(),
        decision_cards=None,
        competition_products=products,
    )
    record = _record()
    record["meta"] = {
        "세부품명번호목록": "축제기획및대행서비스[9015189001]"
    }
    message = pipeline.messages_for_context(record, None)[1]["content"]

    assert pipeline.competition_product_context_mode == "conditions_and_provenance_v2"
    assert pipeline.organizer_input_semantics_mode == "anonymization_v1"
    assert pipeline.metadata_style == "official_lines_human_v2"
    assert "추정가격 3억원 미만에 한함" in message
    assert "[주최 측 입력 표기 규약]" in message
    assert "9015189001" not in message
