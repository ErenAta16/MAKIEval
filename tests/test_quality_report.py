import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code"))

from quality_report import QualityState, build_report, process_row


def test_missing_qid_counts_separate_all_types_from_cultural_only():
    state = QualityState()
    row = {
        "model": "Model-A",
        "topic": "book",
        "language": "en",
        "country_region": "united states",
        "generated_text": "",
        "entities": json.dumps(
            [
                {"entity": "Lagos", "entity_type": "place", "qid": None},
                {"entity": "Ali", "entity_type": "person_name", "qid": ""},
                {"entity": "tea", "entity_type": "drink_name", "qid": None},
                {"entity": "novel", "entity_type": "book_title", "qid": "Q1"},
            ]
        ),
    }

    process_row(state, row)

    assert state.overall.entity_count_all_types == 4
    assert state.overall.missing_qid_all_types == 3
    assert state.overall.entity_count_cultural_only == 2
    assert state.overall.missing_qid_cultural_only == 1

    topic_stats = state.by_topic["book"]
    assert topic_stats.missing_qid_all_types == 3
    assert topic_stats.missing_qid_cultural_only == 1


def test_quality_report_marks_cultural_metric_as_table_10_comparable():
    state = QualityState()
    state.overall.rows = 1

    report = build_report(state, "test")

    assert "missing_qid_cultural_only" in report
    assert "missing_qid_all_types" in report
    assert "Table 10-comparable" in report
