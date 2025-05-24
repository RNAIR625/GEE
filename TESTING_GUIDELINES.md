# Testing Guidelines and Conceptual Cases

This document outlines suggested test cases for various components of the application, particularly focusing on the Rules functionality.

## JavaScript Unit Tests (`static/js/rules.js`)

A JavaScript testing framework (e.g., Jest, Mocha, Jasmine) should be set up to run these tests. Mocking for DOM elements and `fetch` calls will be necessary.

### 1. `editRuleLine(lineId, isCondition)`
   - **Objective:** Verify that the rule line editing modal is populated correctly.
   - **Mock Data:**
     - `currentRuleLines`: Array with sample condition and action lines, including parameters.
     - `allFunctions`: Array of sample function definitions.
     - `classFields`: Array of sample field definitions for the current class.
   - **Test Cases:**
     - Call `editRuleLine` with a valid `lineId` for a condition.
       - **Assert:** `ruleLineModal` is shown, `ruleLineModalTitle` is correct, `functionSelect` has the correct function ID selected, `sequenceNum` is correct, `handleFunctionSelection` is called with the correct parameters.
     - Call `editRuleLine` with a valid `lineId` for an action.
       - **Assert:** Similar checks as above, ensuring `isCondition` is handled.
     - Call `editRuleLine` for a line that has parameters.
       - **Assert:** `handleFunctionSelection` should be called with parameters that lead to pre-filling of field selectors or literal inputs.

### 2. `handleFunctionSelection(existingParams = null)`
   - **Objective:** Ensure parameter input fields are correctly generated and pre-filled based on the selected function and existing parameters.
   - **Mock Data:**
     - `allFunctions`: Array of function definitions (some with params, some without).
     - `classFields`: Array of field definitions.
     - `existingParams`:
       - `null` (for new lines).
       - Array of parameter objects (some field-based, some literal-based).
   - **Setup:**
     - Mock `document.getElementById('functionSelect').value` to return a selected function ID.
     - Mock `document.getElementById('parametersContainer')`.
   - **Test Cases:**
     - Select a function with 0 parameters.
       - **Assert:** `parametersContainer` shows "This function has no parameters."
     - Select a function with N parameters, `existingParams` is `null`.
       - **Assert:** N parameter groups are created. Each group defaults to "Field" and has field/literal inputs hidden/shown appropriately.
     - Select a function with N parameters, `existingParams` provided:
       - Parameter 1 uses a field.
         - **Assert:** Parameter 1 group shows "Field" selected, field dropdown visible and correct field selected, literal input hidden.
       - Parameter 2 uses a literal value.
         - **Assert:** Parameter 2 group shows "Literal Value" selected, literal input visible and correct value entered, field dropdown hidden.
     - Ensure that the `GF_NAME` for fields and `literalValue` are correctly displayed in the generated HTML.

### 3. `generateCodeFromLines()`
   - **Objective:** Verify that JavaScript code is correctly generated from `currentRuleLines`.
   - **Mock Data:**
     - `currentRuleLines`:
       - Empty conditions and actions.
       - Conditions only.
       - Actions only.
       - Both conditions and actions, with various parameter types (fields, string literals, numeric literals).
   - **Setup:**
     - Mock `window.conditionEditor.setValue` and `window.actionEditor.setValue`.
   - **Test Cases:**
     - `currentRuleLines` is empty.
       - **Assert:** Both editors are set to `""`.
     - `currentRuleLines` has one condition: `funcA(fields.field1, 'literalString', 123)`.
       - **Assert:** `conditionEditor.setValue` is called with `funcA(fields.field1, 'literalString', 123);`. `actionEditor.setValue` is called with `""`.
     - `currentRuleLines` has one action: `funcB(fields.field2)`.
       - **Assert:** `actionEditor.setValue` is called with `funcB(fields.field2);`. `conditionEditor.setValue` is called with `""`.
     - Test correct handling of multiple lines, sequence numbers (though `generateCodeFromLines` sorts them), and different parameter types.
     - Test escaping of single quotes in string literals.

