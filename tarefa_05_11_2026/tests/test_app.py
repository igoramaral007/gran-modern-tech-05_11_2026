import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from app import create_app


class TechStockTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = str(Path(self.temp_dir.name) / "test.db")
        self.app = create_app(
            {"TESTING": True, "DATABASE": self.database, "SECRET_KEY": "test-key"}
        )
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def get_product(self, sku):
        with closing(sqlite3.connect(self.database)) as db:
            db.row_factory = sqlite3.Row
            return db.execute(
                "SELECT id, stock FROM products WHERE sku = ?", (sku,)
            ).fetchone()

    def test_database_has_required_seed_data(self):
        with closing(sqlite3.connect(self.database)) as db:
            category_count = db.execute(
                "SELECT COUNT(*) FROM categories"
            ).fetchone()[0]
            supplier_count = db.execute(
                "SELECT COUNT(*) FROM suppliers"
            ).fetchone()[0]
            product_count = db.execute(
                "SELECT COUNT(*) FROM products"
            ).fetchone()[0]
        self.assertEqual((category_count, supplier_count, product_count), (4, 3, 6))

    def test_dashboard_shows_joined_catalog_and_replenishment_warning(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Microsoft 365 Business Standard", response.data)
        self.assertIn(b"Risco de Ruptura / Reposi", response.data)
        self.assertIn(b"MicroParts Distribuidora Ltda.", response.data)
        self.assertIn(b"Assinatura anual", response.data)

    def test_rejects_outgoing_movement_above_available_stock(self):
        product = self.get_product("HW-RAM-002")
        response = self.client.post(
            "/movements/new",
            data={
                "product_id": product["id"],
                "operation": "Saída",
                "quantity": "4",
                "note": "Teste de saldo insuficiente",
            },
            follow_redirects=True,
        )
        self.assertIn("Saldo insuficiente".encode(), response.data)
        self.assertEqual(self.get_product("HW-RAM-002")["stock"], 3)

    def test_movement_updates_stock_and_records_audit_entry(self):
        product = self.get_product("HW-RAM-002")
        response = self.client.post(
            "/movements/new",
            data={
                "product_id": product["id"],
                "operation": "Entrada",
                "quantity": "5",
                "note": "Reposição de teste",
            },
            follow_redirects=True,
        )
        self.assertIn("Entrada registrada".encode(), response.data)
        self.assertEqual(self.get_product("HW-RAM-002")["stock"], 8)
        with closing(sqlite3.connect(self.database)) as db:
            movement = db.execute(
                "SELECT operation, quantity, note FROM movements ORDER BY id DESC LIMIT 1"
            ).fetchone()
        self.assertEqual(movement, ("Entrada", 5, "Reposição de teste"))

    def test_duplicate_sku_is_rejected(self):
        response = self.client.post(
            "/products/new",
            data={
                "sku": "HW-SSD-001",
                "name": "SSD duplicado",
                "manufacturer": "Marca",
                "item_type": "Hardware",
                "specification": "Teste",
                "price": "10",
                "stock": "0",
                "min_stock": "0",
                "location": "Prateleira",
                "category_id": "1",
                "supplier_id": "1",
            },
            follow_redirects=True,
        )
        self.assertIn("Este SKU já está cadastrado".encode(), response.data)
        with closing(sqlite3.connect(self.database)) as db:
            count = db.execute(
                "SELECT COUNT(*) FROM products WHERE sku = 'HW-SSD-001'"
            ).fetchone()[0]
        self.assertEqual(count, 1)

    def test_category_with_products_cannot_be_deleted(self):
        response = self.client.post(
            "/catalogs/delete/category/1", follow_redirects=True
        )
        self.assertIn("existem ativos vinculados".encode(), response.data)
        with closing(sqlite3.connect(self.database)) as db:
            category = db.execute(
                "SELECT name FROM categories WHERE id = 1"
            ).fetchone()
        self.assertEqual(category, ("Armazenamento",))

    def test_supplier_with_products_cannot_be_deleted(self):
        response = self.client.post(
            "/catalogs/delete/supplier/1", follow_redirects=True
        )
        self.assertIn("existem ativos vinculados".encode(), response.data)
        with closing(sqlite3.connect(self.database)) as db:
            supplier = db.execute(
                "SELECT company_name FROM suppliers WHERE id = 1"
            ).fetchone()
        self.assertEqual(supplier, ("MicroParts Distribuidora Ltda.",))

    def test_non_positive_product_price_is_rejected(self):
        response = self.client.post(
            "/products/new",
            data={
                "sku": "HW-PRICE-INVALID",
                "name": "Produto inválido",
                "manufacturer": "Marca",
                "item_type": "Hardware",
                "specification": "Teste",
                "price": "0",
                "stock": "0",
                "min_stock": "0",
                "location": "Prateleira",
                "category_id": "1",
                "supplier_id": "1",
            },
            follow_redirects=True,
        )
        self.assertIn("preço deve ser maior que zero".encode(), response.data)
        with closing(sqlite3.connect(self.database)) as db:
            count = db.execute(
                "SELECT COUNT(*) FROM products WHERE sku = 'HW-PRICE-INVALID'"
            ).fetchone()[0]
        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
