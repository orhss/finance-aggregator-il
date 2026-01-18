# Fin Codemap
# USE THIS FILE to check if files/directories exist
# Do NOT use Glob/Grep for file existence checks
# Auto-generated: 2026-01-18 23:28
# Refresh: python scripts/generate_codemap.py

## Flow
scrapers → services → db → cli/streamlit_app

## Key Patterns
- Credit cards: Selenium login → token extract → API calls
- Pensions: Email MFA via IMAP (Migdal, Phoenix)
- Brokers: Pure REST API clients

## cli/ - CLI interface for financial data aggregator
- cli/commands/accounts.py: fn:list_accounts,show_account,account_summary
- cli/commands/config.py: fn:show,set,setup,manage_card_holder,list_card_holders
- cli/commands/export.py: fn:serialize_date,export_transactions,export_transactions_csv,export_transactions_json,export_balances
- cli/commands/init.py: fn:main
- cli/commands/maintenance.py: fn:cleanup,backup,verify
- cli/commands/reports.py: fn:make_bar,make_sparkline,get_trend_indicator,format_change,generate_insights
- cli/commands/rules.py: fn:list_rules,add_rule,remove_rule,apply_rules,init_rules
- cli/commands/sync.py: fn:sync_all,sync_excellence,sync_meitav,sync_migdal,sync_phoenix
- cli/commands/tags.py: fn:list_tags,rename_tag,delete_tag,migrate_categories
- cli/commands/transactions.py: fn:browse_transactions,list_transactions,show_transaction,tag_transaction,untag_transaction
- cli/main.py: fn:setup_logging,version,callback,main
- cli/tui/browser.py: class:EditScreen,TagScreen,TransactionBrowser | fn:run_browser
- cli/utils.py: fn:print_success,print_error,print_warning,print_info,create_table

## config/ - Configuration management for financial data aggreg
- config/constants.py: class:AccountType,Institution,SyncType,SyncStatus,TransactionStatus
- config/settings.py: class:BrokerCredentials,PensionCredentials,CreditCardCredentials,EmailCredentials,Credentials | fn:get_encryption_key,encrypt_credentials,decrypt_credentials,save_credentials,load_credentials

## db/ - Database layer for financial data aggregator
- db/database.py: fn:get_database_url,enable_foreign_keys,create_database_engine,init_db,drop_all_tables
- db/migrations/add_indexes.py: fn:run_migration,rollback_migration,check_indexes
- db/models.py: class:Account,Transaction,Balance,SyncHistory,Tag

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
- scrapers/credit_cards/cal_credit_card_client.py: class:CALCredentials,TransactionStatus,TransactionType,TrnTypeCode,Installments | fn:main
- scrapers/credit_cards/isracard_credit_card_client.py: class:IsracardCredentials,TransactionStatus,TransactionType,Installments,Transaction | fn:main
- scrapers/credit_cards/max_credit_card_client.py: class:MaxCredentials,TransactionStatus,TransactionType,MaxPlanName,Installments | fn:main
- scrapers/exceptions.py: class:ScraperError,AuthenticationError,LoginFailedError,MFAFailedError,SessionExpiredError
- scrapers/pensions/migdal_pension_client.py: class:MigdalEmailMFARetriever,MigdalSeleniumMFAAutomator | fn:main
- scrapers/pensions/phoenix_pension_client.py: class:PhoenixEmailMFARetriever,PhoenixSeleniumMFAAutomator | fn:main
- scrapers/utils/retry.py: fn:retry_with_backoff,retry_selenium_action,retry_api_call
- scrapers/utils/wait_conditions.py: class:SmartWait

## services/ - Services package for data synchronization and anal
- services/analytics_service.py: class:AnalyticsService | fn:get_effective_amount,effective_amount_expr,effective_category_expr
- services/base_service.py: class:BaseSyncService
- services/broker_service.py: class:BrokerSyncResult,BrokerService
- services/credit_card_service.py: class:CreditCardSyncResult,CreditCardService
- services/pension_service.py: class:PensionSyncResult,PensionService
- services/rules_service.py: class:MatchType,Rule,RulesService
- services/tag_service.py: class:TagService

## streamlit_app/
- streamlit_app/app.py: fn:load_custom_css
- streamlit_app/components/bulk_actions.py: fn:show_bulk_preview,show_bulk_confirmation,bulk_action_workflow,quick_bulk_preview
- streamlit_app/components/charts.py: fn:spending_donut,trend_line,category_bar,balance_history,spending_by_day
- streamlit_app/components/empty_states.py: fn:empty_transactions_state,empty_search_results,empty_accounts_state,empty_analytics_state,empty_dashboard_state
- streamlit_app/components/filters.py: fn:date_range_filter,account_filter,institution_filter,status_filter,category_filter
- streamlit_app/components/heatmap.py: fn:calendar_heatmap,monthly_heatmap
- streamlit_app/components/loading.py: class:ProgressTracker | fn:show_progress_steps,contextual_spinner,skeleton_table,skeleton_metrics,show_loading_message
- streamlit_app/components/responsive.py: fn:responsive_columns,mobile_card,responsive_metrics,responsive_table_config,stacked_layout
- streamlit_app/components/sidebar.py: fn:render_quick_stats,render_about,render_minimal_sidebar
- streamlit_app/components/theme.py: fn:init_theme,render_theme_switcher,apply_theme,format_category_badge_themed,format_tags_themed
- streamlit_app/config/theme.py: class:ColorPalette,Theme | fn:get_theme,set_theme_mode
- streamlit_app/pages/1_📊_Dashboard.py: Dashboard Page - High-level overview of financial status
- streamlit_app/pages/2_🔄_Sync.py: Sync Management Page - Trigger sync and view sync status
- streamlit_app/pages/3_💳_Transactions.py: Transactions Browser Page - View, filter, search, and manage
- streamlit_app/pages/4_📈_Analytics.py: fn:time_range_selector
- streamlit_app/pages/5_🏷️_Tags.py: Tags Management Page - Create, edit, and manage transaction 
- streamlit_app/pages/6_📋_Rules.py: Rules Management Page - Manage auto-categorization and taggi
- streamlit_app/pages/7_💰_Accounts.py: Accounts Management Page - View and manage financial account
- streamlit_app/pages/8_⚙️_Settings.py: Settings Page - Application configuration and management
- streamlit_app/utils/cache.py: fn:get_transactions_cached,get_dashboard_stats,get_category_spending_cached,get_monthly_trend_cached,get_accounts_cached
- streamlit_app/utils/errors.py: class:ErrorBoundary | fn:safe_service_call,get_user_friendly_error,safe_call_with_spinner,handle_error_with_retry,safe_decorator
- streamlit_app/utils/formatters.py: fn:format_currency,format_date,format_datetime,format_number,format_percentage
- streamlit_app/utils/insights.py: fn:generate_spending_insight,generate_balance_insight,generate_pending_insight,generate_category_insight,get_time_greeting
- streamlit_app/utils/rtl.py: fn:has_hebrew,fix_rtl,format_description,mixed_rtl_ltr,clean_merchant_name
- streamlit_app/utils/session.py: fn:init_session_state,get_analytics_service,get_tag_service,get_rules_service,get_credit_card_service
