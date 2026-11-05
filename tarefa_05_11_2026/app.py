import math
import os
import sqlite3
from pathlib import Path

from flask import Flask, flash, g, redirect, render_template, request, url_for


BASE_DIR = Path(__file__).resolve().parent
ALLOWED_ITEM_TYPES = {"Hardware", "Software", "Periférico"}
ALLOWED_MOVEMENTS = {"Entrada", "Saída"}


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "techstock-manager-dev-key"),
        DATABASE=os.environ.get("DATABASE_PATH", str(BASE_DIR / "techstock.db")),
    )
    if test_config:
        app.config.update(test_config)

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"], timeout=10)
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
        return g.db

    @app.teardown_appcontext
    def close_db(_error=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def initialize_database():
        db = get_db()
        has_tables = db.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'products'"
        ).fetchone()
        if not has_tables:
            db.executescript((BASE_DIR / "database.sql").read_text(encoding="utf-8"))

    with app.app_context():
        initialize_database()

    def get_catalog_options():
        db = get_db()
        categories = db.execute(
            "SELECT id, name FROM categories ORDER BY name"
        ).fetchall()
        suppliers = db.execute(
            "SELECT id, company_name FROM suppliers ORDER BY company_name"
        ).fetchall()
        return categories, suppliers

    @app.get("/")
    def dashboard():
        db = get_db()
        products = db.execute(
            """
            SELECT p.id, p.sku, p.name, p.manufacturer, p.item_type,
                   p.price, p.stock, p.min_stock, p.location, p.licensing_model,
                   c.name AS category_name, s.company_name AS supplier_name
            FROM products AS p
            INNER JOIN categories AS c ON c.id = p.category_id
            INNER JOIN suppliers AS s ON s.id = p.supplier_id
            WHERE p.active = 1
            ORDER BY CASE WHEN p.stock <= p.min_stock THEN 0 ELSE 1 END,
                     p.name
            """
        ).fetchall()
        stats = db.execute(
            """
            SELECT COUNT(*) AS product_count,
                   COALESCE(SUM(stock), 0) AS unit_count,
                   COALESCE(SUM(CASE WHEN stock <= min_stock THEN 1 ELSE 0 END), 0)
                       AS alert_count
            FROM products
            WHERE active = 1
            """
        ).fetchone()
        movements = db.execute(
            """
            SELECT m.operation, m.quantity, m.created_at, m.note, p.name, p.sku
            FROM movements AS m
            INNER JOIN products AS p ON p.id = m.product_id
            ORDER BY m.id DESC
            LIMIT 6
            """
        ).fetchall()
        return render_template(
            "dashboard.html", products=products, stats=stats, movements=movements
        )

    @app.route("/products/new", methods=["GET", "POST"])
    def new_product():
        categories, suppliers = get_catalog_options()
        if request.method == "POST":
            form = request.form
            sku = form.get("sku", "").strip()
            name = form.get("name", "").strip()
            manufacturer = form.get("manufacturer", "").strip()
            item_type = form.get("item_type", "").strip()
            specification = form.get("specification", "").strip()
            licensing_model = form.get("licensing_model", "").strip()
            location = form.get("location", "").strip()
            try:
                price = float(form.get("price", ""))
                stock = int(form.get("stock", ""))
                min_stock = int(form.get("min_stock", ""))
                category_id = int(form.get("category_id", ""))
                supplier_id = int(form.get("supplier_id", ""))
            except (TypeError, ValueError):
                flash("Preencha preço, saldo, estoque mínimo, categoria e fornecedor corretamente.", "error")
                return render_template(
                    "product_form.html",
                    categories=categories,
                    suppliers=suppliers,
                    form=form,
                )

            if not all((sku, name, manufacturer, specification, location)):
                flash("Preencha todos os campos obrigatórios do produto.", "error")
            elif item_type not in ALLOWED_ITEM_TYPES:
                flash("Selecione uma classificação válida para o ativo.", "error")
            elif not math.isfinite(price) or price <= 0 or stock < 0 or min_stock < 0:
                flash("O preço deve ser maior que zero e os saldos não podem ser negativos.", "error")
            elif item_type == "Software" and not licensing_model:
                flash("Informe a modalidade de licenciamento do software.", "error")
            else:
                try:
                    db = get_db()
                    db.execute(
                        """
                        INSERT INTO products
                            (sku, name, manufacturer, item_type, specification,
                             licensing_model, price, stock, min_stock, location,
                             category_id, supplier_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            sku,
                            name,
                            manufacturer,
                            item_type,
                            specification,
                            licensing_model or None,
                            price,
                            stock,
                            min_stock,
                            location,
                            category_id,
                            supplier_id,
                        ),
                    )
                    db.commit()
                    flash("Ativo cadastrado com sucesso.", "success")
                    return redirect(url_for("dashboard"))
                except sqlite3.IntegrityError as exc:
                    get_db().rollback()
                    if "products.sku" in str(exc):
                        flash("Este SKU já está cadastrado. Informe um código único.", "error")
                    else:
                        flash("Não foi possível cadastrar o ativo. Confira categoria e fornecedor.", "error")
            return render_template(
                "product_form.html",
                categories=categories,
                suppliers=suppliers,
                form=form,
            )
        return render_template(
            "product_form.html", categories=categories, suppliers=suppliers, form={}
        )

    @app.route("/movements/new", methods=["GET", "POST"])
    def new_movement():
        db = get_db()
        products = db.execute(
            """
            SELECT id, sku, name, stock FROM products
            WHERE active = 1 ORDER BY name
            """
        ).fetchall()
        if request.method == "POST":
            form = request.form
            operation = form.get("operation", "")
            note = form.get("note", "").strip()
            try:
                product_id = int(form.get("product_id", ""))
                quantity = int(form.get("quantity", ""))
            except (TypeError, ValueError):
                flash("Selecione um ativo e informe uma quantidade inteira válida.", "error")
                return render_template("movement_form.html", products=products, form=form)
            if operation not in ALLOWED_MOVEMENTS:
                flash("Selecione uma operação válida.", "error")
            elif quantity <= 0:
                flash("A quantidade da movimentação deve ser maior que zero.", "error")
            else:
                try:
                    db.execute("BEGIN IMMEDIATE")
                    product = db.execute(
                        "SELECT id, stock FROM products WHERE id = ? AND active = 1",
                        (product_id,),
                    ).fetchone()
                    if product is None:
                        db.rollback()
                        flash("O ativo selecionado não existe ou está desativado.", "error")
                    elif operation == "Saída" and quantity > product["stock"]:
                        db.rollback()
                        flash(
                            f"Saldo insuficiente. Disponível: {product['stock']} unidade(s); "
                            f"solicitado: {quantity}.",
                            "error",
                        )
                    else:
                        delta = quantity if operation == "Entrada" else -quantity
                        db.execute(
                            "UPDATE products SET stock = stock + ? WHERE id = ?",
                            (delta, product_id),
                        )
                        db.execute(
                            """
                            INSERT INTO movements (operation, quantity, note, product_id)
                            VALUES (?, ?, ?, ?)
                            """,
                            (operation, quantity, note or None, product_id),
                        )
                        db.commit()
                        flash(f"{operation} registrada e saldo atualizado.", "success")
                        return redirect(url_for("dashboard"))
                except sqlite3.IntegrityError:
                    db.rollback()
                    flash("A movimentação não pôde ser registrada. Confira os dados informados.", "error")
            return render_template("movement_form.html", products=products, form=form)
        return render_template("movement_form.html", products=products, form={})

    @app.route("/catalogs", methods=["GET", "POST"])
    def catalogs():
        db = get_db()
        if request.method == "POST":
            catalog_type = request.form.get("catalog_type", "")
            try:
                if catalog_type == "category":
                    name = request.form.get("name", "").strip()
                    if not name:
                        flash("Informe o nome da categoria.", "error")
                    else:
                        db.execute("INSERT INTO categories (name) VALUES (?)", (name,))
                        db.commit()
                        flash("Categoria cadastrada.", "success")
                elif catalog_type == "supplier":
                    company_name = request.form.get("company_name", "").strip()
                    cnpj = request.form.get("cnpj", "").strip()
                    phone = request.form.get("phone", "").strip()
                    email = request.form.get("email", "").strip()
                    if not all((company_name, cnpj, phone, email)):
                        flash("Preencha todos os dados do fornecedor.", "error")
                    else:
                        db.execute(
                            """
                            INSERT INTO suppliers (company_name, cnpj, phone, email)
                            VALUES (?, ?, ?, ?)
                            """,
                            (company_name, cnpj, phone, email),
                        )
                        db.commit()
                        flash("Fornecedor cadastrado.", "success")
                else:
                    flash("Tipo de cadastro inválido.", "error")
            except sqlite3.IntegrityError as exc:
                db.rollback()
                if "categories.name" in str(exc):
                    flash("Já existe uma categoria com esse nome.", "error")
                elif "suppliers.cnpj" in str(exc):
                    flash("Já existe um fornecedor cadastrado com esse CNPJ.", "error")
                else:
                    flash("Não foi possível cadastrar. Confira os dados informados.", "error")
            return redirect(url_for("catalogs"))

        categories = db.execute(
            """
            SELECT c.id, c.name, COUNT(p.id) AS product_count
            FROM categories AS c
            LEFT JOIN products AS p ON p.category_id = c.id
            GROUP BY c.id ORDER BY c.name
            """
        ).fetchall()
        suppliers = db.execute(
            """
            SELECT s.id, s.company_name, s.cnpj, s.phone, s.email,
                   COUNT(p.id) AS product_count
            FROM suppliers AS s
            LEFT JOIN products AS p ON p.supplier_id = s.id
            GROUP BY s.id ORDER BY s.company_name
            """
        ).fetchall()
        return render_template("catalogs.html", categories=categories, suppliers=suppliers)

    @app.post("/catalogs/delete/<catalog_type>/<int:catalog_id>")
    def delete_catalog_entry(catalog_type, catalog_id):
        table = {"category": "categories", "supplier": "suppliers"}.get(catalog_type)
        if table is None:
            flash("Tipo de cadastro inválido.", "error")
            return redirect(url_for("catalogs"))
        db = get_db()
        try:
            cursor = db.execute(f"DELETE FROM {table} WHERE id = ?", (catalog_id,))
            db.commit()
            if cursor.rowcount:
                flash("Cadastro excluído.", "success")
            else:
                flash("O cadastro selecionado não foi encontrado.", "error")
        except sqlite3.IntegrityError:
            db.rollback()
            flash(
                "Não é possível excluir: existem ativos vinculados a este cadastro. "
                "Desative ou reatribua os ativos antes de tentar novamente.",
                "error",
            )
        return redirect(url_for("catalogs"))

    @app.post("/products/<int:product_id>/deactivate")
    def deactivate_product(product_id):
        db = get_db()
        cursor = db.execute(
            "UPDATE products SET active = 0 WHERE id = ? AND active = 1",
            (product_id,),
        )
        db.commit()
        if cursor.rowcount:
            flash("Ativo descontinuado. Seu histórico de movimentações foi preservado.", "success")
        else:
            flash("Ativo não encontrado ou já descontinuado.", "error")
        return redirect(url_for("dashboard"))

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
