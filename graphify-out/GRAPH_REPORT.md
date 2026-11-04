# Graph Report - .  (2026-11-04)


## Summary
- 4346 nodes · 13124 edges · 190 communities (159 shown, 31 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 1893 edges (avg confidence: 0.79)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Document Parsing
- Document Parsing
- API Layer
- UI Components
- Document Parsing
- Document Parsing
- API Layer
- Frontend Pages
- API Layer
- Test Coverage
- Document Parsing
- API Layer
- API Layer
- API Layer
- Backend Services
- API Layer
- Test Coverage
- Document Parsing
- Test Coverage
- API Layer
- Document Parsing
- Document Parsing
- Test Coverage
- ML Scripts
- Test Coverage
- Data Storage
- Test Coverage
- Test Coverage
- Test Coverage
- Document Parsing
- Test Coverage
- Test Coverage
- CUAD Evaluation
- Document Parsing
- Test Coverage
- Test Coverage
- Document Parsing
- Frontend Pages
- API Layer
- Test Coverage
- API Layer
- Test Coverage
- CUAD Evaluation
- Test Coverage
- Test Coverage
- Backend Services
- Data Storage
- Test Coverage
- CUAD Evaluation
- Data Storage
- API Layer
- Document Parsing
- Document Parsing
- Test Coverage
- Test Coverage
- Test Coverage
- Data Storage
- Frontend Application
- Document Parsing
- API Layer
- Test Coverage
- Parser Contract
- Test Fixtures
- Model Calibration
- Test Coverage
- Test Coverage
- Analysis Pipeline
- Test Fixtures
- Document Parsing
- Analysis Pipeline
- Backend Services
- UI Components
- CUAD Evaluation
- Test Coverage
- Test Coverage
- UI Components
- Candidate Analyzer
- Test Coverage
- API Layer
- CUAD Evaluation
- API Layer
- CUAD Evaluation
- Model Calibration
- Test Coverage
- Test Coverage
- Test Coverage
- Document Parsing
- Document Parsing
- Backend Services
- UI Components
- Analysis Pipeline
- CUAD Evaluation
- Test Coverage
- CUAD Evaluation
- Test Coverage
- Test Coverage
- API Layer
- Document Parsing
- Document Start Flow
- CUAD Evaluation
- API Layer
- Backend Services
- Test Coverage
- Document Start Flow
- Test Coverage
- API Layer
- API Layer
- API Layer
- Test Coverage
- Test Coverage
- Test Coverage
- API Layer
- API Layer
- Parser Contract
- ML Scripts
- Test Coverage
- Test Coverage
- Test Coverage
- Test Coverage
- Backend Services
- Parser Contract
- Parser Contract
- Parser Contract
- Test Coverage
- Backend Services
- Test Fixtures
- Test Fixtures
- Test Coverage
- Test Coverage
- CUAD Evaluation
- Parser Contract
- Document Start Flow
- Frontend Application
- Test Fixtures
- Test Fixtures
- Test Coverage
- Parser Contract
- API Layer
- Test Coverage
- CUAD Evaluation
- Analysis Pipeline
- Test Coverage
- Data Storage
- Test Coverage
- Test Coverage
- Test Coverage
- Test Coverage
- API Layer
- API Layer
- UI Components
- CUAD Evaluation
- Analysis Pipeline
- Test Coverage
- Data Storage
- Test Coverage
- Test Coverage
- API Layer
- Candidate Analyzer
- Frontend Application
- Test Fixtures
- Architecture
- Test Coverage
- Candidate Analyzer
- Machine Learning
- Test Fixtures
- Machine Learning
- UI Components
- Frontend Pages
- Test Fixtures
- Test Fixtures
- Test Fixtures
- Test Fixtures
- Test Fixtures
- Parser Contract
- UI Components
- Test Fixtures
- Test Fixtures
- Backend Runtime
- Backend Runtime
- Backend Runtime
- Test Coverage
- Test Coverage
- Test Coverage
- Test Coverage

## God Nodes (most connected - your core abstractions)
1. `Structure` - 93 edges
2. `ParsedDocument` - 70 edges
3. `parse_pdf` - 67 edges
4. `Application Store` - 54 edges
5. `parse_docx` - 51 edges
6. `ParseError` - 50 edges
7. `build_docx()` - 50 edges
8. `Labels` - 48 edges
9. `parse_document()` - 47 edges
10. `Atomic Json` - 47 edges

## Surprising Connections (you probably didn't know these)
- `Candidate Prototype v0` --semantically_similar_to--> `client`  [INFERRED] [semantically similar]
  docs/ml/ReleaseHandoff.md → frontend/src/api/client.ts
- `Python 3.12 Runtime` --conceptually_related_to--> `Settings`  [INFERRED]
  README.md → backend/app/config.py
- `Memory-Only Sessions and Documents` --conceptually_related_to--> `create_app`  [INFERRED]
  README.md → backend/app/main.py
- `Real Analyzer Mode` --conceptually_related_to--> `create_app`  [INFERRED]
  README.md → backend/app/main.py
- `PDF and DOCX Parsing Pipeline` --conceptually_related_to--> `parse_document`  [INFERRED]
  README.md → backend/app/parsing/__init__.py

## Import Cycles
- 1-file cycle: `backend/app/parsing/docx.py -> backend/app/parsing/docx.py`

## Hyperedges (group relationships)
- **Document Parsing Flow** — backend_app_api_routes_upload_document, backend_app_parse_worker_run, parsing_parse_document, backend_app_parsing_model_parseddocument, backend_app_parsing_structure_build_structure [EXTRACTED 1.00]
- **Canonical Contract Representation** — backend_app_parsing_assemble_textassembler, backend_app_parsing_model_parseddocument, backend_app_parsing_model_structurenode, backend_app_parsing_schema_to_json, backend_app_parsing_schema_from_json [EXTRACTED 1.00]
- **API Readiness and Session Boundary** — backend_app_main_create_app, backend_app_api_routes_ready, backend_app_api_auth_require_session, backend_app_api_routes_read_document, backend_app_api_errors_error_envelope [INFERRED 0.85]
- **Bounded Parse and Analysis Execution** — backend_app_services_parse_jobs_parsequeue, backend_app_services_memcap_cappedprocess, backend_app_services_analysis_jobs_analysisqueue, backend_app_services_store_store [INFERRED 0.85]
- **Store Content Lifecycle** — backend_app_services_store_store, backend_app_services_store_ram_text_storage, backend_app_services_store_sqlite_metadata, backend_app_services_store_documentrecord, backend_app_services_store_session, backend_app_services_store_jobrecord [INFERRED 0.95]
- **Test Structure Test Suite** — backend_tests_test_structure_test_decimal_labels_nest_by_their_number_of_parts, backend_tests_test_structure_test_a_node_ends_where_the_next_node_at_its_level_or_above_starts, backend_tests_test_structure_test_a_node_ends_at_the_last_body_block_it_covers, backend_tests_test_structure_test_a_node_that_spans_a_page_break_holds_the_page_furniture_between_its_blocks, backend_tests_test_structure_test_blocks_that_are_not_body_text_never_start_a_node, backend_tests_test_structure_test_letters_sit_one_level_below_the_nearest_decimal_node, backend_tests_test_structure_test_a_letter_with_no_decimal_node_sits_below_the_nearest_open_node, backend_tests_test_structure_test_i_under_b_is_a_roman_numeral_one_level_below_the_letter, backend_tests_test_structure_test_i_after_h_is_the_next_letter, backend_tests_test_structure_test_a_numeral_that_continues_both_ways_is_a_letter_with_a_warning, backend_tests_test_structure_test_the_ambiguity_warning_names_the_page_of_the_block, backend_tests_test_structure_test_doubled_letters_follow_z, backend_tests_test_structure_test_a_number_that_does_not_continue_a_sequence_stays_body_text, backend_tests_test_structure_test_a_block_that_is_only_a_bare_number_is_a_page_number_not_a_clause, backend_tests_test_structure_test_a_decimal_label_has_up_to_five_parts_of_up_to_three_digits, backend_tests_test_structure_test_a_doubled_letter_is_the_only_multi_letter_label, backend_tests_test_structure_test_a_label_with_a_full_stop_and_nothing_else_is_still_a_label, backend_tests_test_structure_test_a_label_may_run_straight_into_its_title, backend_tests_test_structure_test_a_restart_inside_a_long_run_is_a_list_and_not_a_new_sequence, backend_tests_test_structure_test_a_short_numbered_party_list_does_not_take_the_clause_numbers, backend_tests_test_structure_test_a_restart_replaces_a_run_of_three_but_not_a_run_of_four, backend_tests_test_structure_test_a_restart_that_replaced_a_short_run_can_be_replaced_in_turn, backend_tests_test_structure_test_a_decimal_must_carry_the_number_of_the_open_decimal_above_it, backend_tests_test_structure_test_a_deeper_decimal_may_skip_a_level_that_has_no_node, backend_tests_test_structure_test_letters_restart_under_each_clause_even_after_a_long_run, backend_tests_test_structure_test_a_wrapped_cross_reference_does_not_cut_the_clause, backend_tests_test_structure_test_a_sequence_may_start_with_a_subnumber_when_the_parent_is_not_a_node, backend_tests_test_structure_test_a_sequence_survives_a_heading_between_its_members, backend_tests_test_structure_test_contents_entries_never_become_nodes, backend_tests_test_structure_test_a_block_that_wraps_onto_a_number_is_not_a_contents_entry, backend_tests_test_structure_test_a_roman_heading_followed_by_a_lower_case_word_is_running_text, backend_tests_test_structure_test_a_trail_of_three_dots_is_not_a_dot_leader, backend_tests_test_structure_test_a_contents_list_does_not_use_up_the_numbers, backend_tests_test_structure_test_a_numbered_line_ending_in_a_year_is_not_a_contents_entry, backend_tests_test_structure_test_a_heading_word_that_ends_in_its_own_number_is_not_a_contents_entry, backend_tests_test_structure_test_article_and_roman_headings_are_level_one_headings, backend_tests_test_structure_test_a_numbered_section_heading_uses_its_part_count, backend_tests_test_structure_test_an_all_caps_line_is_an_unnumbered_level_one_heading_that_closes_open_nodes, backend_tests_test_structure_test_a_line_that_is_not_a_short_all_caps_line_is_not_a_heading, backend_tests_test_structure_test_a_short_two_line_title_in_capitals_is_one_heading [EXTRACTED 1.00]
- **Test Docx Test Suite** — backend_tests_test_docx_test_unsafe_names_are_recognised_after_backslashes_become_slashes, backend_tests_test_docx_test_the_name_check_runs_before_any_member_is_read, backend_tests_test_docx_test_the_size_limit_is_inclusive_and_counts_the_bytes_read, backend_tests_test_docx_test_the_limit_stops_a_member_in_the_middle_of_its_output, backend_tests_test_docx_test_a_member_that_lies_about_its_size_is_cut_short_and_refused, backend_tests_test_docx_test_the_library_is_handed_every_member_stored_at_its_real_size, backend_tests_test_docx_test_a_member_that_lies_and_matches_its_checksum_is_cut_and_handed_over_stored, backend_tests_test_docx_test_a_member_whose_compressed_data_ends_early_is_malformed, backend_tests_test_docx_test_an_encrypted_member_is_malformed, backend_tests_test_docx_test_a_member_that_is_neither_stored_nor_deflated_is_unsafe, backend_tests_test_docx_test_bytes_that_are_not_a_package_are_malformed, backend_tests_test_docx_test_a_package_without_a_main_document_is_malformed, backend_tests_test_docx_test_a_document_part_with_no_body_is_malformed, backend_tests_test_docx_test_overlapping_entries_are_malformed, backend_tests_test_docx_test_a_warning_from_the_archive_reader_does_not_escape, backend_tests_test_docx_test_each_library_error_type_maps_to_malformed_file, backend_tests_test_docx_test_an_error_outside_the_tuple_is_not_hidden, backend_tests_test_docx_test_an_element_named_ins_in_another_namespace_is_not_a_tracked_change, backend_tests_test_docx_test_text_inside_a_wrapper_is_read_once_with_no_warning, backend_tests_test_docx_test_an_unknown_block_is_skipped_with_a_warning_and_partial, backend_tests_test_docx_test_section_properties_and_table_properties_raise_no_warning, backend_tests_test_docx_test_a_wrapper_around_whole_paragraphs_is_seen_through, backend_tests_test_docx_test_markers_between_blocks_raise_no_warning, backend_tests_test_docx_test_an_unknown_child_of_a_table_or_a_row_is_skipped_with_a_warning, backend_tests_test_docx_test_alternate_content_yields_the_box_once_right_after_its_anchor, backend_tests_test_docx_test_bare_vml_yields_each_box_once_and_numbers_them_in_order, backend_tests_test_docx_test_a_box_inside_a_box_is_numbered_before_the_rest_of_its_outer_box, backend_tests_test_docx_test_a_box_in_a_cell_splits_the_cell_text_around_it, backend_tests_test_docx_test_an_embedded_object_sets_partial_and_warns, backend_tests_test_docx_test_tables_are_numbered_and_empty_cells_are_skipped, backend_tests_test_docx_test_text_before_and_after_a_nested_table_is_flushed_as_separate_blocks, backend_tests_test_docx_test_style_linked_numbering_labels_paragraphs_that_carry_no_numpr, backend_tests_test_docx_test_composite_labels_and_the_restart_of_deeper_levels, backend_tests_test_docx_test_a_style_chain_gives_the_list_and_the_level_from_different_styles, backend_tests_test_docx_test_a_paragraph_with_no_style_takes_the_default_paragraph_style, backend_tests_test_docx_test_a_level_whose_text_is_blank_gives_no_label, backend_tests_test_docx_test_numbers_and_levels_are_read_strictly, backend_tests_test_docx_test_numid_zero_switches_off_a_list_the_style_gives, backend_tests_test_docx_test_start_values_and_start_overrides, backend_tests_test_docx_test_a_level_with_no_start_begins_at_zero [EXTRACTED 1.00]
- **Test Pdf Test Suite** — backend_tests_test_pdf_test_detect_type_names_a_pdf_and_a_docx, backend_tests_test_pdf_test_detect_type_finds_the_pdf_header_in_the_first_1024_bytes, backend_tests_test_pdf_test_a_package_that_mentions_a_pdf_header_is_still_a_docx, backend_tests_test_pdf_test_detect_type_rejects_with_a_fixed_code, backend_tests_test_pdf_test_simple_pdf_gives_numbered_clauses_as_blocks_with_page_separators, backend_tests_test_pdf_test_block_bboxes_sit_inside_the_page_and_wrap_the_text, backend_tests_test_pdf_test_two_columns_read_left_column_then_right_after_a_full_width_title, backend_tests_test_pdf_test_a_wrapped_paragraph_stays_one_block_and_spacing_starts_the_next, backend_tests_test_pdf_test_a_word_hyphenated_across_a_line_break_is_left_as_it_is, backend_tests_test_pdf_test_ligatures_survive_and_space_runs_and_nbsp_become_single_spaces, backend_tests_test_pdf_test_hanging_indents_keep_a_clause_together_and_a_return_to_the_edge_starts_a_block, backend_tests_test_pdf_test_a_blank_page_adds_no_block_and_keeps_the_page_numbers, backend_tests_test_pdf_test_a_page_that_opens_on_an_indented_tail_still_splits_later_hanging_paragraphs, backend_tests_test_pdf_test_a_first_line_indent_does_not_cut_a_paragraph_after_its_first_line, backend_tests_test_pdf_test_page_numbers_far_right_stay_on_their_row_and_raise_no_warning, backend_tests_test_pdf_test_a_word_with_no_text_is_dropped_before_layout, backend_tests_test_pdf_test_a_table_page_keeps_top_to_bottom_order_and_warns_of_more_than_two_columns, backend_tests_test_pdf_test_a_full_width_line_between_column_rows_warns_that_order_is_uncertain, backend_tests_test_pdf_test_a_gutter_needs_text_on_both_sides_in_two_rows, backend_tests_test_pdf_test_a_gap_between_rows_that_is_never_a_gap_inside_one_row_is_no_gutter, backend_tests_test_pdf_test_the_gutter_scan_grows_with_the_words_and_not_with_their_square, backend_tests_test_pdf_test_a_repeated_header_and_a_numbered_footer_are_decoration_on_every_page, backend_tests_test_pdf_test_a_page_number_is_decoration_even_in_a_one_page_file, backend_tests_test_pdf_test_a_header_on_two_pages_is_text_but_page_numbers_on_them_are_decoration, backend_tests_test_pdf_test_a_repeated_line_needs_three_pages_and_half_the_pages_from_six, backend_tests_test_pdf_test_a_body_line_in_the_margin_is_its_own_text_block, backend_tests_test_pdf_test_a_page_number_that_opens_or_closes_a_page_is_decoration_outside_the_margins, backend_tests_test_pdf_test_a_page_number_in_the_left_half_of_two_columns_is_read_last, backend_tests_test_pdf_test_page_number_shapes, backend_tests_test_pdf_test_a_file_whose_every_page_is_scanned_is_rejected, backend_tests_test_pdf_test_one_scanned_page_among_text_pages_is_a_warning_and_a_partial_read, backend_tests_test_pdf_test_a_page_image_over_a_thin_text_layer_is_partial_not_scanned, backend_tests_test_pdf_test_an_image_that_covers_under_half_the_page_does_not_make_it_scanned, backend_tests_test_pdf_test_a_file_of_blank_pages_has_no_text, backend_tests_test_pdf_test_annotation_text_the_layout_cannot_see_makes_the_read_partial, backend_tests_test_pdf_test_an_owner_password_only_file_parses_like_the_plain_one, backend_tests_test_pdf_test_a_page_of_unmapped_glyphs_keeps_its_text_warns_and_is_partial, backend_tests_test_pdf_test_more_than_a_quarter_of_a_pages_glyphs_must_be_unmapped_to_warn, backend_tests_test_pdf_test_the_share_is_worked_out_for_each_page, backend_tests_test_pdf_test_a_word_counts_each_unmapped_glyph_once_whatever_its_length [EXTRACTED 1.00]
- **Canonical Parser Pipeline** — docs_app_architecture_upload_and_analysis_request_flow, docs_app_parsercontract_parseddocument, docs_app_parser_output_schema_defs_block, docs_app_parser_output_schema_defs_structurenode, docs_app_parsercontract_unicode_code_point_offsets, docs_app_architecture_pdf_reading_order [EXTRACTED 1.00]
- **Candidate-Only Model Governance** — docs_ml_cuad_calibration_frozen_extractor_calibration_assessment, docs_ml_cuad_calibration_offline_sigmoid_calibrator, docs_ml_cuad_candidatepolicy_frozen_candidate_only_operating_policy, docs_ml_cuad_candidatepolicy_disjoint_full_candidate_selection, docs_ml_cuad_cardlyticsfamilyreview_cardlytics_software_agreement_family_review [EXTRACTED 1.00]
- **Annotation Label System** — docs_app_annotationguidelines_annotation_catalogue, docs_app_annotationguidelines_arbitration, docs_app_annotationguidelines_seat_or_venue, docs_app_annotationguidelines_stamping_or_registration, docs_app_annotationguidelines_forum_selection, docs_app_annotationguidelines_dispute_escalation [EXTRACTED 1.00]
- **CUAD Document and Split-Safety Policy** — docs_ml_cuad_crosssplitreview_cross_split_text_review, docs_ml_cuad_remainingcrosssplitreview_remaining_cross_split_review, docs_ml_cuad_remainingtrainingfamilyreview_remaining_training_family_review, docs_ml_cuad_unresolvedhandlingpolicy_unresolved_handling_policy, docs_ml_cuad_datareview_exact_text_deduplication, docs_ml_cuad_unresolvedhandlingpolicy_conservative_hold [INFERRED 0.95]
- **Decoder Quality Evidence Chain** — docs_ml_cuad_decoderexperiment_single_bounded_decoder_experiment, docs_ml_cuad_decoderreview_full_candidate_decoder_review, docs_ml_cuad_sourceerrorreview_source_span_error_review, docs_ml_cuad_finalevaluation_frozen_final_extraction_evaluation, docs_ml_phases_score_quality_diagnostic, docs_ml_cuad_decoderreview_disjoint_full [INFERRED 0.95]
- **Candidate Release Validation Chain** — docs_ml_realanalyzer_real_analyzer_v0, docs_ml_candidateapiintegration_candidate_parser_api_integration, docs_ml_candidaterelease_candidate_release_packaging, docs_ml_candidatereleaseverification_candidate_release_verification, docs_ml_categorycatalogue_category_catalogue, docs_ml_realanalyzer_review_candidate [INFERRED 0.95]
- **Candidate Release Verification and Policy Flow** — docs_ml_releasehandoff_candidate_prototype_v0, docs_ml_releasehandoff_candidate_only_release_policy, docs_ml_releasehandoff_clean_split_roberta_qa, docs_ml_releasehandoff_positive_margin_disjoint_full, docs_ml_releasehandoff_uncalibrated_acceptance_policy [EXTRACTED 1.00]
- **Scope Fixture Application Contract** — docs_ml_scopefixtures_scope_fixture_handoff, docs_ml_scopefixtures_fixture_envelope_1_0, docs_ml_scopefixtures_unicode_span_rules, docs_ml_scopefixtures_incomplete_job_policy, frontend_src_api_types_span, frontend_src_api_types_manualreview [INFERRED 0.95]
- **Reader Review Shell Flow** — frontend_src_components_categorysidebar_categorysidebar, frontend_src_components_clausedetailpanel_clausedetailpanel, frontend_src_components_appheader_appheader, frontend_src_components_appfooter_appfooter [INFERRED 0.85]
- **Keyboard Accessible Dialog Flow** — frontend_src_components_dropdownmenu_dropdownmenu, frontend_src_components_confirmdialog_confirmdialog, frontend_src_components_keyboardhint_keyboardhint, frontend_src_components_dropdownmenu_shared_focus_ring_accessibility [INFERRED 0.85]
- **Manual Review Navigation Flow** — frontend_src_components_manualreviewlist_manualreviewlist, frontend_src_components_manualreviewlist_manualreviewitem, frontend_src_components_segmentedfilter_segmentedfilter, frontend_src_components_offsettag_offsettag, frontend_src_components_spanhighlight_spanhighlight, frontend_src_components_marginruler_marginruler [INFERRED 0.95]
- **Party Role and Polarity Flow** — frontend_src_components_roleselector_roleselector, frontend_src_components_partybindingfield_partybindingfield, frontend_src_components_partybindingfield_partybinding, frontend_src_components_polaritybadge_polaritybadge, frontend_src_components_polaritybadge_polarity_kind [INFERRED 0.95]
- **Review Scope and Uncertainty** — frontend_src_components_scopepanel_scopepanel, frontend_src_components_scopepanel_review_scope, frontend_src_components_noticebanner_noticebanner, frontend_src_components_ruleflagcard_ruleflagcard, frontend_src_components_manualreviewlist_manualreview_state [INFERRED 0.85]
- **Upload Validation and Start Flow** — frontend_src_components_uploaddropzone_uploaddropzone, frontend_src_lib_startflow_initialflow, frontend_src_lib_startflow_flowreducer, frontend_src_lib_startflow_nextblocker, frontend_src_lib_startflow_stale_response_guard [INFERRED 0.85]
- **Reader Accessibility and Motion Handling** — frontend_src_lib_reveal_revealonce, frontend_src_lib_reveal_browserobserver, frontend_src_lib_usemedia_usereducedmotion, frontend_src_lib_usereveal_usereveal, frontend_src_lib_paneltransition_paneltransition [INFERRED 0.85]
- **Reader Text Offset and Party Selection** — frontend_src_lib_offsets_buildoffsetindex, frontend_src_lib_offsets_slicecp, frontend_src_lib_startflow_partyname, lib_startflow_startflowtests [INFERRED 0.85]
- **Contract Review Flow** — frontend_src_pages_start_start, frontend_src_pages_start_usestartflow_usestartflow, frontend_src_pages_start_summary_summary, frontend_src_pages_reader_reader [INFERRED 0.95]
- **Landing Explanation and Demo** — frontend_src_pages_landing_landing, frontend_src_pages_landing_herodemo_herodemo, frontend_src_pages_landing_heroexamples_hero_examples, frontend_src_pages_howitworks_howitworks [INFERRED 0.85]
- **Accuracy and Trust Loop** — frontend_src_pages_accuracy_accuracy, frontend_src_pages_accuracy_glossary, frontend_src_pages_howitworks_sections, frontend_src_pages_reader_reader [INFERRED 0.85]
- **Offline Candidate-Only Inference Flow** — ml_clauseanchor_core_analyzer_candidateonlyanalyzer, ml_clauseanchor_core_inference_featuretokenizer, ml_clauseanchor_core_inference_torchbackend, ml_clauseanchor_core_inference_windowcandidates, ml_clauseanchor_core_inference_disjointcandidates [EXTRACTED 1.00]
- **Versioned Analysis Contract** — ml_clauseanchor_core_contract_analysisresult, ml_clauseanchor_core_contract_categoryresult, ml_clauseanchor_core_contract_clausefinding, ml_clauseanchor_core_contract_span, ml_clauseanchor_core_serialization_todict, ml_clauseanchor_core_serialization_fromdict [EXTRACTED 1.00]
- **CUAD Validation and Evaluation** — configs_family_manifest_familypolicy, configs_splitfreeze_frozenpartition, configs_calibration_unvalidatedcalibration, configs_candidatepolicy_candidateonly, configs_finalevaluation_finalprotocol [EXTRACTED 1.00]
- **Eight Scope Scenario Families** — ml_fixtures_scope_01_supported_and_outside_family_1, ml_fixtures_scope_02_outside_only_family_2, ml_fixtures_scope_03_mixed_paragraph_family_3, ml_fixtures_scope_04_broad_span_family_4, ml_fixtures_scope_05_distant_clauses_family_5, ml_fixtures_scope_06_incomplete_family_6, ml_fixtures_scope_07_positions_family_7, ml_fixtures_scope_08_proposed_category_family_8 [INFERRED 0.85]
- **CUAD Training Window Pipeline** — ml_scripts_prepare_cuad_training_plan_sample_epoch, ml_scripts_prepare_cuad_features_build_shard, ml_scripts_cuad_training_fitwindowdataset, ml_scripts_cuad_training_collate_windows, ml_scripts_cuad_training_joint_marginal_loss, ml_scripts_cuad_training_optimizer_update [INFERRED 0.85]
- **CUAD Feature Verification Chain** — ml_scripts_freeze_cuad_splits_build_bundle, ml_scripts_prepare_cuad_training_assets_verify_local_assets, ml_scripts_prepare_cuad_features_verify_shard, ml_scripts_prepare_cuad_training_plan_audit_features [INFERRED 0.85]
- **CUAD Release and Evaluation Flow** — ml_scripts_cuad_review_policy_validate_review_manifest, ml_scripts_package_candidate_release_build, ml_scripts_evaluate_candidate_policy_run, ml_scripts_cuad_final_evaluation_score_all [INFERRED 0.75]
- **CUAD Baseline Evaluation** — ml_scripts_run_cuad_baseline_run_cuad_baseline, ml_scripts_smoke_cuad_baseline_smoke_cuad_baseline, ml_scripts_validate_cuad_decoder_validate_cuad_decoder, ml_scripts_run_cuad_final_evaluation_run_cuad_final_evaluation [INFERRED 0.85]
- **CUAD Split and Training Flow** — ml_scripts_propose_cuad_splits_propose_cuad_splits, ml_scripts_train_cuad_train_cuad, ml_scripts_validate_cuad_decoder_validate_cuad_decoder [INFERRED 0.85]
- **Candidate Release Validation** — ml_scripts_smoke_candidate_analyzer_smoke_candidate_analyzer, ml_scripts_smoke_candidate_api_smoke_candidate_api, ml_tests_test_candidate_release_test_candidate_release [INFERRED 0.85]
- **CUAD Data and Training Pipeline** — ml_tests_test_cuad_preparation_module, ml_tests_test_cuad_splits_module, ml_tests_test_cuad_families_module, ml_tests_test_cuad_features_module, ml_tests_test_cuad_training_plan_module, ml_tests_test_cuad_training_assets_module, ml_tests_test_cuad_trainer_module, ml_tests_test_cuad_training_module [INFERRED 0.85]
- **CUAD Decoder Validation Pipeline** — ml_tests_test_cuad_development_module, ml_tests_test_cuad_decoder_validation_module, ml_tests_test_cuad_decoder_experiment_module, ml_tests_test_cuad_decoder_review_module, ml_tests_test_cuad_error_review_module, ml_tests_test_cuad_review_policy_module [INFERRED 0.85]
- **CUAD Evaluation and Release Pipeline** — ml_tests_test_cuad_inference_module, ml_tests_test_cuad_evaluation_module, ml_tests_test_cuad_score_diagnostic_module, ml_tests_test_cuad_final_evaluation_module, ml_tests_test_cuad_freeze_module, ml_tests_test_cuad_smoke_module [INFERRED 0.85]
- **ClauseAnchor Favicon Symbol System** — frontend_public_favicon_clauseanchor_favicon, frontend_public_favicon_document_brackets, frontend_public_favicon_balance_scale [EXTRACTED 1.00]

## Communities (190 total, 31 thin omitted)

### Community 0 - "Document Parsing"
Cohesion: 0.06
Nodes (215): parse_docx, abstract_num(), _after_h(), _all_blank(), _alternate_content(), _anchor(), _archive_too_large(), _blank_page() (+207 more)

### Community 1 - "Document Parsing"
Cohesion: 0.05
Nodes (102): parse_document(), Parses one PDF or DOCX held in memory. Raises ParseError with a fixed code when, from_json, _name_span(), _object(), Any, The JSON form of a ParsedDocument and its JSON Schema (docs/app/ParserContract.m, The document as plain data that json.dumps accepts. Without `text` the document (+94 more)

### Community 2 - "API Layer"
Cohesion: 0.04
Nodes (75): Candidate-Only Release Policy, Candidate Prototype v0, Clean-Split RoBERTa QA, Positive-Margin Disjoint Full Decoder, Uncalibrated Acceptance Policy, Scope Fixture Build Log, Fixture Envelope 1.0, Incomplete Job Inventory Policy (+67 more)

### Community 3 - "UI Components"
Cohesion: 0.04
Nodes (73): ButtonIcon, ButtonProps, ButtonSize, ButtonState, ButtonVariant, SIZES, DEFAULT_ITEMS, DropdownMenuProps (+65 more)

### Community 4 - "Document Parsing"
Cohesion: 0.19
Nodes (90): catalogue_file(), _clean_env(), client(), fixture_bytes(), fixtures(), hanging(), make_client(), MonkeyPatch (+82 more)

### Community 5 - "Document Parsing"
Cohesion: 0.27
Nodes (86): parse_pdf, list_pdf(), One page of lines at one left edge and one pitch. Nothing in the geometry separa, A85, Flate stream, Kinds, Make zip, Assert only the blocks differ (+78 more)

### Community 6 - "API Layer"
Cohesion: 0.07
Nodes (86): B, Labels, Outline, Parent labels, ParseWarning, StructureNode, A block with a kind and a locator, for tests that need more than plain text., Structure (+78 more)

### Community 7 - "Frontend Pages"
Cohesion: 0.05
Nodes (49): AppHeader, DEFAULT_LINKS, HeaderVariant, NavLink, Anchor Logomark, Brand Mark, Favicon(), Horizontal Lockup (+41 more)

### Community 8 - "API Layer"
Cohesion: 0.08
Nodes (53): locate, DocNode, PartyChoice, ROLES, buildOffsetIndex, OffsetIndex, sliceCp, toCodePoint (+45 more)

### Community 9 - "Test Coverage"
Cohesion: 0.06
Nodes (31): cached_check, check_bundle, exercise, Verify the portable release in an isolated subprocess and run a CPU smoke.  This, Behavior checks shared by the real CPU run and explicit test doubles., run, smoke_source, Build (+23 more)

### Community 10 - "Document Parsing"
Cohesion: 0.06
Nodes (33): ParsedDocument, AnalysisActiveError, Analysis Record, Session Token Digest, DocumentLimitError, Document Record, Exception, Sessions, documents and jobs: metadata in SQLite, content in RAM (D4, D5).  SQLi (+25 more)

### Community 11 - "API Layer"
Cohesion: 0.06
Nodes (40): mockSettings, App, LINKS, Root, RootError, Lazy Route Loading, Lazy Page Loader, Root Route (+32 more)

### Community 12 - "API Layer"
Cohesion: 0.07
Nodes (41): CATALOGUE, CatalogueEntry, CATEGORY_BY_ID, G, GROUP_ORDER, rows, Support, EvaluationRow (+33 more)

### Community 13 - "API Layer"
Cohesion: 0.19
Nodes (51): analysis(), assert_error(), bearer(), body(), cancel(), job(), keys(), new_document() (+43 more)

### Community 14 - "Backend Services"
Cohesion: 0.10
Nodes (42): Analyzer Factory, Collection, The one analyzer of this process. It never falls back from real to the stub: a r, Sample mode runs the stub, which takes only its own fixture text and its own cat, Sample Mode Validation, test_stub_mode_builds_the_stub_from_the_core_fixture(), CandidateOnlyAnalyzer, context_from_parsed_document() (+34 more)

### Community 15 - "API Layer"
Cohesion: 0.09
Nodes (44): Review Category Catalogue, CatalogueError, Review Category, Catalogue Loader, Exception, Path, The review scope: the fixed notice and the category catalogue.  The catalogue, `reason` is `missing` (no readable file) or `invalid` (the file breaks the shape (+36 more)

### Community 16 - "Test Coverage"
Cohesion: 0.09
Nodes (31): Export, Export selected local training weights; no training or dataset inference.  Run f, Acquire, Check Archive, Copy Checked, Main, Prepare, Publish (+23 more)

### Community 17 - "Document Parsing"
Cohesion: 0.16
Nodes (40): StructureNode, Job Record, Polls until `check()` is truthy and returns its value. A real child process fini, Polling Test Helper, corrupt(), make_rig(), AnalysisResult, LogCaptureFixture (+32 more)

### Community 18 - "Test Coverage"
Cohesion: 0.11
Nodes (27): Directory, Aggregate, Atomic Json, Bind Run, Cache Tokenizer, Finish, Inference Inputs, Inference Engine (+19 more)

### Community 19 - "API Layer"
Cohesion: 0.08
Nodes (8): candidate(), GateTests, pair(), point(), One selector, fixed exit gate, complete whole-tie curves and immutable runs., SavedExperimentTests, SelectorTests, summaries()

### Community 20 - "Document Parsing"
Cohesion: 0.10
Nodes (31): _format(), _Level, _levels(), _number(), _Numbering, Exception, A list paragraph whose number cannot be computed. It never leaves this module an, The w:val of a named child, or None when the child or the attribute is absent. (+23 more)

### Community 21 - "Document Parsing"
Cohesion: 0.09
Nodes (40): _blocks(), _Box, _check_budget(), _content_streams(), _decoded_length(), _group(), _gutters(), _has_annotation_text() (+32 more)

### Community 22 - "Test Coverage"
Cohesion: 0.12
Nodes (40): Doc with parties, Names, Parse, StructureNode, Party nodes and `name_span` (ParserContract.md section 8, parser 1.3.0).  Ever, Test a between line and an and line make two parties that end at the list boundary, Test a between line without a party after it gives nothing, Test a by and between sentence splits at the top level and (+32 more)

### Community 23 - "ML Scripts"
Cohesion: 0.05
Nodes (38): dependencies, react, react-dom, react-router, devDependencies, oxfmt, tailwindcss, @tailwindcss/vite (+30 more)

### Community 24 - "Test Coverage"
Cohesion: 0.10
Nodes (17): Aggregate, Deduplicate, Evaluate, Match Counts, All-window dev_select decoding and anchored-span checkpoint selection.  Caller v, Probe: first fixed question, all its windows, never selection eligible., Exact-range dedup then score-ordered interval NMS; never concatenate., Summarize (+9 more)

### Community 25 - "Data Storage"
Cohesion: 0.46
Nodes (34): clock(), Test Clock, The injected clock (one callable). Tests move time with `advance`, so nothing sl, Add doc, Column, Dump, Path, Ram ids (+26 more)

### Community 26 - "Test Coverage"
Cohesion: 0.10
Nodes (29): canonical_bytes, canonical_sha256, components, family_id, main, member_record, Validate reviewed CUAD families without creating splits or changing data.  Run f, Validate the frozen v1 scope, also used to reproduce the title screen. (+21 more)

### Community 27 - "Test Coverage"
Cohesion: 0.11
Nodes (21): Collate Windows, Initialize Qa Model, Make Optimizer, Optimizer Update, Fit-only CUAD loading, joint marginal loss and clean QA initialization.  Used by, Caller verifies pinned asset hashes first; require every encoder tensor., Finish one real update, retrying AMP overflow on the SAME effective batch., Reconstruct saved evidence and all three epoch lists; never write data. (+13 more)

### Community 28 - "Test Coverage"
Cohesion: 0.15
Nodes (19): Assign Families, Family Inventory, Integer Targets, Main, Propose, Propose Cuad Splits, Propose deterministic, family-isolated CUAD splits for review before freezing., One deterministic greedy run with exact source-document capacities. (+11 more)

### Community 29 - "Document Parsing"
Cohesion: 0.12
Nodes (23): Block, ParseWarning, Clause Structure Builder, _is_caps_heading(), _is_contents(), _Label, _Node, _outer_tables() (+15 more)

### Community 30 - "Test Coverage"
Cohesion: 0.10
Nodes (8): text_digest(), validate_result(), validate_span(), result_json_schema(), Main, Regenerate self-authored fixture data and the wire schema., Contract Tests, Test Contract

### Community 31 - "Test Coverage"
Cohesion: 0.13
Nodes (21): Score All, Assert Parity, Count At Threshold, Evaluate, Finite Json, Load Reference, Main, Matches (+13 more)

### Community 32 - "CUAD Evaluation"
Cohesion: 0.10
Nodes (32): cached, code_hash, collect, execution, labeled_rows, now_ist, print_report, Frozen extractor -> dev_cal only -> one predeclared calibration assessment.  Def (+24 more)

### Community 33 - "Document Parsing"
Cohesion: 0.11
Nodes (32): build_structure, ParseWarning, StructureNode, The clause tree of one document, and the warnings its numbering raised. Header,, Assert valid nodes, Fixtures, StructureNode, The node half of the invariant: every node slices back to its text, nodes come i (+24 more)

### Community 34 - "Test Coverage"
Cohesion: 0.10
Nodes (24): AUTHORITY, JudgmentCardProps, JudgmentPassage, JudgmentState, NEUTRAL, Specimen, Authority, AUTHORITY_PHRASE (+16 more)

### Community 35 - "Test Coverage"
Cohesion: 0.10
Nodes (27): MarginRuler, MarginRulerProps, Mark, MARK_COLOR, RulerMark, RulerVariant, SpanHighlight, panelTransition (+19 more)

### Community 36 - "Document Parsing"
Cohesion: 0.12
Nodes (28): Coverage, Analysis Result Validation, Resolved Decision Count, Processing Completeness Check, AnalysisResult, The boundary with Tanishq's core (`clauseanchor_core`): the analyzer factory, th, What a result must pass before the store takes it. Raises ValueError, and the ca, API.md section 10. True only when the parse left nothing out and every requested (+20 more)

### Community 37 - "Frontend Pages"
Cohesion: 0.08
Nodes (32): type, type, minimum, type, properties, type, type, additionalProperties (+24 more)

### Community 38 - "API Layer"
Cohesion: 0.10
Nodes (17): code_hashes(), file_spec(), Offline, fail-closed verification for the candidate-only inference export., The independently supplied canonical manifest digest is the trust anchor., read_json(), require(), runtime_versions(), verify_bundle() (+9 more)

### Community 39 - "Test Coverage"
Cohesion: 0.12
Nodes (26): audit_categories, main, parse_table, Verify CUAD category names and exact questions against the official table.  Run, save_outputs, build_question_rows, canonical_bytes, check_india_prompts (+18 more)

### Community 40 - "API Layer"
Cohesion: 0.33
Nodes (30): Assert invalid, Bearer, Open session, Probe, LogCaptureFixture, MakeClient, MonkeyPatch, Path (+22 more)

### Community 41 - "Test Coverage"
Cohesion: 0.14
Nodes (14): fields, Build Bundle, Load Frozen Partition, Main, Freeze the reviewed CUAD assignment and materialize four logical partitions.  Ru, Verify against source reconstruction, not just checksums stored beside data., Source-verified input for later feature preparation; no training approval., Construct immutable logical partitions, with independent membership checks. (+6 more)

### Community 42 - "CUAD Evaluation"
Cohesion: 0.17
Nodes (27): annotation_signature, answer_counts, check_test, check_training, contexts, inspect_records, main, paired_paragraphs (+19 more)

### Community 43 - "Test Coverage"
Cohesion: 0.13
Nodes (5): Candidate Analyzer Tests, Software tests only: tiny random QA weights and explicit test logits.  No select, Clearly a test double; receives real tokenizer encodings, not fixtures., Scripted Logits, Test Candidate Analyzer

### Community 44 - "Test Coverage"
Cohesion: 0.12
Nodes (12): CUAD Decoder Error Review, CUAD Evaluation Metrics, CUAD Checkpoint Freeze, CUAD Inference Validation, CUAD Review Policy, candidate(), CurveTests, DocumentTests (+4 more)

### Community 45 - "Backend Services"
Cohesion: 0.10
Nodes (20): _Accounting, _BasicLimits, Capped Child Process, _ExtendedLimits, _IoCounters, A memory cap for one child process. This is the only platform-specific code in t, The most memory the child committed, or None where the platform cannot say (POSI, Ends the child and everything it started. On Windows the job is ended, because t (+12 more)

### Community 46 - "Data Storage"
Cohesion: 0.56
Nodes (28): Finished, Job, CaptureFixture, LogCaptureFixture, MonkeyPatch, Popen, Session, The parse queue: one worker, one child process per parse, real children througho (+20 more)

### Community 47 - "Test Coverage"
Cohesion: 0.11
Nodes (3): Only mutable pointer; previous file survives any failure before replace., Replace Json, SavedReviewTests

### Community 48 - "CUAD Evaluation"
Cohesion: 0.21
Nodes (27): Interval Iou, Assignment, Atomic Text, Best Overlap, Build Review, Candidate Evidence, Coordinates, Coverage Label (+19 more)

### Community 49 - "Data Storage"
Cohesion: 0.13
Nodes (9): CUAD Feature Engineering, CheckpointTests, components(), evaluation(), make_dataset(), CUAD Trainer Integration, Checkpoint transactions, resumed optimization and trainer state transitions., RunnerIntegrationTests (+1 more)

### Community 50 - "API Layer"
Cohesion: 0.14
Nodes (26): health(), Liveness only. It checks no dependency, so a probe cannot fail on a missing cata, Analysis, Capabilities, CategorySpec, CategoryView, ClauseView, DecisionCoverage (+18 more)

### Community 51 - "Document Parsing"
Cohesion: 0.22
Nodes (23): Builds source_text and fixes each block's offsets at the moment it is appended., TextAssembler, add(), assert_invariant(), build(), Block, BlockKind, test_block_without_text_is_refused() (+15 more)

### Community 52 - "Document Parsing"
Cohesion: 0.11
Nodes (21): Block, BlockKind, Collection, ParseWarning, detect_type, pdf_start(), Where `%PDF-` begins, or -1 when it is not within the first 1,024 bytes, where r, Names the file type from its magic bytes. Nothing is extracted from the archive. (+13 more)

### Community 53 - "Test Coverage"
Cohesion: 0.16
Nodes (14): Exhibit Key, Issuer Key, Main, Markdown Report, Parse Title, r"""Screen CUAD source titles for further related-document review candidates.  R, Review Cuad Titles, Screen Titles (+6 more)

### Community 54 - "Test Coverage"
Cohesion: 0.14
Nodes (6): candidate(), fixture(), Selector geometry, report/source integrity and read-only checkpoint review., ReportTests, reseal(), SelectorTests

### Community 56 - "Data Storage"
Cohesion: 0.78
Nodes (24): New doc, New session, The analysis half of the Store: job rows with progress, the result in RAM, one a, Another document of the session may still be parsing, and this one's analysis st, Start, Store, Test a finish after the document is deleted leaves no trace, Test a finish that contradicts itself is refused (+16 more)

### Community 57 - "Frontend Application"
Cohesion: 0.08
Nodes (24): compilerOptions, allowImportingTsExtensions, baseUrl, isolatedModules, jsx, lib, module, moduleResolution (+16 more)

### Community 58 - "Document Parsing"
Cohesion: 0.13
Nodes (23): NameSpan, add_parties, _after_marker(), _is_role(), _lead_end(), _name_span(), _open_at(), _phrase_end() (+15 more)

### Community 59 - "API Layer"
Cohesion: 0.14
Nodes (22): OpenAPI Export Builder, main(), Path, Development tool: writes docs/app/openapi.json, the app's OpenAPI document (API., The document as text, with sorted keys, a two-space indent, ASCII only and one t, Api md, Field names, Gaps (+14 more)

### Community 60 - "Test Coverage"
Cohesion: 0.14
Nodes (8): dict, candidate_result(), CounterLike, fixture(), official_result(), Synthetic final-run checks; pinned evaluator/decoder code, no CUAD examples or t, RecordAndMetricTests, spec()

### Community 61 - "Parser Contract"
Cohesion: 0.09
Nodes (24): items, type, $ref, $ref, enum, items, type, type (+16 more)

### Community 62 - "Test Fixtures"
Cohesion: 0.09
Nodes (24): items, type, items, type, type, type, type, authority_ids (+16 more)

### Community 63 - "Model Calibration"
Cohesion: 0.09
Nodes (24): enum, type, properties, anyOf, enum, type, enum, calibration_scope (+16 more)

### Community 65 - "Test Coverage"
Cohesion: 0.13
Nodes (10): CUAD Decoder Experiment Validation, CUAD Decoder Review Validation, candidate(), FixedModel, fixture(), GeometryTests, ModelLoadingTests, CUAD Decoder Geometry Validation (+2 more)

### Community 66 - "Analysis Pipeline"
Cohesion: 0.09
Nodes (23): properties, type, type, Span, type, type, enum, artifact_manifest_sha256 (+15 more)

### Community 67 - "Test Fixtures"
Cohesion: 0.09
Nodes (23): type, type, type, type, type, type, type, properties (+15 more)

### Community 68 - "Document Parsing"
Cohesion: 0.14
Nodes (3): Scope Fixture Validation, Contract and regression checks for the scope handoff, not browser tests., ScopeFixtureTests

### Community 69 - "Analysis Pipeline"
Cohesion: 0.20
Nodes (19): ConfigError, _int(), API settings, read once from CLAUSEANCHOR_ environment variables.  Parser limits, An environment variable holds a value the API cannot use., _text(), MonkeyPatch, Path, test_a_bad_manifest_digest_names_the_variable_and_not_the_value() (+11 more)

### Community 70 - "Backend Services"
Cohesion: 0.16
Nodes (10): Analysis Job Queue, Analysis Queue Item, AnalysisResult, The analysis queue: one worker thread, a FIFO with a named limit, and the one an, Stops a waiting or running job. A waiting one ends at once, and a running one at, The store's `on_drop` hook. It runs under the store's lock and only sets flags,, Marks the job stopped and drops its text. The caller holds the lock., Stops a running analysis and waits for the worker thread. (+2 more)

### Community 71 - "UI Components"
Cohesion: 0.11
Nodes (17): Button, styleFor(), ClauseDetailPanel, ClauseDetailPanelProps, eyebrow, Honest Threshold Warning, PanelData, Review Candidate Note (+9 more)

### Community 72 - "CUAD Evaluation"
Cohesion: 0.20
Nodes (20): CandidateEngine, CandidateEngine.call, CandidateEngine.init, Configure Arm, OfficialEngine, OfficialEngine.init, Frozen deployment analyzer and a separate benchmark-only reference path.  Refere, Release Engine (+12 more)

### Community 73 - "Test Coverage"
Cohesion: 0.20
Nodes (8): Align Answers, Return status and unique local pairs -> original answer occurrence IDs., Map gold in the FULL context so windows cannot cut Unicode byte pieces.      Rep, Window Targets, answer(), CuadFeatureTargetTests, Protect source alignment, multi-answer targets, partition binding and resume., targets()

### Community 74 - "Test Coverage"
Cohesion: 0.22
Nodes (5): Candidate, Policy Tests, Synthetic software checks; no real policy/test examples or trained weights., Task, Test Cuad Candidate Policy

### Community 75 - "UI Components"
Cohesion: 0.14
Nodes (16): ManualItem, ManualItemVariant, ManualListState, Manual Review State, ManualReviewItem, ManualReviewList, Preview(), MobileDrawer (+8 more)

### Community 76 - "Candidate Analyzer"
Cohesion: 0.10
Nodes (21): properties, anyOf, decision_confidence, reason_code, search_complete, status, unresolved_count, windows_done (+13 more)

### Community 77 - "Test Coverage"
Cohesion: 0.18
Nodes (13): Compare Reference, Main, Run the pinned CUAD checkpoint on one fixed, complete official-test question.  R, Fixed source-order selection; never use answer labels to build input., Runtime Versions, Select Question, Smoke, Smoke Cuad Baseline (+5 more)

### Community 78 - "API Layer"
Cohesion: 0.16
Nodes (15): Authored Docx, Backend Hashes, Check Analysis, Check Progress, Preflight, Real local ASGI upload -> parser child -> analysis queue -> trained CPU model., Validate exactly the categories returned by the API against its parser text., Use the unmodified app/factory/workers. Parameters enable explicit tiny-model un (+7 more)

### Community 79 - "CUAD Evaluation"
Cohesion: 0.24
Nodes (17): Aggregate Results, Bind Run, Exact Candidates, Infer Question, Load Model, Main, Make Record, Process Questions (+9 more)

### Community 80 - "API Layer"
Cohesion: 0.15
Nodes (13): fake_core(), Real mode on a fake: `CandidateOnlyAnalyzer` in the factory becomes this object,, FakeCore, AnalysisResult, A stand-in for the CandidateOnlyAnalyzer class and for its instance.      Call, LogCaptureFixture, MakeClient, Path (+5 more)

### Community 81 - "CUAD Evaluation"
Cohesion: 0.12
Nodes (20): Contract Understanding Atticus Dataset, CUAD Research Authors, CUAD Research Paper, CUAD v1 Source Snapshot, Annotation Catalogue, Arbitration, Cap on Liability, Dispute Escalation (+12 more)

### Community 82 - "Model Calibration"
Cohesion: 0.11
Nodes (20): required, required, id, calibration_scope, category_id, clauses, confidence, confidence_band (+12 more)

### Community 83 - "Test Coverage"
Cohesion: 0.25
Nodes (6): Sample Epoch, Validate Selection, CuadSamplingTests, Guard fit-only sampling, gold coverage and immutable plan publication., record(), sampling_fixture()

### Community 86 - "Document Parsing"
Cohesion: 0.13
Nodes (17): Depends, Request, Session, The bearer check. Every route that needs a session depends on `require_session`., The live session for the bearer token, or a 401 that does not say which check fa, require_session, Fixed API Error Envelope, Takes the file as the raw body, queues a parse and answers at once. The type com (+9 more)

### Community 87 - "Document Parsing"
Cohesion: 0.25
Nodes (9): _children(), BlockKind, Turns the parts into plain items, in document order. It holds no assembler, so t, A14: an unknown block-level child is skipped, with a warning and partial., The text of a paragraph, and the text boxes it anchors. Text box content is not, Walks the block-level children of a part, a text box or a cell. In a cell the, Reads one part, or one note. Tables and text boxes are numbered within it., _Walk (+1 more)

### Community 88 - "Backend Services"
Cohesion: 0.18
Nodes (8): Bounded Worker Pattern, Parse Queue Item, Parse Job Queue, The parse queue: a bounded queue in the app process, one worker thread, one chil, Marks the job stopped, drops its bytes and kills its child. The caller holds the, Kills the running child and waits for it and for the worker thread., Queues one parse. False when `parse_queue_length` parses are already waiting., The store's `on_drop` hook. It runs under the store's lock. A waiting job loses

### Community 89 - "UI Components"
Cohesion: 0.13
Nodes (13): DropdownMenu Focus Ring Test, ConfirmDialog, ConfirmDialogProps, Disclosure, DropdownMenu, MenuItem, Shared Focus-Ring Accessibility, DragHandleIcon() (+5 more)

### Community 90 - "Analysis Pipeline"
Cohesion: 0.19
Nodes (12): _decode(), from_dict(), AnalysisResult, Strict JSON conversion and schema export for the core dataclasses., to_dict(), to_json(), main, Main (+4 more)

### Community 91 - "CUAD Evaluation"
Cohesion: 0.15
Nodes (17): bootstrap_families, distribution, grouped, project_result, Offline candidate-only policy projection and fixed-policy measurements.  No mode, Project saved real candidates to v2; gold is never used in this function.      S, Select fixed candidates, validate v2 projections, then score against gold., summarize_policy (+9 more)

### Community 92 - "Test Coverage"
Cohesion: 0.19
Nodes (16): Bind Output, Bootstrap Documents, Code Sha, Curve Point, Describe Target, Detailed Point, Diagnose, Load Pools (+8 more)

### Community 93 - "CUAD Evaluation"
Cohesion: 0.20
Nodes (18): Cached Result, Category Comparison, Check Coverage, Choose Point, Detail, Feasible Point, Gate, Load Pools (+10 more)

### Community 94 - "Test Coverage"
Cohesion: 0.13
Nodes (4): Examples, Method Tests, Synthetic tests for leakage boundaries, one method, provenance and resume.  No r, Test Cuad Calibration

### Community 95 - "Test Coverage"
Cohesion: 0.18
Nodes (4): CuadFamilyTests, CUAD Family Splitting, CUAD Dataset Preparation, CUAD Dataset Splits

### Community 96 - "API Layer"
Cohesion: 0.22
Nodes (17): Analysis, error_response(), cancel_job, capabilities(), create_session(), _job_view(), datetime, JSONResponse (+9 more)

### Community 97 - "Document Parsing"
Cohesion: 0.74
Nodes (17): New doc, Parsed, The document and job half of the Store that 2-C fills: delete, job state, result, Rows, Store, Test a job can fail with a code, Test a job finishes with a result or a code and never both, Test a job of an expired session is gone (+9 more)

### Community 98 - "Document Start Flow"
Cohesion: 0.14
Nodes (18): properties, minimum, type, type, const, minimum, type, properties (+10 more)

### Community 99 - "CUAD Evaluation"
Cohesion: 0.27
Nodes (17): Breakdown, Load Checkpoint Reports, Main, Ordered, Print Summary, Compare five fixed selectors on saved dev_select candidates, without inference., Reproduce original capped scoring and validate every saved source span., Verify hashes, but never torch.load or change an existing training file. (+9 more)

### Community 100 - "API Layer"
Cohesion: 0.21
Nodes (17): _analysis_request(), delete_current_session(), delete_document(), _filename(), Depends, Request, Session, The raw body, or None once it passes `limit`. It counts what arrives, so a missi (+9 more)

### Community 101 - "Backend Services"
Cohesion: 0.14
Nodes (12): AnalysisResult, Ends a waiting or running analysis. `succeeded` and `partial` carry the result,, validate_probability(), Main, Document Index, Main, Download and verify the pinned official CUAD benchmark split files., Sha256 (+4 more)

### Community 102 - "Test Coverage"
Cohesion: 0.19
Nodes (9): Dataset, FitWindowDataset, FitWindowDataset. arrays, FitWindowDataset.close, FitWindowDataset.getitem, FitWindowDataset.init, FitWindowDataset.len, Consume indices from a verified plan, without resampling or reshuffling. (+1 more)

### Community 103 - "Document Start Flow"
Cohesion: 0.13
Nodes (17): end, start, text, required, required, authority_status, case_name, citation (+9 more)

### Community 104 - "Test Coverage"
Cohesion: 0.26
Nodes (5): Inspect Group, Cross-check labels, paired targets and occurrence references before sampling., CUAD Training Assets, CuadFeatureCoverageTests, CUAD Training Plan

### Community 106 - "API Layer"
Cohesion: 0.17
Nodes (14): create_app, _lifespan(), FastAPI, The FastAPI app. `create_app(settings)` builds one, so tests bring their own set, `clock` is the one source of time for expiry, so tests move it by hand., Sweep Background Task, MonkeyPatch, test_create_app_without_settings_reads_the_environment() (+6 more)

### Community 107 - "API Layer"
Cohesion: 0.33
Nodes (15): Assert envelope, Item, Probe, BaseModel, LogCaptureFixture, TestClient, The app with three routes that only tests have: path and query numbers, a body,, Test 404 does not echo the path (+7 more)

### Community 108 - "Test Coverage"
Cohesion: 0.15
Nodes (5): FeatureTokenizer.init, InputTests, CUAD Final Evaluation, RealReferenceEngineTests, Tokenizer

### Community 109 - "Test Coverage"
Cohesion: 0.28
Nodes (11): Initial Progress, Learning Rate, Main, Resumable clean CUAD training; default invocation performs only TWO updates.  Fi, One completed effective batch, including a correctly weighted short tail., Record Evaluation, Run, Train Cuad (+3 more)

### Community 110 - "Test Coverage"
Cohesion: 0.29
Nodes (5): Amp Update Tests, Assert Tree Equal, Example, Real GradScaler overflow, same-batch replay and legacy checkpoint recovery., Test Cuad Amp Recovery

### Community 111 - "API Layer"
Cohesion: 0.22
Nodes (12): asgi_post(), Streaming ASGI Request Body, Any, Made-up test data: a catalogue and a clock that only moves when a test moves it,, A request body for `asgi_post` that records how many bytes the app took from it., POSTs straight into the app, with no server and no TestClient in between, and re, analyses_path(), test_a_body_over_the_cap_is_a_422_before_the_document_is_looked_up() (+4 more)

### Community 112 - "API Layer"
Cohesion: 0.13
Nodes (15): RAM Text Store with TTL, SQLite Metadata Store, Upload and Analysis Request Flow, Analysis, Capabilities, additionalProperties, required, type (+7 more)

### Community 113 - "Parser Contract"
Cohesion: 0.13
Nodes (14): additionalProperties, text_sha256, warnings, required, $schema, title, type, blocks (+6 more)

### Community 114 - "ML Scripts"
Cohesion: 0.28
Nodes (14): display_units, exact_keys, load_families, main, observe, paragraph_units, Check development fixtures, not the running application or a trained model.  The, Compute a reference snapshot independently of the checked-in expectations. (+6 more)

### Community 115 - "Test Coverage"
Cohesion: 0.21
Nodes (12): Bind Features, FeatureTokenizer, FeatureTokenizer.context, FeatureTokenizer.question, FeatureTokenizer.windows, File Spec, Group Inputs, Main (+4 more)

### Community 116 - "Test Coverage"
Cohesion: 0.28
Nodes (5): Build Shard, Write into a private staging directory; publish only on success., Check hashes and typed array schema before reusing a shard., Verify Shard, CuadFeatureTokenizerTests

### Community 119 - "Backend Services"
Cohesion: 0.19
Nodes (9): Session TTL Limit, Settings, MonkeyPatch, Path, The analyzer factory, and the promise that stub mode loads no model library., test_a_directory_that_is_not_a_bundle_fails_and_is_not_replaced_by_the_stub(), test_real_mode_builds_the_candidate_only_analyzer_on_cpu_with_the_digest(), test_real_mode_with_incomplete_settings_fails_and_never_builds_the_stub() (+1 more)

### Community 120 - "Parser Contract"
Cohesion: 0.14
Nodes (14): enum, properties, code, detail, BLANK_PAGE, COLUMN_ORDER_UNCERTAIN, EMBEDDED_OBJECT, MORE_THAN_TWO_COLUMNS (+6 more)

### Community 121 - "Parser Contract"
Cohesion: 0.14
Nodes (14): StructureNode, properties, properties, additionalProperties, type, name_span, additionalProperties, else (+6 more)

### Community 122 - "Parser Contract"
Cohesion: 0.14
Nodes (14): text, enum, clause, definition, footer, footnote, header, heading (+6 more)

### Community 124 - "Backend Services"
Cohesion: 0.22
Nodes (13): CUAD Cross-Split Text Review, CUAD Data Review, Exact-Text Family Deduplication, AduroBioTech Question-Level Hold, CUAD Federated Services-Family Source Review, CUAD PCQuote Co-branding-Family Source Review, CUAD Remaining Cross-Split Candidate Review, CUAD Remaining Training-Family Review (+5 more)

### Community 125 - "Test Fixtures"
Cohesion: 0.15
Nodes (12): additionalProperties, type, additionalProperties, type, $defs, CategoryResult, ClauseFinding, Passage (+4 more)

### Community 126 - "Test Fixtures"
Cohesion: 0.15
Nodes (13): items, type, items, type, $ref, items, type, categories (+5 more)

### Community 127 - "Test Coverage"
Cohesion: 0.28
Nodes (4): check(), CuadTrainingAssetTests, Guard the base checkpoint identity and code-point/overlap tokenizer checks., window()

### Community 128 - "Test Coverage"
Cohesion: 1.00
Nodes (12): Structure of, Test a docx contents list with tab page numbers makes no clause nodes, Test a list label names the node, Test a nested table has no node of its own, Test a numeral list after h is read as numerals in a word file, Test a pdf contents page makes no clause nodes, Test a table is one leaf node with its cells, Test a word list continues across an empty numbered paragraph (+4 more)

### Community 129 - "CUAD Evaluation"
Cohesion: 0.21
Nodes (12): Official CUAD Baseline, Unvalidated Pooled Calibration, Candidate-Only Operating Policy, CUAD Family Policy, Legacy Family Screen, Final Evaluation Protocol, Frozen CUAD Partition, Cohort-Balanced Split Policy (+4 more)

### Community 130 - "Parser Contract"
Cohesion: 0.18
Nodes (12): items, maxItems, minItems, items, type, items, maxItems, minimum (+4 more)

### Community 131 - "Document Start Flow"
Cohesion: 0.23
Nodes (12): required, end, id, start, required, required, bbox, kind (+4 more)

### Community 132 - "Frontend Application"
Cohesion: 0.20
Nodes (10): check(), css, dark, light, luminance(), Pair, plainStatus, ratio() (+2 more)

### Community 133 - "Test Fixtures"
Cohesion: 0.17
Nodes (12): RuleFlag, additionalProperties, required, type, authority_ids, evidence_spans, label_key, note (+4 more)

### Community 134 - "Test Fixtures"
Cohesion: 0.17
Nodes (11): files, 01_supported_and_outside.json, 02_outside_only.json, 03_mixed_paragraph.json, 04_broad_span.json, 05_distant_clauses.json, 06_incomplete.json, 07_positions.json (+3 more)

### Community 136 - "Parser Contract"
Cohesion: 0.18
Nodes (11): additionalProperties, type, $defs, Block, ParseWarning, additionalProperties, required, type (+3 more)

### Community 137 - "API Layer"
Cohesion: 0.18
Nodes (11): Candidate-Only API Integration Check, Candidate Prototype: Local Parser/API Integration Check, Candidate Prototype Packaging and Integration Checks, Candidate Prototype Package Verification, Category Catalogue 1.0.0, not_validated Category Support, Stable Namespaced Category Identity, Analyzer Interface Contract (+3 more)

### Community 138 - "Test Coverage"
Cohesion: 0.31
Nodes (3): Joint Marginal Loss, Mean -log sum P(start)*P(end) over UNIQUE annotated pairs per window.      FP32, MarginalLossTests

### Community 139 - "CUAD Evaluation"
Cohesion: 0.20
Nodes (10): near_score_sentence_pack_v1, The Single Bounded Decoder Experiment, disjoint_full Decoder Variant, CUAD Full-Candidate Decoder Review, Clean-Checkpoint CUAD Evaluation, Frozen Final Extraction Evaluation, Boundary-Aware Candidate Selection, CUAD Source-Span Error Review (+2 more)

### Community 140 - "Analysis Pipeline"
Cohesion: 0.20
Nodes (10): additionalProperties, required, type, AnalysisResult, text_sha256, warnings, artifact_manifest_sha256, categories (+2 more)

### Community 142 - "Data Storage"
Cohesion: 0.36
Nodes (8): name, File Spec, Latest, Transactional local training checkpoints. Caller holds the run lock.  A checkpoi, Restore, Restore Rng, Rng State, Save

### Community 143 - "Test Coverage"
Cohesion: 0.25
Nodes (4): disjoint_candidates(), exact_candidates(), Preserve original exact-dedup semantics without its overlap suppression., Frozen Parity Tests

### Community 144 - "Test Coverage"
Cohesion: 0.39
Nodes (3): Keep the original run identity; bind a specific recovery in a sidecar.      This, Resolve Execution, Recovery Identity Tests

### Community 146 - "Test Coverage"
Cohesion: 0.22
Nodes (9): _latin_unicode, list_pdf, _long_lines, _partly_scanned, _pdf, _simple, _text, _tight_clauses (+1 more)

### Community 147 - "API Layer"
Cohesion: 0.32
Nodes (7): install_error_handling(), Exception, FastAPI, JSONResponse, Request, The error envelope: one fixed shape for every error response.  Messages are fixe, _reply()

### Community 148 - "API Layer"
Cohesion: 0.25
Nodes (8): _document_json(), Any, The document's metadata and, once it is parsed, the full parser output. Another, The parser's full output, plus `page` on every node (API.md section 3). The page, read_document, AnalysisRequest, Analysis and Document API Views, Unknown fields are refused (plan 9.1). The ids and the scope are both required (

### Community 149 - "UI Components"
Cohesion: 0.29
Nodes (6): MetricCell, MetricCellProps, MetricVariant, PerformanceTableRow, PerformanceTableRowProps, PerfVariant

### Community 150 - "CUAD Evaluation"
Cohesion: 0.43
Nodes (7): Audit Features, Main, Pools, Prepare, Audit saved CUAD features and prepare deterministic fit-only epoch samples.  Run, Read the existing artifacts, independently cross-checking target tables., Same

### Community 151 - "Analysis Pipeline"
Cohesion: 0.38
Nodes (7): Arbitration, Cap on Liability, Non-Compete, Question Set, Stub Analysis Result, Fixture Contract, Category Catalogue

### Community 152 - "Test Coverage"
Cohesion: 0.33
Nodes (7): Frontend HTML Shell, Frontend Package Manifest, Font Performance Tests, Main Entry Point, Design Token Tests, TypeScript Compiler Options, Vite Configuration

### Community 155 - "Test Coverage"
Cohesion: 0.29
Nodes (7): build_docx, _header_footer, _list_number_style, _notes, _simple_docx, _tracked, _word_notes

### Community 156 - "API Layer"
Cohesion: 1.00
Nodes (6): Test a heading is at least sixty percent capitals and at most eighty characters, Test a line that is not a short all caps line is not a heading, Test a schedule word in running text is not a schedule, Test a section word in running text is not a heading, Test an all caps contents entry is not a heading, Test schedule words start a schedule node

### Community 157 - "Candidate Analyzer"
Cohesion: 0.33
Nodes (6): Incomplete processing takes precedence, Incomplete processing overrides completed manual-review inventory and absence claims., Incomplete processing overrides completed manual-review inventory and absence claims., Incomplete processing overrides completed manual-review inventory and absence claims., Incomplete processing overrides completed manual-review inventory and absence claims., Incomplete processing overrides completed manual-review inventory and absence claims.

### Community 158 - "Frontend Application"
Cohesion: 0.40
Nodes (5): Accessible Scalable Icon, Balance Scale, ClauseAnchor Favicon, Document Brackets, Light and Dark Theme Styling

### Community 159 - "Test Fixtures"
Cohesion: 0.40
Nodes (5): Position, union, hierarchy and gap edge cases, Leading/trailing separators count in full coverage. Whitespace-only leaves need no card and remain in the full text., Adjacent accepted intervals from two requested categories jointly cover a unit. Union coverage, not the longest individual span, decides full coverage., Overlapping sibling leaves force exact-paragraph fallback, not dropped text or double-counted ranges., Only the SECOND repeated clause is accepted. Nested parents are not cards. Gaps remain visible; emoji offsets count code points.

### Community 160 - "Architecture"
Cohesion: 0.50
Nodes (4): Canonical Parser, PDF Reading Order, Scanned PDF Handling, Unicode Code Point Offsets

### Community 162 - "Test Coverage"
Cohesion: 0.67
Nodes (3): Path, Path, size and modification time of every file under root, tool folders left out, snapshot()

### Community 163 - "Candidate Analyzer"
Cohesion: 0.67
Nodes (3): Disjoint Full Decoder, disjoint_candidates, exact_candidates

### Community 164 - "Machine Learning"
Cohesion: 0.67
Nodes (3): clauseanchor_core Public API, clauseanchor-core Package, ML Runtime Requirements

### Community 165 - "Test Fixtures"
Cohesion: 0.67
Nodes (3): Proposed categories are not validated support, Catalogue membership is not validated decision support. This proposed category has no measured policy or model., Catalogue membership is not validated decision support. This proposed category has no measured policy or model.

### Community 166 - "Machine Learning"
Cohesion: 1.00
Nodes (3): Baseline Evaluation Stack, Evaluation Libraries, Inference Libraries

## Ambiguous Edges - Review These
- `upload_document` → `Fixed API Error Envelope`  [AMBIGUOUS]
  backend/app/api/routes.py · relation: conceptually_related_to
- `Review Category Catalogue` → `Document Text in RAM`  [AMBIGUOUS]
  backend/app/services/scope.py · relation: conceptually_related_to
- `CUAD XACCT Unparsed-Title Review` → `Conservative Document-Level Holds`  [AMBIGUOUS]
  docs/ml/CUAD_XACCTTitleReview.md · relation: conceptually_related_to

## Knowledge Gaps
- **510 isolated node(s):** `_BasicLimits`, `_IoCounters`, `clauseanchor-backend`, `Test the committed schema file is the schema`, `Api md` (+505 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **31 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `upload_document` and `Fixed API Error Envelope`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Review Category Catalogue` and `Document Text in RAM`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `CUAD XACCT Unparsed-Title Review` and `Conservative Document-Level Holds`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `ParsedDocument` connect `Document Parsing` to `Document Parsing`, `Document Parsing`, `Test Coverage`, `Document Parsing`, `Backend Services`, `Document Parsing`, `API Layer`, `Document Parsing`, `Document Parsing`, `Test Coverage`, `Document Parsing`, `Document Parsing`, `Document Parsing`, `Document Parsing`, `Backend Services`, `API Layer`, `Document Parsing`, `Backend Services`, `Document Parsing`?**
  _High betweenness centrality (0.077) - this node is a cross-community bridge._
- **Why does `Run Lock` connect `Test Coverage` to `CUAD Evaluation`, `CUAD Evaluation`, `Backend Services`, `CUAD Evaluation`, `Test Coverage`, `CUAD Evaluation`, `Test Coverage`, `CUAD Evaluation`, `Test Coverage`, `CUAD Evaluation`, `Test Coverage`, `Test Coverage`, `CUAD Evaluation`?**
  _High betweenness centrality (0.050) - this node is a cross-community bridge._
- **Why does `Application Store` connect `Document Parsing` to `Document Parsing`, `Backend Services`, `Backend Services`, `API Layer`, `API Layer`, `Data Storage`, `API Layer`, `API Layer`, `Document Parsing`, `API Layer`, `Backend Services`, `Backend Services`, `Data Storage`, `Data Storage`?**
  _High betweenness centrality (0.032) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `Structure` (e.g. with `Test the parties lie inside the preamble and the rest of the tree is untouched` and `Without the party step`) actually correct?**
  _`Structure` has 4 INFERRED edges - model-reasoned connections that need verification._