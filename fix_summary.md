# JSON Serialization Error Fix

## Problem
The application was throwing a JSON serialization error when accessing the rule groups page:

```
Error fetching rule groups: Object of type Row is not JSON serializable
127.0.0.1 - - [25/May/2025 23:19:41] "GET /rule_groups/get_rule_groups HTTP/1.1" 500 -
```

## Root Cause
The issue was in `routes/rule_groups.py` where SQLite Row objects were being directly passed to `jsonify()` without converting them to dictionaries first. SQLite Row objects are not JSON serializable by default.

## Solution
Fixed the `get_rule_groups()` and `get_assigned_rules()` functions in `routes/rule_groups.py`:

### Before (Lines 22-26):
```python
# Handle case when no rule groups exist yet
if rule_groups is None:
    return jsonify([])
    
return jsonify(rule_groups)  # ❌ Row objects not serializable
```

### After (Lines 22-28):
```python
# Handle case when no rule groups exist yet
if rule_groups is None:
    return jsonify([])
    
# Convert Row objects to dictionaries for JSON serialization
rule_groups_list = [dict(row) for row in rule_groups]
return jsonify(rule_groups_list)  # ✅ Dictionaries are serializable
```

### Similar fix for `get_assigned_rules()` function (Lines 199-205):
```python
# Handle case when no rules are assigned
if rules is None:
    return jsonify([])
    
# Convert Row objects to dictionaries for JSON serialization
rules_list = [dict(row) for row in rules]
return jsonify(rules_list)
```

## Verification
After applying the fix:
- The rule groups page loads successfully (HTTP 200)
- No more JSON serialization errors
- All functionality works as expected

## Related Notes
Other route files (`classes.py`, `fields.py`, `env_config.py`, `functions.py`) were already handling Row conversion correctly using `[dict(row) for row in rows]` pattern.

## Status: ✅ FIXED
The JSON serialization error has been resolved and the rule groups functionality is now working properly.