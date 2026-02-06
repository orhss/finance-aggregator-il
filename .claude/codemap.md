# Fin Codemap
# USE THIS FILE to check if files/directories exist
# Do NOT use Glob/Grep for file existence checks
# Auto-generated: 2026-02-06 21:15
# Refresh: python scripts/generate_codemap.py

## Flow
scrapers → services → db → cli/streamlit_app

## Key Patterns
- Credit cards: Selenium login → token extract → API calls
- Pensions: Email MFA via IMAP (Migdal, Phoenix)
- Brokers: Pure REST API clients

## cli/ - CLI interface for financial data aggregator
- cli/commands/accounts.py: fn:list_accounts,show_account,account_summary
- cli/commands/auth.py: fn:status,enable,disable,add_user_cmd,remove_user_cmd
- cli/commands/budget.py: fn:make_progress_bar,show_budget,set_budget,delete_budget
- cli/commands/categories.py: fn:analyze_categories,list_mappings,unmapped_categories,map_category,unmap_category
- cli/commands/config.py: fn:show,set,setup,manage_card_holder,list_card_holders
- cli/commands/export.py: fn:serialize_date,export_transactions,export_transactions_csv,export_transactions_json,export_balances
- cli/commands/init.py: fn:main
- cli/commands/maintenance.py: fn:cleanup,backup,verify,migrate
- cli/commands/reports.py: fn:make_bar,make_sparkline,get_trend_indicator,format_change,generate_insights
- cli/commands/rules.py: fn:list_rules,add_rule,remove_rule,apply_rules,init_rules
- cli/commands/sync.py: fn:sync_all,sync_excellence,sync_meitav,sync_migdal,sync_phoenix
- cli/commands/tags.py: fn:list_tags,rename_tag,delete_tag,migrate_categories
- cli/commands/transactions.py: fn:browse_transactions,list_transactions,show_transaction,tag_transaction,untag_transaction
- cli/main.py: fn:setup_logging,version,callback,main
- cli/tui/browser.py: class:EditScreen,TagScreen,TransactionBrowser | fn:run_browser
- cli/utils.py: fn:parse_date,parse_date_range,get_analytics,get_db_session,spinner

## config/ - Configuration management for financial data aggreg
- config/constants.py: class:AccountType,Institution,SyncType,SyncStatus,TransactionStatus
- config/settings.py: class:BrokerCredentials,PensionCredentials,CreditCardCredentials,EmailCredentials,Credentials | fn:get_encryption_key,encrypt_credentials,decrypt_credentials,save_credentials,load_credentials

## db/ - Database layer for financial data aggregator
- db/database.py: fn:get_database_url,enable_foreign_keys,create_database_engine,init_db,drop_all_tables
- db/migrations/add_indexes.py: fn:run_migration,rollback_migration,check_indexes
- db/models.py: class:Account,Transaction,Balance,SyncHistory,Tag
- db/query_utils.py: fn:effective_amount_expr,effective_category_expr,get_effective_amount

## examples/ - Example scripts demonstrating scraper usage
- examples/example_cal_usage.py: fn:main,display_results,export_to_csv

