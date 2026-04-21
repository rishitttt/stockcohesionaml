import unittest

from nifty200_pipeline.promoters import classify_promoter_payload, classifier_for_name


ACC_JUN_2022 = [
    {"COL_I": "AMBUJA CEMENTS LIMITED", "ENTITY_TYPE": "Promoter", "COL_IX_Total": "93984120"},
    {"COL_I": "HOLDERIND INVESTMENTS LTD", "ENTITY_TYPE": "Promoter", "COL_IX_Total": "8411000"},
]


ACC_SEP_2022 = [
    {"COL_I": "AMBUJA CEMENTS LIMITED", "ENTITY_TYPE": "Promoter", "COL_IX_Total": "93984120"},
    {"COL_I": "HOLDERIND INVESTMENTS LTD", "ENTITY_TYPE": "Promoter", "COL_IX_Total": "8411000"},
    {"COL_I": "ENDEAVOUR TRADE AND INVESTMENT LIMITED", "ENTITY_TYPE": "Promoter", "COL_IX_Total": "4051465"},
]

LEGACY_ABB = [
    {"category": "e", "COL_I": "Any Other (specify)", "ENTITY_TYPE": "-", "COL_IX_Total": "158931281"},
    {"category": " ", "COL_I": "Bodies Corporate", "ENTITY_TYPE": "-", "COL_IX_Total": "158931281"},
    {"category": " ", "COL_I": "ABB Asea Brown Boveri Limited", "ENTITY_TYPE": "-", "COL_IX_Total": "146390951"},
    {"category": " ", "COL_I": "ABB Norden Holding AB", "ENTITY_TYPE": "-", "COL_IX_Total": "12540330"},
]

LEGACY_RELIANCE = [
    {"category": "a", "COL_I": "Mukesh D Ambani", "ENTITY_TYPE": "-", "COL_IX_Total": "7776010"},
    {"category": " ", "COL_I": "Srichakra Commercials LLP", "ENTITY_TYPE": "-", "COL_IX_Total": "714247552"},
    {"category": " ", "COL_I": "Reliance Industries Holding Private Ltd", "ENTITY_TYPE": "-", "COL_IX_Total": "280776291"},
]


class PromoterClassifierTests(unittest.TestCase):
    def test_classifier_maps_named_groups(self) -> None:
        self.assertEqual(classifier_for_name("TATA SONS PRIVATE LIMITED"), "Tata")
        self.assertEqual(classifier_for_name("ADANI ENTERPRISES LIMITED"), "Adani")
        self.assertEqual(classifier_for_name("President of India"), "GOI_PSU")
        self.assertEqual(classifier_for_name("AMBUJA CEMENTS LIMITED"), "Independent")

    def test_acc_transition_is_not_marked_adani_too_early(self) -> None:
        jun_group, jun_entity, _ = classify_promoter_payload(ACC_JUN_2022)
        sep_group, sep_entity, _ = classify_promoter_payload(ACC_SEP_2022)
        self.assertEqual(jun_group, "Independent")
        self.assertEqual(jun_entity, "AMBUJA CEMENTS LIMITED")
        self.assertEqual(sep_group, "Adani")
        self.assertEqual(sep_entity, "ENDEAVOUR TRADE AND INVESTMENT LIMITED")

    def test_legacy_blank_entity_type_rows_still_classify(self) -> None:
        group, entity, _ = classify_promoter_payload(LEGACY_ABB)
        self.assertEqual(group, "Independent")
        self.assertEqual(entity, "ABB Asea Brown Boveri Limited")

    def test_reliance_can_be_identified_from_legacy_names(self) -> None:
        group, entity, _ = classify_promoter_payload(LEGACY_RELIANCE)
        self.assertEqual(group, "Reliance")
        self.assertEqual(entity, "Reliance Industries Holding Private Ltd")


if __name__ == "__main__":
    unittest.main()
