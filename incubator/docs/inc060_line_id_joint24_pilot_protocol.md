# INC-060: Source-Line-ID Grounded Joint-24 Pilot

INC-060 tests the opposite of INC-054: retain source-grounded reasoning while
replacing free-text evidence with flat original-line IDs.  It uses the exact
INC-054 48-notice cohort, complete ordered documents, item definitions, model,
seed, and two-repeat design.  Each non-absence positive requires one numbered
source line; absence items have no evidence field.  The only changed variable
is evidence transport.  A source ID is valid only if it resolves to an
unchanged line no longer than 500 characters.  The output reserve is 512 from
INC-059's observed serialization requirement.

This is a diagnostic against fixed INC-041 rows on the same cohort. Advance
requires both repeats to exceed that reference by 0.05 Macro F1, complete
source-ID validity, and no completion over 512. A pass still requires a later
all-dev repeated evidence-aware confirmation.
