"""Tests for import CLI functionality including balance assertions."""

import pytest
from unittest.mock import Mock, MagicMock
from beanhub_import.data_types import GeneratedBalance, Amount, BeancountTransaction
from beanhub_cli.import_cli import (
    BalanceChangeSet,
    compute_balance_changes,
    _balance_needs_update,
    apply_balance_changes,
)


class TestBalanceChangeSet:
    """Test the BalanceChangeSet class."""
    
    def test_balance_change_set_initialization(self):
        """Test that BalanceChangeSet initializes correctly."""
        changes = BalanceChangeSet()
        assert changes.add == []
        assert changes.update == {}
        assert changes.remove == []


class TestComputeBalanceChanges:
    """Test the compute_balance_changes function."""
    
    def test_new_balance_assertion(self):
        """Test adding a new balance assertion."""
        # Create a new balance assertion
        balance = GeneratedBalance(
            sources=["test.ofx"],
            id="balance:Liabilities:Capital-One:2025-08-23",
            date="2025-08-23",
            account="Liabilities:Capital-One",
            amount=Amount(number="-100.22", currency="USD"),
            meta=None
        )
        
        # No existing transactions
        existing_txns = []
        
        changes = compute_balance_changes([balance], existing_txns, None)
        
        assert len(changes.add) == 1
        assert changes.add[0] == balance
        assert len(changes.update) == 0
        assert len(changes.remove) == 0
    
    def test_existing_balance_no_change(self):
        """Test that existing balance with no changes is not updated."""
        balance = GeneratedBalance(
            sources=["test.ofx"],
            id="balance:Liabilities:Capital-One:2025-08-23",
            date="2025-08-23",
            account="Liabilities:Capital-One",
            amount=Amount(number="-100.22", currency="USD"),
            meta=None
        )
        
        # Mock existing transaction with same content
        existing_txn = Mock(spec=BeancountTransaction)
        existing_txn.id = "balance:Liabilities:Capital-One:2025-08-23"
        existing_txn.lineno = 100
        existing_txn.__str__ = Mock(return_value="2025-08-23 balance Liabilities:Capital-One  -100.22 USD")
        
        changes = compute_balance_changes([balance], [existing_txn], None)
        
        assert len(changes.add) == 0
        assert len(changes.update) == 0
        assert len(changes.remove) == 0
    
    def test_existing_balance_needs_update(self):
        """Test that existing balance with changes is updated."""
        # New balance with different amount
        balance = GeneratedBalance(
            sources=["test.ofx"],
            id="balance:Liabilities:Capital-One:2025-08-23",
            date="2025-08-23",
            account="Liabilities:Capital-One",
            amount=Amount(number="-150.50", currency="USD"),  # Different amount
            meta=None
        )
        
        # Mock existing transaction with old amount
        existing_txn = Mock(spec=BeancountTransaction)
        existing_txn.id = "balance:Liabilities:Capital-One:2025-08-23"
        existing_txn.lineno = 100
        existing_txn.__str__ = Mock(return_value="2025-08-23 balance Liabilities:Capital-One  -100.22 USD")
        
        changes = compute_balance_changes([balance], [existing_txn], None)
        
        assert len(changes.add) == 0
        assert len(changes.update) == 1
        assert 100 in changes.update
        assert changes.update[100] == balance
        assert len(changes.remove) == 1
        assert changes.remove[0] == existing_txn


class TestBalanceNeedsUpdate:
    """Test the _balance_needs_update function."""
    
    def test_balance_needs_update_different_amount(self):
        """Test that balance needs update when amount changes."""
        new_balance = GeneratedBalance(
            sources=["test.ofx"],
            id="balance:Liabilities:Capital-One:2025-08-23",
            date="2025-08-23",
            account="Liabilities:Capital-One",
            amount=Amount(number="-150.50", currency="USD"),
            meta=None
        )
        
        existing_txn = Mock(spec=BeancountTransaction)
        existing_txn.__str__ = Mock(return_value="2025-08-23 balance Liabilities:Capital-One  -100.22 USD")
        
        assert _balance_needs_update(new_balance, existing_txn) == True
    
    def test_balance_needs_update_same_amount(self):
        """Test that balance doesn't need update when amount is same."""
        new_balance = GeneratedBalance(
            sources=["test.ofx"],
            id="balance:Liabilities:Capital-One:2025-08-23",
            date="2025-08-23",
            account="Liabilities:Capital-One",
            amount=Amount(number="-100.22", currency="USD"),
            meta=None
        )
        
        existing_txn = Mock(spec=BeancountTransaction)
        existing_txn.__str__ = Mock(return_value="2025-08-23 balance Liabilities:Capital-One  -100.22 USD")
        
        assert _balance_needs_update(new_balance, existing_txn) == False
    
    def test_balance_needs_update_different_account(self):
        """Test that balance needs update when account changes."""
        new_balance = GeneratedBalance(
            sources=["test.ofx"],
            id="balance:Liabilities:Capital-One:2025-08-23",
            date="2025-08-23",
            account="Liabilities:Capital-One-Secondary",  # Different account
            amount=Amount(number="-100.22", currency="USD"),
            meta=None
        )
        
        existing_txn = Mock(spec=BeancountTransaction)
        existing_txn.__str__ = Mock(return_value="2025-08-23 balance Liabilities:Capital-One  -100.22 USD")
        
        assert _balance_needs_update(new_balance, existing_txn) == True


class TestApplyBalanceChanges:
    """Test the apply_balance_changes function."""
    
    def test_apply_balance_changes_add_only(self):
        """Test applying balance changes with only additions."""
        # Mock tree and parser
        tree = Mock()
        tree.children = []
        parser = Mock()
        
        # Mock balance tree
        balance_tree = Mock()
        balance_tree.children = ["new_balance_entry"]
        parser.parse.return_value = balance_tree
        
        # Create changes with only additions
        changes = BalanceChangeSet()
        changes.add = [
            GeneratedBalance(
                sources=["test.ofx"],
                id="balance:Liabilities:Capital-One:2025-08-23",
                date="2025-08-23",
                account="Liabilities:Capital-One",
                amount=Amount(number="-100.22", currency="USD"),
                meta=None
            )
        ]
        
        result_tree = apply_balance_changes(tree, changes, parser)
        
        # Should have called parser.parse with balance content
        parser.parse.assert_called_once()
        # Should have added new balance to tree
        assert "new_balance_entry" in result_tree.children
    
    def test_apply_balance_changes_remove_and_add(self):
        """Test applying balance changes with removals and additions."""
        # Mock tree with existing entries
        tree = Mock()
        existing_entry = Mock()
        existing_entry.meta = Mock()
        existing_entry.meta.line = 100
        tree.children = [existing_entry, "other_entry"]
        
        parser = Mock()
        balance_tree = Mock()
        balance_tree.children = ["updated_balance_entry"]
        parser.parse.return_value = balance_tree
        
        # Create changes with removal and update
        changes = BalanceChangeSet()
        existing_txn = Mock()
        existing_txn.lineno = 100
        changes.remove = [existing_txn]
        changes.update = {
            100: GeneratedBalance(
                sources=["test.ofx"],
                id="balance:Liabilities:Capital-One:2025-08-23",
                date="2025-08-23",
                account="Liabilities:Capital-One",
                amount=Amount(number="-150.50", currency="USD"),
                meta=None
            )
        }
        
        result_tree = apply_balance_changes(tree, changes, parser)
        
        # Should have removed the old entry and added the new one
        assert existing_entry not in result_tree.children
        assert "other_entry" in result_tree.children
        assert "updated_balance_entry" in result_tree.children
