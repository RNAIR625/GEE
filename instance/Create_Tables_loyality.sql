  -- 1. CUSTOMERS table
  CREATE TABLE CUSTOMERS (
      customer_id TEXT PRIMARY KEY,
      email TEXT UNIQUE NOT NULL,
      first_name TEXT NOT NULL,
      last_name TEXT NOT NULL,
      phone TEXT,
      date_of_birth DATE,
      join_date DATETIME DEFAULT CURRENT_TIMESTAMP,
      current_tier_id INTEGER DEFAULT 1,
      lifetime_points INTEGER DEFAULT 0,
      status TEXT DEFAULT 'active' CHECK(status IN ('active', 'inactive', 'suspended')),
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (current_tier_id) REFERENCES LOYALTY_TIERS(tier_id)
  );

  -- 2. LOYALTY_TIERS table
  CREATE TABLE LOYALTY_TIERS (
      tier_id INTEGER PRIMARY KEY AUTOINCREMENT,
      tier_name TEXT UNIQUE NOT NULL,
      min_points INTEGER NOT NULL,
      max_points INTEGER,
      discount_percentage DECIMAL(5,2) DEFAULT 0,
      points_multiplier DECIMAL(3,2) DEFAULT 1.0,
      free_shipping BOOLEAN DEFAULT 0,
      priority_support BOOLEAN DEFAULT 0,
      color_code TEXT,
      icon_url TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  );

  -- 3. CUSTOMER_POINTS table
  CREATE TABLE CUSTOMER_POINTS (
      customer_id TEXT PRIMARY KEY,
      current_points INTEGER DEFAULT 0,
      pending_points INTEGER DEFAULT 0,
      expired_points INTEGER DEFAULT 0,
      last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (customer_id) REFERENCES CUSTOMERS(customer_id)
  );

  -- 4. POINTS_TRANSACTIONS table
  CREATE TABLE POINTS_TRANSACTIONS (
      transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
      customer_id TEXT NOT NULL,
      transaction_type TEXT NOT NULL CHECK(transaction_type IN ('earned', 'redeemed', 'expired', 'adjustment', 'bonus')),
      points INTEGER NOT NULL,
      balance_after INTEGER NOT NULL,
      reference_type TEXT,
      reference_id TEXT,
      description TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      expires_at DATETIME,
      FOREIGN KEY (customer_id) REFERENCES CUSTOMERS(customer_id)
  );

  -- 5. CUSTOMER_PREFERENCES table
  CREATE TABLE CUSTOMER_PREFERENCES (
      customer_id TEXT PRIMARY KEY,
      email_notifications BOOLEAN DEFAULT 1,
      sms_notifications BOOLEAN DEFAULT 0,
      preferred_categories TEXT, -- JSON array
      preferred_brands TEXT, -- JSON array
      language TEXT DEFAULT 'en',
      currency TEXT DEFAULT 'USD',
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (customer_id) REFERENCES CUSTOMERS(customer_id)
  );

  -- 6. ORDERS table
  CREATE TABLE ORDERS (
      order_id TEXT PRIMARY KEY,
      customer_id TEXT NOT NULL,
      order_date DATETIME DEFAULT CURRENT_TIMESTAMP,
      subtotal DECIMAL(10,2) NOT NULL,
      discount_amount DECIMAL(10,2) DEFAULT 0,
      tax_amount DECIMAL(10,2) DEFAULT 0,
      shipping_amount DECIMAL(10,2) DEFAULT 0,
      total_amount DECIMAL(10,2) NOT NULL,
      points_earned INTEGER DEFAULT 0,
      points_redeemed INTEGER DEFAULT 0,
      status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'processing', 'shipped', 'delivered', 'cancelled')),
      payment_status TEXT DEFAULT 'pending' CHECK(payment_status IN ('pending', 'paid', 'failed', 'refunded')),
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (customer_id) REFERENCES CUSTOMERS(customer_id)
  );

  -- 7. ORDER_ITEMS table
  CREATE TABLE ORDER_ITEMS (
      item_id INTEGER PRIMARY KEY AUTOINCREMENT,
      order_id TEXT NOT NULL,
      product_id TEXT NOT NULL,
      product_name TEXT NOT NULL,
      quantity INTEGER NOT NULL,
      unit_price DECIMAL(10,2) NOT NULL,
      discount_amount DECIMAL(10,2) DEFAULT 0,
      total_price DECIMAL(10,2) NOT NULL,
      points_earned INTEGER DEFAULT 0,
      FOREIGN KEY (order_id) REFERENCES ORDERS(order_id),
      FOREIGN KEY (product_id) REFERENCES PRODUCTS(product_id)
  );

  -- 8. PRODUCTS table
  CREATE TABLE PRODUCTS (
      product_id TEXT PRIMARY KEY,
      product_name TEXT NOT NULL,
      category TEXT NOT NULL,
      brand TEXT,
      price DECIMAL(10,2) NOT NULL,
      points_per_dollar INTEGER DEFAULT 1,
      bonus_points INTEGER DEFAULT 0,
      is_active BOOLEAN DEFAULT 1,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  );

  -- 9. DISCOUNT_RULES table
  CREATE TABLE DISCOUNT_RULES (
      rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
      rule_name TEXT NOT NULL,
      rule_type TEXT NOT NULL CHECK(rule_type IN ('percentage', 'fixed', 'points_redemption', 'tier_based')),
      min_purchase_amount DECIMAL(10,2),
      min_points_required INTEGER,
      discount_value DECIMAL(10,2),
      points_to_currency_rate DECIMAL(5,4) DEFAULT 0.01, -- 1 point = $0.01
      applicable_tiers TEXT, -- JSON array of tier_ids
      start_date DATETIME,
      end_date DATETIME,
      is_active BOOLEAN DEFAULT 1,
      priority INTEGER DEFAULT 0,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  );

  -- 10. APPLIED_DISCOUNTS table
  CREATE TABLE APPLIED_DISCOUNTS (
      discount_id INTEGER PRIMARY KEY AUTOINCREMENT,
      order_id TEXT NOT NULL,
      rule_id INTEGER,
      discount_type TEXT NOT NULL,
      discount_amount DECIMAL(10,2) NOT NULL,
      points_used INTEGER DEFAULT 0,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (order_id) REFERENCES ORDERS(order_id),
      FOREIGN KEY (rule_id) REFERENCES DISCOUNT_RULES(rule_id)
  );

  -- 11. TIER_BENEFITS table
  CREATE TABLE TIER_BENEFITS (
      benefit_id INTEGER PRIMARY KEY AUTOINCREMENT,
      tier_id INTEGER NOT NULL,
      benefit_type TEXT NOT NULL,
      benefit_value TEXT NOT NULL,
      description TEXT,
      is_active BOOLEAN DEFAULT 1,
      FOREIGN KEY (tier_id) REFERENCES LOYALTY_TIERS(tier_id)
  );

  -- 12. TIER_HISTORY table
  CREATE TABLE TIER_HISTORY (
      history_id INTEGER PRIMARY KEY AUTOINCREMENT,
      customer_id TEXT NOT NULL,
      old_tier_id INTEGER,
      new_tier_id INTEGER NOT NULL,
      change_reason TEXT,
      changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (customer_id) REFERENCES CUSTOMERS(customer_id),
      FOREIGN KEY (old_tier_id) REFERENCES LOYALTY_TIERS(tier_id),
      FOREIGN KEY (new_tier_id) REFERENCES LOYALTY_TIERS(tier_id)
  );

  -- Create indexes for better performance
  CREATE INDEX idx_customers_email ON CUSTOMERS(email);
  CREATE INDEX idx_customers_tier ON CUSTOMERS(current_tier_id);
  CREATE INDEX idx_points_customer ON POINTS_TRANSACTIONS(customer_id, created_at);
  CREATE INDEX idx_orders_customer ON ORDERS(customer_id, order_date);
  CREATE INDEX idx_order_items_order ON ORDER_ITEMS(order_id);
  CREATE INDEX idx_products_category ON PRODUCTS(category);
  CREATE INDEX idx_discount_rules_active ON DISCOUNT_RULES(is_active, start_date, end_date);
