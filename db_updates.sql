-- Create the additional tables needed for rule groups

-- Table for rule definitions (if not already exists)
CREATE TABLE IF NOT EXISTS GRG_RULES (
    RULE_ID INTEGER PRIMARY KEY,
    RULE_NAME TEXT NOT NULL,
    RULE_TYPE TEXT,
    DESCRIPTION TEXT,
    CREATE_DATE DATETIME DEFAULT CURRENT_TIMESTAMP,
    UPDATE_DATE DATETIME
);

-- Table for rule groups
CREATE TABLE IF NOT EXISTS GRG_RULE_GROUPS (
    GRG_ID INTEGER PRIMARY KEY,
    GROUP_NAME TEXT NOT NULL,
    COND_TYPE TEXT,
    GRG_ID_PARENT INTEGER,
    DESCRIPTION TEXT,
    COND_GRG_ID_START INTEGER,
    ACT_GRG_ID_START INTEGER,
    CREATE_DATE DATETIME DEFAULT CURRENT_TIMESTAMP,
    UPDATE_DATE DATETIME,
    FOREIGN KEY (GRG_ID_PARENT) REFERENCES GRG_RULE_GROUPS(GRG_ID)
);

-- Table for mapping rules to rule groups
CREATE TABLE IF NOT EXISTS GRG_RULE_GROUP_RULES (
    MAPPING_ID INTEGER PRIMARY KEY,
    GRG_ID INTEGER,
    RULE_ID INTEGER,
    SEQUENCE INTEGER,
    CREATE_DATE DATETIME DEFAULT CURRENT_TIMESTAMP,
    UPDATE_DATE DATETIME,
    FOREIGN KEY (GRG_ID) REFERENCES GRG_RULE_GROUPS(GRG_ID),
    FOREIGN KEY (RULE_ID) REFERENCES GRG_RULES(RULE_ID)
);

-- Insert some sample data for testing
INSERT INTO GRG_RULES (RULE_ID, RULE_NAME, RULE_TYPE, DESCRIPTION)
VALUES 
    (1, 'Validate Email Format', 'VALIDATION', 'Validates that an email address is properly formatted'),
    (2, 'Check Required Fields', 'VALIDATION', 'Checks that all required fields have values'),
    (3, 'Calculate Total Amount', 'CALCULATION', 'Calculates the total amount including taxes and fees'),
    (4, 'Format Phone Number', 'FORMATTING', 'Formats phone numbers to a standardized format'),
    (5, 'Verify Address', 'VALIDATION', 'Verifies that an address is valid and properly formatted');