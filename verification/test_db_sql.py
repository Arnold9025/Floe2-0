import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import importlib

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Do not import db here, import it after mocking

class TestPostgresLogic(unittest.TestCase):
    
    def setUp(self):
        # Mock psycopg2 before importing db
        self.mock_psycopg2 = MagicMock()
        self.mock_psycopg2.extras.RealDictCursor = MagicMock()
        
        self.modules_patcher = patch.dict(sys.modules, {'psycopg2': self.mock_psycopg2, 'psycopg2.extras': self.mock_psycopg2.extras})
        self.modules_patcher.start()
        
        # Now import db
        from execution import db
        self.db = db
        importlib.reload(self.db) # Reload to pick up the mock
        
    def tearDown(self):
        self.modules_patcher.stop()

    def test_get_db_connection_postgres(self):
        """Test that get_db_connection uses psycopg2 when DATABASE_URL is set"""
        self.db.DATABASE_URL = "postgres://user:pass@localhost:5432/db"
        
        conn = self.db.get_db_connection()
        
        self.mock_psycopg2.connect.assert_called_with(
            "postgres://user:pass@localhost:5432/db", 
            cursor_factory=self.mock_psycopg2.extras.RealDictCursor
        )
        
    def test_execute_query_transformation(self):
        """Test that execute_query transforms SQLite syntax to Postgres syntax"""
        self.db.DATABASE_URL = "postgres://user:pass@localhost:5432/db"
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        
        # SQLite style query
        query = "INSERT INTO table (col) VALUES (?)"
        params = (1,)
        
        self.db.execute_query(mock_conn, query, params)
        
        # Check if transformed to Postgres style (%s)
        mock_cursor.execute.assert_called_with(
            "INSERT INTO table (col) VALUES (%s)", 
            params
        )

    def test_execute_query_autoincrement_transformation(self):
        """Test transformation of AUTOINCREMENT to SERIAL"""
        self.db.DATABASE_URL = "postgres://user:pass@localhost:5432/db"
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        
        query = "CREATE TABLE test (id INTEGER PRIMARY KEY AUTOINCREMENT)"
        
        self.db.execute_query(mock_conn, query)
        
        mock_cursor.execute.assert_called_with(
            "CREATE TABLE test (id SERIAL PRIMARY KEY)", 
            ()
        )

if __name__ == '__main__':
    unittest.main()
