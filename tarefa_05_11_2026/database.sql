PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE CHECK (length(trim(name)) > 0)
);

CREATE TABLE IF NOT EXISTS suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL CHECK (length(trim(company_name)) > 0),
    cnpj TEXT NOT NULL UNIQUE CHECK (length(trim(cnpj)) > 0),
    phone TEXT NOT NULL,
    email TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT NOT NULL UNIQUE CHECK (length(trim(sku)) > 0),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    manufacturer TEXT NOT NULL,
    item_type TEXT NOT NULL CHECK (item_type IN ('Hardware', 'Software', 'Periférico')),
    specification TEXT NOT NULL,
    licensing_model TEXT,
    price NUMERIC NOT NULL CHECK (price > 0),
    stock INTEGER NOT NULL DEFAULT 0 CHECK (typeof(stock) = 'integer' AND stock >= 0),
    min_stock INTEGER NOT NULL DEFAULT 0 CHECK (typeof(min_stock) = 'integer' AND min_stock >= 0),
    location TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    category_id INTEGER NOT NULL,
    supplier_id INTEGER NOT NULL,
    CHECK (item_type != 'Software' OR length(trim(licensing_model)) > 0),
    FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE RESTRICT,
    FOREIGN KEY (supplier_id) REFERENCES suppliers (id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation TEXT NOT NULL CHECK (operation IN ('Entrada', 'Saída')),
    quantity INTEGER NOT NULL CHECK (typeof(quantity) = 'integer' AND quantity > 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    note TEXT,
    product_id INTEGER NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_products_category ON products (category_id);
CREATE INDEX IF NOT EXISTS idx_products_supplier ON products (supplier_id);
CREATE INDEX IF NOT EXISTS idx_products_stock ON products (stock, min_stock);
CREATE INDEX IF NOT EXISTS idx_movements_product_date ON movements (product_id, created_at);

INSERT OR IGNORE INTO categories (name) VALUES
    ('Armazenamento'),
    ('Processamento'),
    ('Suítes de Escritório'),
    ('Sistemas Operacionais');

INSERT OR IGNORE INTO suppliers (company_name, cnpj, phone, email) VALUES
    ('MicroParts Distribuidora Ltda.', '12.345.678/0001-90', '(11) 3333-1000', 'vendas@microparts.example'),
    ('TechLicenças Brasil S.A.', '23.456.789/0001-01', '(11) 3333-2000', 'comercial@techlicencas.example'),
    ('Distribuidora Central de TI Ltda.', '34.567.890/0001-12', '(21) 3333-3000', 'contato@centralti.example');

INSERT OR IGNORE INTO products
    (sku, name, manufacturer, item_type, specification, licensing_model,
     price, stock, min_stock, location, category_id, supplier_id)
VALUES
    ('HW-SSD-001', 'SSD NVMe 1 TB', 'Kingston', 'Hardware', 'NVMe PCIe 4.0, leitura até 3500 MB/s', NULL, 429.90, 12, 5, 'Prateleira A-01', 1, 1),
    ('HW-RAM-002', 'Memória DDR4 16 GB', 'Corsair', 'Hardware', 'DDR4 3200 MHz, módulo UDIMM', NULL, 219.90, 3, 5, 'Prateleira B-02', 2, 1),
    ('HW-CPU-003', 'Processador Core i5', 'Intel', 'Hardware', '10 núcleos, socket LGA1700', NULL, 1399.00, 7, 2, 'Bancada C-01', 2, 3),
    ('SW-M365-004', 'Microsoft 365 Business Standard', 'Microsoft', 'Software', 'Aplicativos Office e serviços em nuvem', 'Assinatura anual', 899.00, 25, 8, 'Cofre digital / M365', 3, 2),
    ('SW-WIN-005', 'Windows 11 Pro', 'Microsoft', 'Software', 'Sistema operacional versão Pro', 'OEM', 999.00, 4, 5, 'Cofre digital / Windows', 4, 2),
    ('PF-MOUSE-006', 'Mouse óptico USB', 'Logitech', 'Periférico', '1200 DPI, conexão USB-A', NULL, 69.90, 18, 6, 'Prateleira D-03', 2, 3);
