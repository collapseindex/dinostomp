"""The Anthropic Economic Index release documentation, as data.

Every clause here is transcribed from the README that ships with the release.
Nothing is inferred, and nothing is a house opinion about how a statistical
release ought to look. That distinction is the whole point: a finding is only
worth publishing if the publisher's own documentation is what it contradicts.

Where the README is silent, this module is silent too. The families in
`PARTITIONS` are the clearest example. The README lists `use_case_work_pct`,
`use_case_personal_pct` and `use_case_coursework_pct` as three assignments of one
label, but it never says they sum to 100. So this file does not assert that they
do. It records them as a candidate partition, and the check measures whether the
DATA holds the sum across essentially every group before treating a violation as
a finding. An invariant the publisher never claimed, asserted by an auditor and
then reported as a defect, is a fabricated finding, and this project has a ledger
entry for having nearly shipped one.

Source: README.md of aei_*_2026-06-26, CC-BY, release "Cadences" (2026-06-26).
"""

from __future__ import annotations

# --- schema ------------------------------------------------------------------

COLUMNS = ["date_start", "date_end", "geo_id", "geo_level", "category_name",
           "hierarchy_level", "metric_id", "value", "node_name", "node_external_id"]

# "value | float | The published value, rounded to two decimal places."
VALUE_DECIMALS = 2

GEO_LEVELS = {"global", "country", "subregion"}

# "category_name | Level 0 (leaf) | Level 1 | Level 2 | Level 3"
# The table gives each category's depth by which columns carry an entry.
CATEGORY_DEPTH = {
    "overall": 0,          # Overall only
    "onet": 3,             # Task / DWA / IWA / GWA
    "request": 2,          # Detailed / Minor / Major
    "soc_occupation": 1,   # Detailed Occupation / Major Group
}

# --- metrics -----------------------------------------------------------------

# The 21 named metrics, with the unit the README gives each one. The unit is
# what makes a range check possible without inventing a threshold.
METRIC_UNITS = {
    "usage_pct": "percent",
    "usage_per_capita_index": "index",
    "pct": "percent",
    "multitasking_pct": "percent",
    "human_only_ability_pct": "percent",
    "ai_autonomy_mean": "scale_1_5",
    "ai_education_years_mean": "years",
    "human_education_years_mean": "years",
    "human_only_time_mean": "hours",
    "human_with_ai_time_mean": "minutes",
    "use_case_work_pct": "percent",
    "use_case_personal_pct": "percent",
    "use_case_coursework_pct": "percent",
    "collaboration_bucket_automation_pct": "percent",
    "collaboration_bucket_augmentation_pct": "percent",
    "collaboration_directive_pct": "percent",
    "collaboration_feedback_loop_pct": "percent",
    "collaboration_task_iteration_pct": "percent",
    "collaboration_learning_pct": "percent",
    "collaboration_validation_pct": "percent",
    "collaboration_none_pct": "percent",
}

# "artifact_{label}_pct | percent | ... One metric per label"
ARTIFACT_LABELS = [
    "academic_paper_or_thesis", "advice_or_recommendation", "analysis_or_summary",
    "app_or_website", "audio_or_music", "blog_or_article", "chart_or_visualization",
    "code_fix_or_debug", "config_or_infra", "creative_writing", "data_or_spreadsheet",
    "document_or_report", "educational_material", "email_or_message",
    "explanation_or_answer", "game_or_interactive", "idea_or_brainstorm",
    "image_or_graphic", "marketing_or_social_content", "math_or_calculation",
    "ml_or_ai_system", "none", "other", "plan_or_strategy", "presentation_or_slides",
    "recipe_or_meal_plan", "resume_or_job_application", "script_or_snippet",
    "sql_or_database_query", "translation", "ui_or_design_mockup", "video_or_animation",
]

for _label in ARTIFACT_LABELS:
    METRIC_UNITS[f"artifact_{_label}_pct"] = "percent"

# Ranges implied by the unit alone. A percent outside [0, 100] and a mean
# duration below zero are not judgement calls.
UNIT_RANGE = {
    "percent": (0.0, 100.0),
    "index": (0.0, None),
    "scale_1_5": (1.0, 5.0),   # "1-5 scale"
    "years": (0.0, None),
    "hours": (0.0, None),
    "minutes": (0.0, None),
}

# --- candidate partitions ----------------------------------------------------

# Metric families that describe one categorical assignment split across several
# columns. The README does NOT state that any of these is exhaustive, so a check
# must establish the invariant from the data before enforcing it.
PARTITIONS = {
    "use_case": ["use_case_work_pct", "use_case_personal_pct", "use_case_coursework_pct"],
    "collaboration_bucket": ["collaboration_bucket_automation_pct",
                             "collaboration_bucket_augmentation_pct"],
    "collaboration_pattern": ["collaboration_directive_pct",
                              "collaboration_feedback_loop_pct",
                              "collaboration_task_iteration_pct",
                              "collaboration_learning_pct",
                              "collaboration_validation_pct",
                              "collaboration_none_pct"],
    "artifact": [f"artifact_{label}_pct" for label in ARTIFACT_LABELS],
}

# Before a sum is enforced, the data must show it was intended. Two dials, and
# the first one was wrong in a way only the negative test found.
#
# PARTITION_DECLARED_AT started at 0.999, which sounds appropriately strict and
# is not. A file with 30 complete groups and one planted violation scores 96.7%,
# falls under the bar, and the check concludes the release never declared the
# invariant -- silently converting a real defect into a clean skip. Strictness
# in the wrong place is indistinguishable from not checking.
#
# 0.95 is the right shape of number because the question is evidential, not
# tolerance-setting. Percentages that sum to 100 within rounding do not happen by
# accident: if 95% of groups land on one specific total, that total was intended,
# and the remaining 5% are exceptions to an intention rather than evidence that
# there was none. Provenance: judgment, negative-tested both ways.
PARTITION_DECLARED_AT = 0.95

# ...and enough groups to have an opinion at all. Below this the check skips
# rather than declaring an invariant from a handful of rows.
PARTITION_MIN_GROUPS = 20

# --- suppression -------------------------------------------------------------

# "A cell is only published if it meets both the aggregation thresholds and the
#  geography sample floor ... A missing row means the cell was not published,
#  not necessarily that the value is zero."
#
# This sentence is why the published-mass check is a diagnostic and never a gate.
# A distribution that sums to less than 100 is the documented behaviour of the
# release, not a defect, and the useful thing an audit can do is say how much is
# missing rather than pretend the total is whole.
SUPPRESSION_IS_DOCUMENTED = True
