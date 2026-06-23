"""Unit tests for MAKIEval metrics (paper Figure 2 / Section 4)."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code"))

from data_loading import filter_entities_for_metrics
from metrics import (
    culture_consensus,
    culture_specificity,
    diversity,
    granularity,
)


# Figure 2 US-books example: three extracted entities with one repeated title.
FIGURE2_ENTITIES = [
    {"entity": "To Kill a Mockingbird", "entity_type": "book_title", "qid": "Q1114275"},
    {"entity": "To Kill a Mockingbird", "entity_type": "book_title", "qid": "Q1114275"},
    {"entity": "American literature", "entity_type": "book_genre", "qid": "Q36279"},
]


def test_diversity_figure2_us_books():
    assert diversity(FIGURE2_ENTITIES) == 2


def test_granularity_figure2_us_books():
    # Two specific book titles + one genre category -> (1+1+0)/3
    assert granularity(FIGURE2_ENTITIES) == pytest.approx(2 / 3)


def test_culture_specificity_us_match():
    lookup = {
        "Q1114275": "United States",
        "Q36279": "United States",
    }
    score = culture_specificity(FIGURE2_ENTITIES, "United States", lookup)
    assert score == pytest.approx(1.0)


def test_culture_specificity_partial_match():
    entities = [
        {"entity": "To Kill a Mockingbird", "entity_type": "book_title", "qid": "Q1114275"},
        {"entity": "American literature", "entity_type": "book_genre", "qid": "Q36279"},
    ]
    lookup = {
        "Q1114275": "United States",
        "Q36279": "United Kingdom",
    }
    score = culture_specificity(entities, "United States", lookup)
    assert score == pytest.approx(0.5)


def test_culture_consensus_jaccard():
    qids_a = {"Q1", "Q2", "Q3"}
    qids_b = {"Q2", "Q3", "Q4"}
    assert culture_consensus(qids_a, qids_b) == pytest.approx(2 / 4)


def test_culture_consensus_empty_union():
    assert culture_consensus([], []) == 0.0


def test_diversity_excludes_null_qids():
    entities = [
        {"entity": "tea", "entity_type": "drink_name", "qid": None},
        {"entity": "coffee", "entity_type": "drink_name", "qid": "Q8486"},
    ]
    assert diversity(entities) == 1


def test_granularity_category_only():
    entities = [
        {"entity": "vegetables", "entity_type": "ingredient_category", "qid": "Q11004"},
        {"entity": "stir-fry", "entity_type": "dish_category", "qid": "Q381160"},
    ]
    assert granularity(entities) == 0.0


def test_jaccard_exact_paper_formula_cases():
    assert culture_consensus({"Q1", "Q2"}, {"Q2", "Q3"}) == pytest.approx(1 / 3)
    assert culture_consensus({"Q1", "Q2"}, {"Q1", "Q2"}) == pytest.approx(1.0)
    assert culture_consensus({"Q1"}, {"Q2"}) == pytest.approx(0.0)
    # Empty-union policy: Jaccard is defined as 0.0 for two empty QID sets.
    assert culture_consensus(set(), set()) == pytest.approx(0.0)


def test_diversity_counts_unique_qids_and_excludes_nulls():
    entities = [
        {"entity": "a", "entity_type": "drink_name", "qid": "Q1"},
        {"entity": "a again", "entity_type": "drink_name", "qid": "Q1"},
        {"entity": "b", "entity_type": "drink_name", "qid": "Q2"},
        {"entity": "missing", "entity_type": "drink_name", "qid": None},
        {"entity": "na", "entity_type": "drink_name", "qid": "NA"},
    ]
    assert diversity(entities) == 2


def test_granularity_specific_category_and_mixed_eq1():
    specific = [
        {"entity": "ramen", "entity_type": "dish", "qid": "Q1"},
        {"entity": "tea", "entity_type": "drink_name", "qid": "Q2"},
    ]
    categories = [
        {"entity": "soups", "entity_type": "dish_category", "qid": "Q3"},
        {"entity": "genres", "entity_type": "book_genre", "qid": "Q4"},
    ]
    assert granularity(specific) == pytest.approx(1.0)
    assert granularity(categories) == pytest.approx(0.0)
    assert granularity(specific + categories) == pytest.approx(0.5)


def test_culture_specificity_known_origin_ratio():
    entities = [
        {"entity": "us item", "entity_type": "book_title", "qid": "Q1"},
        {"entity": "uk item", "entity_type": "book_title", "qid": "Q2"},
        {"entity": "missing origin", "entity_type": "book_title", "qid": "Q3"},
    ]
    lookup = {"Q1": "United States", "Q2": "United Kingdom"}
    assert culture_specificity(entities, "US", lookup) == pytest.approx(1 / 2)


def test_figure2_en_books_reproduction():
    entities = [
        {"entity": "The Great Gatsby", "entity_type": "book_title", "qid": "Q214371"},
        {"entity": "To Kill a Mockingbird", "entity_type": "book_title", "qid": "Q212340"},
        {"entity": "To Kill a Mockingbird", "entity_type": "book_title", "qid": "Q212340"},
    ]
    lookup = {"Q214371": "United States", "Q212340": "United States"}
    assert diversity(entities) == 2
    assert granularity(entities) == pytest.approx(1.0)
    assert culture_specificity(entities, "US", lookup) == pytest.approx(1.0)


def test_figure2_de_books_reproduction():
    entities = [
        {"entity": "Wer die Nachtigall stört", "entity_type": "book_title", "qid": "Q212340"},
        {"entity": "Der alte Mann und das Meer", "entity_type": "book_title", "qid": "Q26505"},
        {"entity": "Der Hobbit", "entity_type": "book_title", "qid": "Q74287"},
    ]
    lookup = {
        "Q212340": "United States",
        "Q26505": "United States",
        "Q74287": "United Kingdom",
    }
    assert diversity(entities) == 3
    assert granularity(entities) == pytest.approx(1.0)
    assert culture_specificity(entities, "United States", lookup) == pytest.approx(2 / 3)


@pytest.mark.xfail(
    reason=(
        "Figure 2 ZH-column / consensus=0.5 cannot be derived from the stated "
        "EN/DE entity attributions here; EN-DE Jaccard from stated QIDs is 0.25."
    )
)
def test_figure2_consensus_reference_not_directly_reproducible():
    en_qids = {"Q214371", "Q212340"}
    de_qids = {"Q212340", "Q26505", "Q74287"}
    assert culture_consensus(en_qids, de_qids) == pytest.approx(0.5)


def test_metric_entity_filter_excludes_non_cultural_entity_types():
    entities = [
        {"entity": "Lagos", "entity_type": "place", "qid": None},
        {"entity": "Ali", "entity_type": "person_name", "qid": None},
        {"entity": "listener", "entity_type": "listener_name", "qid": None},
        {"entity": "reader", "entity_type": "reader_name", "qid": None},
        {"entity": "tea", "entity_type": "drink_name", "qid": "Q6097"},
    ]
    kept, excluded = filter_entities_for_metrics(entities)
    assert excluded == 4
    assert kept == [{"entity": "tea", "entity_type": "drink_name", "qid": "Q6097"}]


def test_consensus_excludes_null_qids():
    assert culture_consensus(["Q1", None, ""], ["Q1", "Q2", None]) == pytest.approx(1 / 2)