### 4. `toggleRuleCreationMode()`
   - **Objective:** Verify the confirmation dialog logic when switching from Code Editor to Structured mode with changes.
   - **Setup:**
     - Mock `window.conditionEditor.getValue()`, `window.actionEditor.getValue()`.
     - Mock `confirm()`.
     - Set `document.getElementById('modeCodeEditor').checked`.
   - **Test Cases:**
     - Switch from Code to Structured. No changes in editors.
       - **Assert:** `confirm()` is NOT called. Mode switches.
     - Switch from Code to Structured. Changes in `conditionEditor`. `confirm()` returns `true`.
       - **Assert:** `confirm()` IS called. Mode switches. `renderRuleLines()` is called.
     - Switch from Code to Structured. Changes in `actionEditor`. `confirm()` returns `false`.
       - **Assert:** `confirm()` IS called. Mode does NOT switch (`modeCodeEditor` remains checked). UI visibility remains for Code Editor.

## Python Unit Tests (`routes/rules.py`)

A Python testing framework (e.g., PyTest, Unittest) should be used. Mocking for `db_helpers` (`query_db`, `modify_db`) and Flask's `request` and `jsonify` will be necessary.

### 1. `/rules/add_rule_line` (Endpoint: `add_rule_line`)
   - **Objective:** Test adding new rule lines (conditions/actions) to a rule.
   - **Mock Data:**
     - `request.json`: Payload for adding a rule line (with/without parameters).
   - **Setup:**
     - Mock `modify_db` to simulate database inserts and return a `lastrowid`.
   - **Test Cases:**
     - Valid request to add a condition line with field parameter.
       - **Assert:** `modify_db` called for `GEE_RULE_LINES` and `GEE_RULE_LINE_PARAMS`. Correct SQL and parameters. Returns 200 with success and ID.
     - Valid request to add an action line with literal parameter.
       - **Assert:** Similar to above.
     - Request missing `ruleId` or `functionId`.
       - **Assert:** Returns 400 with error message. `modify_db` not called.

### 2. `/rules/update_rule_line` (Endpoint: `update_rule_line`)
   - **Objective:** Test updating existing rule lines.
   - **Mock Data:**
     - `request.json`: Payload for updating a rule line.
   - **Setup:**
     - Mock `modify_db` to simulate database updates/deletes/inserts.
   - **Test Cases:**
     - Valid request to update a line (e.g., change function, change params).
       - **Assert:** `modify_db` called to update `GEE_RULE_LINES`, delete old `GEE_RULE_LINE_PARAMS`, insert new `GEE_RULE_LINE_PARAMS`. Returns 200 with success.
     - Request missing `lineId` or `functionId`.
       - **Assert:** Returns 400 with error message.

### 3. `/rules/generate_code/<int:rule_id>` (Endpoint: `generate_code`)
   - **Objective:** Test server-side generation of condition and action code from stored rule lines.
   - **Mock Data:**
     - `rule_id` (parameter).
   - **Setup:**
     - Mock `query_db` to return:
       - No lines for the rule.
       - Only condition lines.
       - Only action lines.
       - Both condition and action lines, with field and literal parameters.
   - **Test Cases:**
     - Rule has no lines.
       - **Assert:** Returns 200 with `{"conditionCode": "", "actionCode": ""}`.
     - Rule has one condition: `funcA(fields.field1, 'literal')`.
       - **Assert:** Returns 200 with `{"conditionCode": "funcA(fields.field1, 'literal');", "actionCode": ""}`.
     - Rule has one action with a numeric literal.
       - **Assert:** Correctly formats numeric literal without quotes.
     - Rule has multiple lines for conditions and actions.
       - **Assert:** Code blocks are correctly formed with newlines.
     - Test correct handling of parameter types (Field vs. Literal) and data types (string vs. numeric for literals).
