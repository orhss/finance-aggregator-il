"""
Interactive Transaction Browser TUI

A Textual-based terminal UI for browsing, searching, tagging, and editing transactions.
"""

from datetime import date, datetime
from typing import Optional, List, Dict, Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import DataTable, Header, Footer, Input, Static, Button, Label, OptionList
from textual.widgets.option_list import Option
from textual.containers import Container, Horizontal, Vertical, Grid
from textual.screen import ModalScreen
from textual.message import Message
from textual import on

from services.analytics_service import AnalyticsService
from services.tag_service import TagService
from cli.utils import fix_rtl


class EditScreen(ModalScreen):
    """Modal screen for editing transaction category"""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, transaction_id: int, transaction_data: Dict[str, Any]):
        super().__init__()
        self.transaction_id = transaction_id
        self.transaction_data = transaction_data

    def compose(self) -> ComposeResult:
        # Apply RTL fix for Hebrew text in description and categories
        description = fix_rtl(self.transaction_data.get('description', 'N/A'))
        raw_category = fix_rtl(self.transaction_data.get('raw_category', '') or '')
        normalized_category = fix_rtl(self.transaction_data.get('category', '') or '')

        with Container(id="edit-dialog"):
            yield Static("Edit Transaction", id="edit-title")
            yield Static(f"Date: {self.transaction_data.get('date', 'N/A')}", classes="edit-field")
            yield Static(f"Description: {description}", classes="edit-field")
            yield Static(f"Amount: {self.transaction_data.get('amount', 'N/A')}", classes="edit-field")
            # Show category hierarchy
            if raw_category:
                yield Static(f"Provider Category: {raw_category}", classes="edit-field")
            if normalized_category and normalized_category != raw_category:
                yield Static(f"Normalized: {normalized_category}", classes="edit-field")
            yield Label("Your Category Override:")
            yield Input(
                value=self.transaction_data.get('user_category', '') or '',
                placeholder="Enter category override...",
                id="category-input"
            )
            with Horizontal(id="edit-buttons"):
                yield Button("Save", variant="primary", id="save-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

    @on(Button.Pressed, "#save-btn")
    def handle_save(self) -> None:
        category_input = self.query_one("#category-input", Input)
        new_category = category_input.value.strip()

        tag_service = TagService()
        success = tag_service.update_transaction(
            self.transaction_id,
            user_category=new_category if new_category else None
        )

        if success:
            self.dismiss({"saved": True, "category": new_category})
        else:
            self.dismiss({"saved": False, "error": "Failed to save"})

    @on(Button.Pressed, "#cancel-btn")
    def handle_cancel(self) -> None:
        self.dismiss({"saved": False})

    def action_cancel(self) -> None:
        self.dismiss({"saved": False})


class TagScreen(ModalScreen):
    """Modal screen for adding/removing tags with autocomplete"""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("down", "focus_suggestions", "Suggestions", show=False),
    ]

    def __init__(self, transaction_id: int, current_tags: List[str]):
        super().__init__()
        self.transaction_id = transaction_id
        self.current_tags = current_tags
        self.all_tags: List[str] = []

    def compose(self) -> ComposeResult:
        with Container(id="tag-dialog"):
            yield Static("Manage Tags", id="tag-title")
            yield Static(self._format_current_tags(), id="current-tags")
            yield Label("Tag name:")
            yield Input(placeholder="Enter or select tag...", id="tag-input")
            yield OptionList(id="tag-suggestions")
            with Horizontal(id="tag-buttons"):
                yield Button("Add", variant="primary", id="add-btn")
                yield Button("Remove", variant="warning", id="remove-btn")
                yield Button("Close", variant="default", id="close-btn")

    def on_mount(self) -> None:
        """Load all existing tags when screen mounts"""
        tag_service = TagService()
        tags = tag_service.get_all_tags()
        self.all_tags = [tag.name for tag in tags]
        # Initially hide suggestions
        self.query_one("#tag-suggestions", OptionList).display = False

    def _format_current_tags(self) -> str:
        """Format current tags with RTL support"""
        if not self.current_tags:
            return "Current tags: (none)"
        # Apply RTL fix to each tag for proper Hebrew display
        formatted_tags = [fix_rtl(tag) for tag in self.current_tags]
        return f"Current tags: {', '.join(formatted_tags)}"

    def _update_suggestions(self, query: str) -> None:
        """Update suggestion list based on input"""
        option_list = self.query_one("#tag-suggestions", OptionList)
        option_list.clear_options()

        if not query:
            option_list.display = False
            return

        # Filter tags that match the query (case-insensitive)
        query_lower = query.lower()
        matching = [tag for tag in self.all_tags if query_lower in tag.lower()]

        if matching:
            for tag in matching[:10]:  # Limit to 10 suggestions
                # Display with RTL fix for Hebrew tags
                option_list.add_option(Option(fix_rtl(tag), id=tag))
            option_list.display = True
        else:
            option_list.display = False

    @on(Input.Changed, "#tag-input")
    def handle_input_changed(self, event: Input.Changed) -> None:
        """Update suggestions as user types"""
        self._update_suggestions(event.value)

    @on(OptionList.OptionSelected, "#tag-suggestions")
    def handle_suggestion_selected(self, event: OptionList.OptionSelected) -> None:
        """Fill input with selected suggestion"""
        if event.option.id:
            tag_input = self.query_one("#tag-input", Input)
            tag_input.value = str(event.option.id)
            self.query_one("#tag-suggestions", OptionList).display = False
            tag_input.focus()

    def action_focus_suggestions(self) -> None:
        """Focus the suggestions list"""
        option_list = self.query_one("#tag-suggestions", OptionList)
        if option_list.display and option_list.option_count > 0:
            option_list.focus()

    @on(Button.Pressed, "#add-btn")
    def handle_add(self) -> None:
        tag_input = self.query_one("#tag-input", Input)
        tag_name = tag_input.value.strip()

        if tag_name:
            tag_service = TagService()
            added = tag_service.tag_transaction(self.transaction_id, [tag_name])
            if added > 0:
                self.current_tags.append(tag_name)
                # Add to all_tags if it's new
                if tag_name not in self.all_tags:
                    self.all_tags.append(tag_name)
                self.query_one("#current-tags", Static).update(self._format_current_tags())
            tag_input.value = ""
            self.query_one("#tag-suggestions", OptionList).display = False

    @on(Button.Pressed, "#remove-btn")
    def handle_remove(self) -> None:
        tag_input = self.query_one("#tag-input", Input)
        tag_name = tag_input.value.strip()

        if tag_name and tag_name in self.current_tags:
            tag_service = TagService()
            removed = tag_service.untag_transaction(self.transaction_id, [tag_name])
            if removed > 0:
                self.current_tags.remove(tag_name)
                self.query_one("#current-tags", Static).update(self._format_current_tags())
            tag_input.value = ""
            self.query_one("#tag-suggestions", OptionList).display = False

    @on(Button.Pressed, "#close-btn")
    def handle_close(self) -> None:
        self.dismiss({"tags": self.current_tags})

    def action_cancel(self) -> None:
        self.dismiss({"tags": self.current_tags})


