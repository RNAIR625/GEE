-- Canadian Tax Database
-- Contains GST, HST, PST information by province/territory and postal codes

CREATE TABLE provinces (
    province_code TEXT PRIMARY KEY,
    province_name TEXT NOT NULL,
    gst_rate REAL DEFAULT 0.05,  -- 5% GST (federal)
    hst_rate REAL DEFAULT 0.0,   -- HST (replaces GST+PST in some provinces)
    pst_rate REAL DEFAULT 0.0,   -- Provincial Sales Tax
    combined_rate REAL NOT NULL, -- Total tax rate
    tax_type TEXT NOT NULL       -- 'GST+PST', 'HST', 'GST_ONLY'
);

CREATE TABLE postal_codes (
    postal_code TEXT PRIMARY KEY,
    province_code TEXT NOT NULL,
    city TEXT,
    region TEXT,
    FOREIGN KEY (province_code) REFERENCES provinces(province_code)
);

CREATE TABLE product_categories (
    category_id INTEGER PRIMARY KEY,
    category_name TEXT NOT NULL,
    description TEXT,
    tax_exempt BOOLEAN DEFAULT 0  -- Some products may be tax exempt
);

CREATE TABLE products (
    product_code TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    category_id INTEGER,
    base_price REAL NOT NULL,
    tax_exempt BOOLEAN DEFAULT 0,
    FOREIGN KEY (category_id) REFERENCES product_categories(category_id)
);

-- Insert Canadian provinces/territories with correct tax rates (2024)
INSERT INTO provinces VALUES 
('ON', 'Ontario', 0.0, 0.13, 0.0, 0.13, 'HST'),           -- 13% HST
('QC', 'Quebec', 0.05, 0.0, 0.09975, 0.14975, 'GST+PST'), -- 5% GST + 9.975% PST
('BC', 'British Columbia', 0.05, 0.0, 0.07, 0.12, 'GST+PST'), -- 5% GST + 7% PST
('AB', 'Alberta', 0.05, 0.0, 0.0, 0.05, 'GST_ONLY'),      -- 5% GST only
('SK', 'Saskatchewan', 0.05, 0.0, 0.06, 0.11, 'GST+PST'), -- 5% GST + 6% PST
('MB', 'Manitoba', 0.05, 0.0, 0.07, 0.12, 'GST+PST'),     -- 5% GST + 7% PST
('NB', 'New Brunswick', 0.0, 0.15, 0.0, 0.15, 'HST'),     -- 15% HST
('NS', 'Nova Scotia', 0.0, 0.15, 0.0, 0.15, 'HST'),       -- 15% HST
('PE', 'Prince Edward Island', 0.0, 0.15, 0.0, 0.15, 'HST'), -- 15% HST
('NL', 'Newfoundland and Labrador', 0.0, 0.15, 0.0, 0.15, 'HST'), -- 15% HST
('YT', 'Yukon', 0.05, 0.0, 0.0, 0.05, 'GST_ONLY'),        -- 5% GST only
('NT', 'Northwest Territories', 0.05, 0.0, 0.0, 0.05, 'GST_ONLY'), -- 5% GST only
('NU', 'Nunavut', 0.05, 0.0, 0.0, 0.05, 'GST_ONLY');      -- 5% GST only

-- Insert sample postal codes for major cities
INSERT INTO postal_codes VALUES 
-- Ontario
('M5V', 'ON', 'Toronto', 'Central'),
('K1A', 'ON', 'Ottawa', 'Eastern'),
('L8S', 'ON', 'Hamilton', 'Central'),
('N2L', 'ON', 'Waterloo', 'Southwestern'),
-- Quebec  
('H3A', 'QC', 'Montreal', 'Montreal'),
('G1R', 'QC', 'Quebec City', 'Quebec City'),
-- British Columbia
('V6B', 'BC', 'Vancouver', 'Lower Mainland'),
('V8W', 'BC', 'Victoria', 'Vancouver Island'),
-- Alberta
('T2P', 'AB', 'Calgary', 'Southern'),
('T5J', 'AB', 'Edmonton', 'Central'),
-- Other provinces
('S4P', 'SK', 'Regina', 'Southern'),
('R3C', 'MB', 'Winnipeg', 'Central'),
('E1C', 'NB', 'Moncton', 'Southeast'),
('B3H', 'NS', 'Halifax', 'Central'),
('C1A', 'PE', 'Charlottetown', 'Queens'),
('A1C', 'NL', 'St. Johns', 'Avalon'),
('Y1A', 'YT', 'Whitehorse', 'Central'),
('X1A', 'NT', 'Yellowknife', 'North Slave'),
('X0A', 'NU', 'Iqaluit', 'Qikiqtaaluk');

-- Insert product categories
INSERT INTO product_categories VALUES 
(1, 'Electronics', 'Electronic devices and accessories', 0),
(2, 'Clothing', 'Apparel and accessories', 0),
(3, 'Food - Groceries', 'Basic food items', 1),  -- Often tax exempt
(4, 'Food - Restaurant', 'Prepared food and dining', 0),
(5, 'Books', 'Books and educational materials', 1), -- Often tax exempt
(6, 'Medical', 'Medical supplies and devices', 1),  -- Often tax exempt
(7, 'Automotive', 'Car parts and accessories', 0),
(8, 'Home & Garden', 'Household and garden items', 0);

-- Insert sample products
INSERT INTO products VALUES 
('LAPTOP001', 'Gaming Laptop', 1, 1299.99, 0),
('PHONE001', 'Smartphone', 1, 899.99, 0),
('SHIRT001', 'Cotton T-Shirt', 2, 29.99, 0),
('JEANS001', 'Blue Jeans', 2, 79.99, 0),
('BREAD001', 'Whole Wheat Bread', 3, 3.49, 1),
('MILK001', 'Organic Milk 1L', 3, 4.99, 1),
('PIZZA001', 'Large Pizza', 4, 18.99, 0),
('BOOK001', 'Programming Guide', 5, 49.99, 1),
('VITAMIN001', 'Multivitamin', 6, 24.99, 1),
('TIRE001', 'All-Season Tire', 7, 149.99, 0),
('HAMMER001', 'Claw Hammer', 8, 19.99, 0);

-- Create indexes for better performance
CREATE INDEX idx_postal_province ON postal_codes(province_code);
CREATE INDEX idx_product_category ON products(category_id);
CREATE INDEX idx_product_exempt ON products(tax_exempt);