  3. Test Insert Statements

  -- Insert Loyalty Tiers
  INSERT INTO LOYALTY_TIERS (tier_name, min_points, max_points, discount_percentage, points_multiplier, free_shipping, priority_support, color_code, icon_url) VALUES
  ('Bronze', 0, 999, 0.00, 1.0, 0, 0, '#CD7F32', '/icons/bronze.png'),
  ('Silver', 1000, 4999, 5.00, 1.5, 0, 0, '#C0C0C0', '/icons/silver.png'),
  ('Gold', 5000, 9999, 10.00, 2.0, 1, 0, '#FFD700', '/icons/gold.png'),
  ('Platinum', 10000, NULL, 15.00, 3.0, 1, 1, '#E5E4E2', '/icons/platinum.png');

  -- Insert Products
  INSERT INTO PRODUCTS (product_id, product_name, category, brand, price, points_per_dollar, bonus_points) VALUES
  ('PROD001', 'Wireless Headphones', 'Electronics', 'TechBrand', 149.99, 2, 100),
  ('PROD002', 'Smart Watch', 'Electronics', 'TechBrand', 299.99, 2, 200),
  ('PROD003', 'Running Shoes', 'Sports', 'SportBrand', 89.99, 1, 50),
  ('PROD004', 'Yoga Mat', 'Sports', 'FitnessBrand', 29.99, 1, 0),
  ('PROD005', 'Coffee Maker', 'Appliances', 'HomeBrand', 79.99, 1, 75),
  ('PROD006', 'Backpack', 'Accessories', 'TravelBrand', 49.99, 1, 25),
  ('PROD007', 'Sunglasses', 'Accessories', 'FashionBrand', 129.99, 2, 0),
  ('PROD008', 'Bluetooth Speaker', 'Electronics', 'TechBrand', 69.99, 2, 50);

  -- Insert Customers
  INSERT INTO CUSTOMERS (customer_id, email, first_name, last_name, phone, date_of_birth, current_tier_id, lifetime_points) VALUES
  ('CUST001', 'john.doe@email.com', 'John', 'Doe', '+1234567890', '1985-03-15', 2, 2500),
  ('CUST002', 'jane.smith@email.com', 'Jane', 'Smith', '+1234567891', '1990-07-22', 3, 6500),
  ('CUST003', 'bob.johnson@email.com', 'Bob', 'Johnson', '+1234567892', '1978-11-30', 1, 750),
  ('CUST004', 'alice.williams@email.com', 'Alice', 'Williams', '+1234567893', '1995-05-18', 4, 12000),
  ('CUST005', 'charlie.brown@email.com', 'Charlie', 'Brown', '+1234567894', '1982-09-10', 2, 3200);

  -- Insert Customer Points
  INSERT INTO CUSTOMER_POINTS (customer_id, current_points, pending_points, expired_points) VALUES
  ('CUST001', 1500, 200, 100),
  ('CUST002', 3200, 0, 500),
  ('CUST003', 750, 50, 0),
  ('CUST004', 5500, 300, 1000),
  ('CUST005', 2100, 0, 200);

  -- Insert Customer Preferences
  INSERT INTO CUSTOMER_PREFERENCES (customer_id, email_notifications, sms_notifications, preferred_categories, preferred_brands, language, currency) VALUES
  ('CUST001', 1, 1, '["Electronics", "Sports"]', '["TechBrand", "SportBrand"]', 'en', 'USD'),
  ('CUST002', 1, 0, '["Electronics", "Appliances"]', '["TechBrand", "HomeBrand"]', 'en', 'USD'),
  ('CUST003', 1, 1, '["Sports", "Accessories"]', '["SportBrand", "TravelBrand"]', 'en', 'USD'),
  ('CUST004', 1, 1, '["Electronics", "Accessories"]', '["TechBrand", "FashionBrand"]', 'en', 'USD'),
  ('CUST005', 0, 0, '["Appliances", "Sports"]', '["HomeBrand", "FitnessBrand"]', 'en', 'USD');

  -- Insert Orders
  INSERT INTO ORDERS (order_id, customer_id, subtotal, discount_amount, tax_amount, shipping_amount, total_amount, points_earned, points_redeemed, status, payment_status) VALUES
  ('ORD001', 'CUST001', 229.98, 11.50, 20.70, 0.00, 239.18, 460, 0, 'delivered', 'paid'),
  ('ORD002', 'CUST002', 369.98, 37.00, 33.30, 0.00, 366.28, 740, 500, 'delivered', 'paid'),
  ('ORD003', 'CUST003', 119.98, 0.00, 10.80, 5.99, 136.77, 120, 0, 'shipped', 'paid'),
  ('ORD004', 'CUST004', 449.97, 67.50, 40.50, 0.00, 422.97, 1350, 1000, 'processing', 'paid'),
  ('ORD005', 'CUST001', 79.99, 0.00, 7.20, 5.99, 93.18, 80, 0, 'pending', 'pending');

  -- Insert Order Items
  INSERT INTO ORDER_ITEMS (order_id, product_id, product_name, quantity, unit_price, discount_amount, total_price, points_earned) VALUES
  ('ORD001', 'PROD001', 'Wireless Headphones', 1, 149.99, 7.50, 142.49, 300),
  ('ORD001', 'PROD005', 'Coffee Maker', 1, 79.99, 4.00, 75.99, 160),
  ('ORD002', 'PROD002', 'Smart Watch', 1, 299.99, 30.00, 269.99, 600),
  ('ORD002', 'PROD008', 'Bluetooth Speaker', 1, 69.99, 7.00, 62.99, 140),
  ('ORD003', 'PROD003', 'Running Shoes', 1, 89.99, 0.00, 89.99, 90),
  ('ORD003', 'PROD004', 'Yoga Mat', 1, 29.99, 0.00, 29.99, 30),
  ('ORD004', 'PROD002', 'Smart Watch', 1, 299.99, 45.00, 254.99, 900),
  ('ORD004', 'PROD001', 'Wireless Headphones', 1, 149.99, 22.50, 127.49, 450),
  ('ORD005', 'PROD005', 'Coffee Maker', 1, 79.99, 0.00, 79.99, 80);

  -- Insert Points Transactions
  INSERT INTO POINTS_TRANSACTIONS (customer_id, transaction_type, points, balance_after, reference_type, reference_id, description) VALUES
  ('CUST001', 'earned', 460, 1960, 'order', 'ORD001', 'Points earned from order ORD001'),
  ('CUST002', 'earned', 740, 3440, 'order', 'ORD002', 'Points earned from order ORD002'),
  ('CUST002', 'redeemed', -500, 2940, 'order', 'ORD002', 'Points redeemed for discount on order ORD002'),
  ('CUST003', 'earned', 120, 870, 'order', 'ORD003', 'Points earned from order ORD003'),
  ('CUST004', 'earned', 1350, 6850, 'order', 'ORD004', 'Points earned from order ORD004'),
  ('CUST004', 'redeemed', -1000, 5850, 'order', 'ORD004', 'Points redeemed for discount on order ORD004'),
  ('CUST001', 'bonus', 500, 2000, 'promotion', 'PROMO001', 'Birthday bonus points'),
  ('CUST002', 'expired', -500, 3200, 'expiration', NULL, 'Points expired after 12 months');

  -- Insert Discount Rules
  INSERT INTO DISCOUNT_RULES (rule_name, rule_type, min_purchase_amount, min_points_required, discount_value, points_to_currency_rate, applicable_tiers, start_date, end_date, is_active, priority) VALUES
  ('5% Off for Silver', 'tier_based', 0, 0, 5.00, 0, '[2]', '2024-01-01', '2024-12-31', 1, 1),
  ('10% Off for Gold', 'tier_based', 0, 0, 10.00, 0, '[3]', '2024-01-01', '2024-12-31', 1, 2),
  ('15% Off for Platinum', 'tier_based', 0, 0, 15.00, 0, '[4]', '2024-01-01', '2024-12-31', 1, 3),
  ('Points Redemption', 'points_redemption', 0, 100, 0, 0.01, '[1,2,3,4]', '2024-01-01', '2024-12-31', 1, 0),
  ('$10 Off $100+', 'fixed', 100.00, 0, 10.00, 0, '[1,2,3,4]', '2024-01-01', '2024-12-31', 1, 4);

  -- Insert Applied Discounts
  INSERT INTO APPLIED_DISCOUNTS (order_id, rule_id, discount_type, discount_amount, points_used) VALUES
  ('ORD001', 1, 'tier_based', 11.50, 0),
  ('ORD002', 2, 'tier_based', 37.00, 0),
  ('ORD002', 4, 'points_redemption', 5.00, 500),
  ('ORD004', 3, 'tier_based', 67.50, 0),
  ('ORD004', 4, 'points_redemption', 10.00, 1000);

  -- Insert Tier Benefits
  INSERT INTO TIER_BENEFITS (tier_id, benefit_type, benefit_value, description) VALUES
  (1, 'points_multiplier', '1x', 'Earn 1 point per dollar spent'),
  (2, 'points_multiplier', '1.5x', 'Earn 1.5 points per dollar spent'),
  (2, 'discount', '5%', '5% discount on all purchases'),
  (3, 'points_multiplier', '2x', 'Earn 2 points per dollar spent'),
  (3, 'discount', '10%', '10% discount on all purchases'),
  (3, 'free_shipping', 'true', 'Free shipping on all orders'),
  (4, 'points_multiplier', '3x', 'Earn 3 points per dollar spent'),
  (4, 'discount', '15%', '15% discount on all purchases'),
  (4, 'free_shipping', 'true', 'Free shipping on all orders'),
  (4, 'priority_support', 'true', '24/7 priority customer support');

  -- Insert Tier History
  INSERT INTO TIER_HISTORY (customer_id, old_tier_id, new_tier_id, change_reason) VALUES
  ('CUST001', 1, 2, 'Reached 1000 lifetime points'),
  ('CUST002', 2, 3, 'Reached 5000 lifetime points'),
  ('CUST004', 3, 4, 'Reached 10000 lifetime points');

  -- Create views for common queries
  CREATE VIEW customer_summary AS
  SELECT
      c.customer_id,
      c.email,
      c.first_name || ' ' || c.last_name as full_name,
      lt.tier_name,
      cp.current_points,
      c.lifetime_points,
      c.status
  FROM CUSTOMERS c
  JOIN LOYALTY_TIERS lt ON c.current_tier_id = lt.tier_id
  JOIN CUSTOMER_POINTS cp ON c.customer_id = cp.customer_id;

  CREATE VIEW order_summary AS
  SELECT
      o.order_id,
      o.customer_id,
      c.email,
      c.first_name || ' ' || c.last_name as customer_name,
      o.order_date,
      o.total_amount,
      o.points_earned,
      o.points_redeemed,
      o.status,
      o.payment_status
  FROM ORDERS o
  JOIN CUSTOMERS c ON o.customer_id = c.customer_id;