class TransactionBrowser(App):
    """Interactive transaction browser TUI"""

    CSS = """
    Screen {
        background: $surface;
    }

    #search-container {
        height: 3;
        padding: 0 1;
    }

    #search-input {
        width: 100%;
    }

    #transactions-table {
        height: 1fr;
    }

    #status-bar {
        height: 1;
        padding: 0 1;
        background: $primary;
        color: $text;
    }

    /* Edit dialog styles */
    #edit-dialog {
        width: 60;
        height: auto;
        padding: 1 2;
        background: $surface;
        border: solid $primary;
    }

    #edit-title {
        text-align: center;
        text-style: bold;
        padding-bottom: 1;
    }

    .edit-field {
        padding: 0 0 0 1;
    }

    #edit-buttons {
        padding-top: 1;
        align: center middle;
    }

    #edit-buttons Button {
        margin: 0 1;
    }

    /* Tag dialog styles */
    #tag-dialog {
        width: 70;
        height: auto;
        padding: 1 2;
        background: $surface;
        border: solid $primary;
    }

    #tag-title {
        text-align: center;
        text-style: bold;
        padding-bottom: 1;
    }

    #current-tags {
        padding: 0 0 1 0;
        color: $text-muted;
    }

    #tag-input {
        width: 100%;
    }

    #tag-suggestions {
        max-height: 8;
        width: 100%;
        background: $surface-darken-1;
        border: solid $primary-darken-1;
        margin-top: 0;
        padding: 0;
    }

    #tag-suggestions:focus {
        border: solid $primary;
    }

    #tag-suggestions > .option-list--option {
        padding: 0 1;
    }

    #tag-buttons {
        padding-top: 1;
        align: center middle;
    }

    #tag-buttons Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("escape", "quit", "Quit"),
        Binding("t", "tag", "Tag"),
        Binding("e", "edit", "Edit"),
        Binding("enter", "edit", "Edit"),
        Binding("r", "refresh", "Refresh"),
        Binding("/", "focus_search", "Search"),
        Binding("m", "load_more", "More"),
    ]

    PAGE_SIZE = 500  # Number of transactions per page

    def __init__(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        tags: Optional[List[str]] = None,
        untagged_only: bool = False,
        institution: Optional[str] = None,
    ):
        super().__init__()
        self.filter_from_date = from_date
        self.filter_to_date = to_date
        self.filter_tags = tags
        self.filter_untagged = untagged_only
        self.filter_institution = institution
        self.transactions: List[Any] = []
        self.transaction_map: Dict[str, int] = {}  # row_key -> transaction_id
        self.search_text = ""
        self.current_offset = 0
        self.has_more = True  # Whether there are more transactions to load

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="search-container"):
            yield Input(placeholder="Type to filter... (press / to focus)", id="search-input")
        yield DataTable(id="transactions-table")
        yield Static("", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the table and load data"""
        table = self.query_one("#transactions-table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True

        # Add columns
        table.add_column("ID", width=6)
        table.add_column("Date", width=12)
        table.add_column("Description", width=30)
        table.add_column("Amount", width=15)
        table.add_column("Card", width=6)
        table.add_column("Category", width=18)
        table.add_column("Tags", width=35)

        self.load_transactions()

    def load_transactions(self, append: bool = False) -> None:
        """Load transactions from database

        Args:
            append: If True, append to existing transactions instead of replacing
        """
        analytics = AnalyticsService()
        tag_service = TagService()

        if not append:
            # Reset pagination when doing a fresh load
            self.current_offset = 0
            self.transactions = []

        new_transactions = analytics.get_transactions(
            from_date=self.filter_from_date,
            to_date=self.filter_to_date,
            tags=self.filter_tags,
            untagged_only=self.filter_untagged,
            institution=self.filter_institution,
            limit=self.PAGE_SIZE,
            offset=self.current_offset
        )

        # Check if there are more transactions to load
        self.has_more = len(new_transactions) == self.PAGE_SIZE

        if append:
            self.transactions.extend(new_transactions)
        else:
            self.transactions = new_transactions

        table = self.query_one("#transactions-table", DataTable)

        if not append:
            table.clear()
            self.transaction_map.clear()

        # Only add the new transactions to the table
        transactions_to_add = new_transactions if append else self.transactions

        for txn in transactions_to_add:
            # Get tags for this transaction (needed for both filtering and display)
            txn_tags = tag_service.get_transaction_tags(txn.id)
            tag_names = [t.name.lower() for t in txn_tags]

            # Apply search filter - search in description, categories (raw, normalized, user), and tags
            if self.search_text:
                search_lower = self.search_text.lower()
                matches_description = search_lower in (txn.description or '').lower()
                matches_raw_category = search_lower in (txn.raw_category or '').lower()
                matches_category = search_lower in (txn.category or '').lower()
                matches_user_category = search_lower in (txn.user_category or '').lower()
                matches_tags = any(search_lower in tag for tag in tag_names)

                if not (matches_description or matches_raw_category or matches_category or matches_user_category or matches_tags):
                    continue

            tags_str = ", ".join([fix_rtl(t.name) for t in txn_tags[:4]]) if txn_tags else ""
            if len(txn_tags) > 4:
                tags_str += f" +{len(txn_tags) - 4}"

            # Format amount - use charged_amount (actual payment) if available
            amount = txn.charged_amount if txn.charged_amount is not None else txn.original_amount
            currency = txn.charged_currency or txn.original_currency
            amount_str = f"{amount:,.2f} {currency}"

            # Get effective category (user_category > category > raw_category)
            category = txn.effective_category or ""

            # Get card info from account
            account = analytics.get_account_by_id(txn.account_id)
            card_str = account.account_number if account else ""

            # Use processed_date for installments (when you actually pay), otherwise transaction_date
            if txn.installment_number and txn.processed_date:
                date_str = txn.processed_date.strftime("%Y-%m-%d")
            else:
                date_str = txn.transaction_date.strftime("%Y-%m-%d")

            row_key = table.add_row(
                str(txn.id),
                date_str,
                fix_rtl(txn.description[:30]) if txn.description else "",
                amount_str,
                card_str,
                fix_rtl(category[:18]) if category else "",
                tags_str,
            )
            self.transaction_map[row_key] = txn.id

        # Update status bar
        status = self.query_one("#status-bar", Static)
        filter_info = []
        if self.filter_from_date:
            filter_info.append(f"from:{self.filter_from_date}")
        if self.filter_to_date:
            filter_info.append(f"to:{self.filter_to_date}")
        if self.filter_tags:
            filter_info.append(f"tags:{','.join(self.filter_tags)}")
        if self.filter_untagged:
            filter_info.append("untagged")
        if self.filter_institution:
            filter_info.append(f"inst:{self.filter_institution}")

        filter_str = f" | Filters: {' '.join(filter_info)}" if filter_info else ""
        more_str = " | [m] Load more" if self.has_more else ""
        status.update(f"Showing {table.row_count} transactions{filter_str}{more_str}")

        analytics.close()

    def get_selected_transaction(self) -> Optional[Dict[str, Any]]:
        """Get currently selected transaction data"""
        table = self.query_one("#transactions-table", DataTable)

        if table.row_count == 0:
            return None

        row_key = table.cursor_row
        if row_key is None or row_key >= table.row_count:
            return None

        # Get the row key from cursor position
        cursor_row = table.cursor_row
        row_keys = list(self.transaction_map.keys())
        if cursor_row >= len(row_keys):
            return None

        row_key = row_keys[cursor_row]
        txn_id = self.transaction_map.get(row_key)

        if not txn_id:
            return None

        # Find the transaction
        for txn in self.transactions:
            if txn.id == txn_id:
                tag_service = TagService()
                txn_tags = tag_service.get_transaction_tags(txn.id)

                # Use charged_amount (actual payment) if available
                amount = txn.charged_amount if txn.charged_amount is not None else txn.original_amount
                currency = txn.charged_currency or txn.original_currency
                return {
                    "id": txn.id,
                    "date": txn.transaction_date.strftime("%Y-%m-%d"),
                    "description": txn.description,
                    "amount": f"{amount:,.2f} {currency}",
                    "raw_category": txn.raw_category or "",
                    "category": txn.category or "",
                    "user_category": txn.user_category or "",
                    "tags": [t.name for t in txn_tags],
                }

        return None

    def action_edit(self) -> None:
        """Open edit dialog for selected transaction"""
        txn_data = self.get_selected_transaction()
        if txn_data:
            self.push_screen(
                EditScreen(txn_data["id"], txn_data),
                self.on_edit_complete
            )

    def on_edit_complete(self, result: Dict[str, Any]) -> None:
        """Handle edit dialog completion"""
        if result.get("saved"):
            self.load_transactions()

    def action_tag(self) -> None:
        """Open tag dialog for selected transaction"""
        txn_data = self.get_selected_transaction()
        if txn_data:
            self.push_screen(
                TagScreen(txn_data["id"], txn_data["tags"]),
                self.on_tag_complete
            )

    def on_tag_complete(self, result: Dict[str, Any]) -> None:
        """Handle tag dialog completion"""
        self.load_transactions()

    def action_refresh(self) -> None:
        """Reload transactions"""
        self.load_transactions()

    def action_load_more(self) -> None:
        """Load the next page of transactions"""
        if not self.has_more:
            return

        # Update offset and load more
        self.current_offset += self.PAGE_SIZE
        self.load_transactions(append=True)

    def action_focus_search(self) -> None:
        """Focus the search input"""
        search_input = self.query_one("#search-input", Input)
        search_input.focus()

    def refresh_display(self) -> None:
        """Re-render the table with current transactions and search filter.

        Unlike load_transactions(), this does not reset pagination or query the database.
        It only re-applies the client-side search filter to already-loaded transactions.
        """
        table = self.query_one("#transactions-table", DataTable)
        table.clear()
        self.transaction_map.clear()

        tag_service = TagService()
        analytics = AnalyticsService()

        for txn in self.transactions:
            # Get tags for this transaction (needed for both filtering and display)
            txn_tags = tag_service.get_transaction_tags(txn.id)
            tag_names = [t.name.lower() for t in txn_tags]

            # Apply search filter - search in description, categories (raw, normalized, user), and tags
            if self.search_text:
                search_lower = self.search_text.lower()
                matches_description = search_lower in (txn.description or '').lower()
                matches_raw_category = search_lower in (txn.raw_category or '').lower()
                matches_category = search_lower in (txn.category or '').lower()
                matches_user_category = search_lower in (txn.user_category or '').lower()
                matches_tags = any(search_lower in tag for tag in tag_names)

                if not (matches_description or matches_raw_category or matches_category or matches_user_category or matches_tags):
                    continue

            tags_str = ", ".join([fix_rtl(t.name) for t in txn_tags[:4]]) if txn_tags else ""
            if len(txn_tags) > 4:
                tags_str += f" +{len(txn_tags) - 4}"

            # Format amount - use charged_amount (actual payment) if available
            amount = txn.charged_amount if txn.charged_amount is not None else txn.original_amount
            currency = txn.charged_currency or txn.original_currency
            amount_str = f"{amount:,.2f} {currency}"

            # Get effective category (user_category > category > raw_category)
            category = txn.effective_category or ""

            # Get card info from account
            account = analytics.get_account_by_id(txn.account_id)
            card_str = account.account_number if account else ""

            # Use processed_date for installments (when you actually pay), otherwise transaction_date
            if txn.installment_number and txn.processed_date:
                date_str = txn.processed_date.strftime("%Y-%m-%d")
            else:
                date_str = txn.transaction_date.strftime("%Y-%m-%d")

            row_key = table.add_row(
                str(txn.id),
                date_str,
                fix_rtl(txn.description[:30]) if txn.description else "",
                amount_str,
                card_str,
                fix_rtl(category[:18]) if category else "",
                tags_str,
            )
            self.transaction_map[row_key] = txn.id

        analytics.close()

        # Update status bar
        status = self.query_one("#status-bar", Static)
        filter_info = []
        if self.filter_from_date:
            filter_info.append(f"from:{self.filter_from_date}")
        if self.filter_to_date:
            filter_info.append(f"to:{self.filter_to_date}")
        if self.filter_tags:
            filter_info.append(f"tags:{','.join(self.filter_tags)}")
        if self.filter_untagged:
            filter_info.append("untagged")
        if self.filter_institution:
            filter_info.append(f"inst:{self.filter_institution}")
        if self.search_text:
            filter_info.append(f"search:\"{self.search_text}\"")

        filter_str = f" | Filters: {' '.join(filter_info)}" if filter_info else ""
        more_str = " | [m] Load more" if self.has_more else ""
        status.update(f"Showing {table.row_count} transactions{filter_str}{more_str}")

    @on(Input.Changed, "#search-input")
    def on_search_changed(self, event: Input.Changed) -> None:
        """Filter transactions based on search input"""
        self.search_text = event.value
        self.refresh_display()


def run_browser(
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    tags: Optional[List[str]] = None,
    untagged_only: bool = False,
    institution: Optional[str] = None,
) -> None:
    """Run the transaction browser TUI"""
    app = TransactionBrowser(
        from_date=from_date,
        to_date=to_date,
        tags=tags,
        untagged_only=untagged_only,
        institution=institution,
    )
    app.run()