## scrapers/ - Financial Institution Scrapers
- scrapers/base/broker_base.py: class:LoginCredentials,AccountInfo,BalanceInfo,BrokerAPIError,AuthenticationError
- scrapers/base/email_retriever.py: class:EmailConfig,MFAConfig,EmailRetrievalError,EmailMFARetriever
- scrapers/base/mfa_handler.py: class:MFAEntryError,MFAHandler
- scrapers/base/pension_automator.py: class:PensionAutomatorBase
- scrapers/base/selenium_driver.py: class:DriverConfig,SeleniumDriver
- scrapers/base/web_actions.py: class:WebActionError,ElementNotFoundError,WebActions
- scrapers/brokers/excellence_broker_client.py: class:BrokerAPIError,AuthenticationError,AccountError,BalanceError,ExtraDeProAPIClient | fn:main
- scrapers/brokers/meitav_broker_client.py: class:MeitavCredentials,MeitavBalance,MeitavHolding,MeitavAccount,MeitavScraperError | fn:main
- scrapers/config/logging_config.py: fn:add_logging_args,setup_logging_from_args,setup_logging
- scrapers/credit_cards/base_scraper.py: class:BaseCreditCardScraper
- scrapers/credit_cards/cal_credit_card_client.py: class:CALCredentials,TrnTypeCode,CardAccount,CALCreditCardScraper | fn:main
- scrapers/credit_cards/isracard_credit_card_client.py: class:IsracardCredentials,CardAccount,IsracardCreditCardScraper | fn:main
- scrapers/credit_cards/max_credit_card_client.py: class:MaxCredentials,MaxPlanName,CardAccount,MaxCreditCardScraper | fn:main
- scrapers/credit_cards/shared_helpers.py: fn:iterate_months,calculate_date_range,filter_transactions_by_date,extract_installments,get_cookies
- scrapers/credit_cards/shared_models.py: class:TransactionStatus,TransactionType,Installments,Transaction,CreditCardScraperError
- scrapers/exceptions.py: class:ScraperError,AuthenticationError,LoginFailedError,MFAFailedError,SessionExpiredError
- scrapers/pensions/migdal_pension_client.py: class:MigdalEmailMFARetriever,MigdalSeleniumMFAAutomator | fn:main
- scrapers/pensions/phoenix_pension_client.py: class:PhoenixEmailMFARetriever,PhoenixSeleniumMFAAutomator | fn:main
- scrapers/utils/retry.py: class:RetryableHTTPError | fn:retry_with_backoff,retry_selenium_action,retry_api_call,retry_on_server_error
- scrapers/utils/wait_conditions.py: class:SmartWait

## services/ - Services package for data synchronization and anal
- services/analytics_service.py: class:AnalyticsService
- services/base_service.py: class:BaseSyncService
- services/broker_service.py: class:BrokerSyncResult,BrokerService
- services/budget_service.py: class:BudgetService
- services/category_service.py: class:CategoryService
- services/credit_card_service.py: class:CreditCardSyncResult,CreditCardService
- services/pension_service.py: class:PensionSyncResult,PensionService
- services/rules_service.py: class:MatchType,Rule,RulesService
- services/tag_service.py: class:TagService

## streamlit_app/
- streamlit_app/app.py: fn:render_empty_state,render_header,render_hero_and_metrics,render_budget_progress,render_insight_banner
- streamlit_app/auth.py: fn:check_authentication,get_logout_button,require_auth
- streamlit_app/components/bulk_actions.py: fn:show_bulk_preview,show_bulk_confirmation,bulk_action_workflow,quick_bulk_preview
- streamlit_app/components/cards.py: fn:get_tokens,get_base_card_css,render_card,render_metric_row,render_account_card
- streamlit_app/components/charts.py: fn:spending_donut,trend_line,category_bar,balance_history,spending_by_day
- streamlit_app/components/empty_states.py: fn:empty_transactions_state,empty_search_results,empty_accounts_state,empty_analytics_state,empty_dashboard_state
- streamlit_app/components/filters.py: fn:date_range_filter,account_filter,institution_filter,status_filter,category_filter
- streamlit_app/components/heatmap.py: fn:calendar_heatmap,monthly_heatmap
- streamlit_app/components/loading.py: class:ProgressTracker | fn:show_progress_steps,contextual_spinner,skeleton_table,skeleton_metrics,show_loading_message
- streamlit_app/components/mobile_ui.py: fn:apply_mobile_css,hero_balance_card,summary_card,transaction_list,bottom_navigation
- streamlit_app/components/responsive.py: fn:responsive_columns,mobile_card,responsive_metrics,responsive_table_config,stacked_layout
- streamlit_app/components/sidebar.py: fn:render_privacy_toggle,render_quick_stats,render_theme_toggle,render_about,render_minimal_sidebar
- streamlit_app/components/theme.py: fn:load_shared_css,init_theme,render_theme_switcher,generate_css_variables,apply_theme
- streamlit_app/config/pages.py: class:PagePath
- streamlit_app/config/theme.py: class:ColorPalette,Theme | fn:get_theme,set_theme_mode
- streamlit_app/main.py: Financial Data Aggregator - Central Entrypoint
- streamlit_app/mobile_dashboard.py: fn:render_budget_progress,render_alerts,render_recent_transactions,render_mobile_dashboard
- streamlit_app/styles/design_tokens.py: fn:get_css_variables,get_token,get_hero_styles,get_card_styles,get_metric_card_styles
- streamlit_app/utils/cache.py: fn:get_transactions_cached,get_dashboard_stats,get_category_spending_cached,get_monthly_trend_cached,get_accounts_cached
- streamlit_app/utils/errors.py: class:ErrorBoundary | fn:safe_service_call,get_user_friendly_error,safe_call_with_spinner,handle_error_with_retry,safe_decorator
- streamlit_app/utils/formatters.py: fn:format_currency,format_date,format_datetime,format_number,format_percentage
- streamlit_app/utils/insights.py: fn:generate_spending_insight,generate_balance_insight,generate_pending_insight,generate_category_insight,get_time_greeting
- streamlit_app/utils/mobile.py: fn:detect_mobile,render_mobile_toggle,is_mobile,mobile_page_config,force_mobile_mode
- streamlit_app/utils/rtl.py: fn:has_hebrew,fix_rtl,format_description,mixed_rtl_ltr,clean_merchant_name
- streamlit_app/utils/session.py: fn:format_amount_private,get_accounts_display,get_dashboard_stats_display,get_transactions_display,get_tags_display
- streamlit_app/views/accounts.py: fn:get_status_indicator,run_sync_in_thread,start_sync,init_sync_state,render_mobile_accounts
- streamlit_app/views/analytics.py: fn:render_mobile_analytics,time_range_selector,render_desktop_analytics
- streamlit_app/views/organize.py: Organize Page - Unified management for Categories, Rules, an
- streamlit_app/views/settings.py: fn:render_theme_settings,render_privacy_settings,render_budget_settings,render_mobile_settings,render_desktop_settings
- streamlit_app/views/transactions.py: fn:render_mobile_transactions,render_desktop_transactions

## tests/
- tests/cli/test_utils.py: class:TestParseDate,TestParseDateRange,TestGetAnalytics,TestGetDbSession,TestSpinner
- tests/conftest.py: fn:db_engine,db_session,sample_account,sample_accounts,create_account
- tests/integration/conftest.py: fn:cli_runner,integration_db_engine,integration_db_session,patched_session_local,patched_db_exists
- tests/integration/test_category_commands.py: fn:test_categories_list_empty,test_categories_list_shows_mappings,test_categories_list_filters_by_provider,test_categories_map_creates_mapping,test_categories_map_updates_existing
- tests/integration/test_service_integration.py: fn:service_db_session,credit_card_service,category_service,analytics_service,temp_rules_file
- tests/integration/test_sync_commands.py: fn:mock_db_session,test_sync_cal_success_output,test_sync_cal_shows_card_count,test_sync_max_success_output,test_sync_isracard_success_output
- tests/scrapers/credit_cards/test_base_scraper.py: class:MockCredentials,MockSeleniumDriver,TestBaseScraperLifecycle,TestScraperConfiguration,TestCurrentScraperBehavior
- tests/scrapers/credit_cards/test_shared_helpers.py: class:MockTransaction,TestIterateMonths,TestCalculateDateRange,TestFilterTransactionsByDate,TestExtractInstallments
- tests/scrapers/credit_cards/test_shared_models.py: class:TestTransactionStatus,TestTransactionType,TestInstallments,TestTransaction,TestCardAccount
- tests/services/test_analytics_service.py: fn:analytics_service,sample_account,test_get_all_accounts_empty,test_get_all_accounts_returns_all,test_get_all_accounts_active_filter
- tests/services/test_category_service.py: fn:category_service,sample_account,sample_mapping,sample_merchant_mapping,test_normalize_category_happy_flow
- tests/services/test_rules_service.py: fn:temp_rules_file,rules_service,sample_account,test_rule_matches_match_types,test_rule_matches_regex
- tests/smoke/test_imports.py: fn:test_cli_main_imports,test_cli_commands_import,test_cli_tui_imports,test_services_import,test_models_import
