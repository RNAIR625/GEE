// Global variables for storing data
let allRules = [];
let allFunctions = [];
let allClasses = [];
let classFields = [];
let currentRuleLines = { conditions: [], actions: [] };
let currentEditingLine = null;
let ruleLineModal = null;

// Initialize the page when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap modals
    const ruleModal = document.getElementById('ruleModal');
    if (ruleModal) {
        new bootstrap.Modal(ruleModal);
    }
    
    const ruleLineModalElement = document.getElementById('ruleLineModal');
    if (ruleLineModalElement) {
        ruleLineModal = new bootstrap.Modal(ruleLineModalElement);
    }
    
    const functionSelectorModal = document.getElementById('functionSelectorModal');
    if (functionSelectorModal) {
        new bootstrap.Modal(functionSelectorModal);
    }
    
    const fieldSelectorModal = document.getElementById('fieldSelectorModal');
    if (fieldSelectorModal) {
        new bootstrap.Modal(fieldSelectorModal);
    }
    
    const deleteModal = document.getElementById('deleteModal');
    if (deleteModal) {
        new bootstrap.Modal(deleteModal);
    }
    
    // Initialize CodeMirror editors if elements exist
    if (document.getElementById('conditionCode')) {
        window.conditionEditor = CodeMirror.fromTextArea(document.getElementById('conditionCode'), {
            mode: 'javascript',
            lineNumbers: true,
            matchBrackets: true,
            autoCloseBrackets: true,
            extraKeys: {"Ctrl-Space": "autocomplete"},
            theme: 'default'
        });
    }
    
    if (document.getElementById('actionCode')) {
        window.actionEditor = CodeMirror.fromTextArea(document.getElementById('actionCode'), {
            mode: 'javascript',
            lineNumbers: true,
            matchBrackets: true,
            autoCloseBrackets: true,
            extraKeys: {"Ctrl-Space": "autocomplete"},
            theme: 'default'
        });
    }
    
    // Handle rule creation mode toggle
    const ruleCreationModeRadios = document.querySelectorAll('input[name="ruleCreationMode"]');
    ruleCreationModeRadios.forEach(radio => {
        radio.addEventListener('change', toggleRuleCreationMode);
    });
    
    // Set up event listeners for buttons
    const saveRuleBtn = document.getElementById('saveRuleBtn');
    if (saveRuleBtn) {
        saveRuleBtn.addEventListener('click', saveRule);
    }
    
    const saveLineBtn = document.getElementById('saveLineBtn');
    if (saveLineBtn) {
        saveLineBtn.addEventListener('click', saveRuleLine);
    }
    
    const selectFunctionBtn = document.getElementById('selectFunctionBtn');
    if (selectFunctionBtn) {
        selectFunctionBtn.addEventListener('click', insertSelectedFunction);
    }
    
    const selectFieldBtn = document.getElementById('selectFieldBtn');
    if (selectFieldBtn) {
        selectFieldBtn.addEventListener('click', insertSelectedField);
    }
    
    // Set up event listeners for code editor buttons
    const insertConditionFunctionBtn = document.getElementById('insertConditionFunctionBtn');
    if (insertConditionFunctionBtn) {
        insertConditionFunctionBtn.addEventListener('click', () => openFunctionSelector('condition'));
    }
    
    const insertConditionFieldBtn = document.getElementById('insertConditionFieldBtn');
    if (insertConditionFieldBtn) {
        insertConditionFieldBtn.addEventListener('click', () => openFieldSelector('condition'));
    }
    
    const insertActionFunctionBtn = document.getElementById('insertActionFunctionBtn');
    if (insertActionFunctionBtn) {
        insertActionFunctionBtn.addEventListener('click', () => openFunctionSelector('action'));
    }
    
    const insertActionFieldBtn = document.getElementById('insertActionFieldBtn');
    if (insertActionFieldBtn) {
        insertActionFieldBtn.addEventListener('click', () => openFieldSelector('action'));
    }
    
    const testConditionBtn = document.getElementById('testConditionBtn');
    if (testConditionBtn) {
        testConditionBtn.addEventListener('click', () => testCode('condition'));
    }
    
    const testActionBtn = document.getElementById('testActionBtn');
    if (testActionBtn) {
        testActionBtn.addEventListener('click', () => testCode('action'));
    }
    
    // Function select change handler
    const functionSelect = document.getElementById('functionSelect');
    if (functionSelect) {
        functionSelect.addEventListener('change', () => handleFunctionSelection());
    }
    
    // Load initial data
    loadRules();
    loadClasses();
    loadFunctions();
});

// Load all rules
function loadRules() {
    fetch('/rules/get_rules')
        .then(response => response.json())
        .then(data => {
            allRules = data;
            renderRules(data);
        })
        .catch(error => {
            console.error('Error loading rules:', error);
            showToast('Error', 'Failed to load rules', 'error');
        });
}

// Load all field classes
function loadClasses() {
    fetch('/classes/get_classes')
        .then(response => response.json())
        .then(data => {
            allClasses = data;
            
            // Populate class dropdowns
            populateClassDropdowns(data);
        })
        .catch(error => {
            console.error('Error loading classes:', error);
            showToast('Error', 'Failed to load field classes', 'error');
        });
}

// Populate class dropdowns
function populateClassDropdowns(classes) {
    // Populate class filter dropdown
    const filterClassDropdown = document.getElementById('filterClass');
    if (filterClassDropdown) {
        // Clear existing options except the first one
        while (filterClassDropdown.options.length > 1) {
            filterClassDropdown.remove(1);
        }
        
        // Add option for "All Classes"
        const allClassOption = document.createElement('option');
        allClassOption.value = "";
        allClassOption.textContent = "All Classes";
        filterClassDropdown.appendChild(allClassOption);
        
        // Add options for each class
        classes.forEach(cls => {
            const option = document.createElement('option');
            option.value = cls.GFC_ID;
            option.textContent = cls.GFC_NAME;
            filterClassDropdown.appendChild(option);
        });
    }
    
    // Populate rule class dropdown
    const ruleClassDropdown = document.getElementById('ruleClass');
    if (ruleClassDropdown) {
        // Clear existing options except the first one
        while (ruleClassDropdown.options.length > 1) {
            ruleClassDropdown.remove(1);
        }
        
        // Add options for each class
        classes.forEach(cls => {
            const option = document.createElement('option');
            option.value = cls.GFC_ID;
            option.textContent = cls.GFC_NAME;
            ruleClassDropdown.appendChild(option);
        });
    }
}

// Load fields for a specific class
function loadFieldsForClass(classId) {
    if (!classId) {
        classFields = [];
        return Promise.resolve([]);
    }
    
    return fetch(`/fields/get_fields_by_class/${classId}`)
        .then(response => response.json())
        .then(data => {
            classFields = data;
            return data;
        })
        .catch(error => {
            console.error('Error loading fields:', error);
            showToast('Error', 'Failed to load fields for the selected class', 'error');
            return [];
        });
}

// Load all functions
function loadFunctions() {
    fetch('/functions/get_functions')
        .then(response => response.json())
        .then(data => {
            allFunctions = data;
            
            // Populate function dropdowns
            populateFunctionDropdowns(data);
        })
        .catch(error => {
            console.error('Error loading functions:', error);
            showToast('Error', 'Failed to load functions', 'error');
        });
}

// Populate function dropdowns
function populateFunctionDropdowns(functions) {
    const functionSelect = document.getElementById('functionSelect');
    if (functionSelect) {
        // Clear existing options except the first one
        while (functionSelect.options.length > 1) {
            functionSelect.remove(1);
        }
        
        // Add options for each function
        functions.forEach(func => {
            const option = document.createElement('option');
            option.value = func.GBF_ID;
            option.textContent = func.FUNC_NAME;
            functionSelect.appendChild(option);
        });
    }
    
    // Populate functions list in function selector modal
    const functionsList = document.getElementById('functionsList');
    if (functionsList) {
        functionsList.innerHTML = '';
        
        functions.forEach(func => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${func.FUNC_NAME}</td>
                <td>${func.PARAM_COUNT} params</td>
                <td class="text-end">
                    <button class="btn btn-sm btn-primary" onclick="selectFunction('${func.GBF_ID}', '${func.FUNC_NAME}')">
                        <i class="fas fa-check me-1"></i>Select
                    </button>
                </td>
            `;
            functionsList.appendChild(row);
        });
    }
}

// Render rules to the table
function renderRules(rules) {
    const ruleList = document.getElementById('ruleList');
    const noRulesMessage = document.getElementById('noRulesMessage');
    
    if (!ruleList) return;
    
    // Clear the current content
    ruleList.innerHTML = '';
    
    if (!rules || rules.length === 0) {
        if (noRulesMessage) {
            noRulesMessage.style.display = 'block';
        }
        return;
    }
    
    // Hide the no rules message
    if (noRulesMessage) {
        noRulesMessage.style.display = 'none';
    }
    
    // Render each rule
    rules.forEach(rule => {
        const row = document.createElement('tr');
        
        // Find class name if class ID exists
        let className = 'None';
        if (rule.GFC_ID && allClasses.length > 0) {
            const cls = allClasses.find(c => c.GFC_ID == rule.GFC_ID);
            if (cls) {
                className = cls.GFC_NAME;
            }
        }
        
        // Format date
        const updatedDate = new Date(rule.UPDATE_DATE).toLocaleString();
        
        row.innerHTML = `
            <td>${rule.RULE_NAME}</td>
            <td>${className}</td>
            <td><span class="badge rule-type-${rule.RULE_TYPE?.toLowerCase()}">${rule.RULE_TYPE || 'Standard'}</span></td>
            <td>${rule.DESCRIPTION || ''}</td>
            <td>${updatedDate}</td>
            <td class="text-end">
                <button class="btn btn-sm btn-warning me-1" onclick="editRule(${rule.RULE_ID})">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-sm btn-danger" onclick="confirmDeleteRule(${rule.RULE_ID})">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        `;
        
        ruleList.appendChild(row);
    });
    
    // Update rule count
    const ruleCount = document.getElementById('ruleCount');
    if (ruleCount) {
        ruleCount.textContent = `${rules.length} rules`;
    }
}

// Open new rule modal
function openNewRuleModal() {
    // Reset the form
    document.getElementById('ruleForm').reset();
    document.getElementById('ruleId').value = '';
    
    // Set default values
    document.getElementById('modalTitle').textContent = 'Add New Rule';
    document.getElementById('ruleType').value = 'Standard';
    
    // Reset rule lines
    currentRuleLines = { conditions: [], actions: [] };
    
    // Reset CodeMirror editors if they exist
    if (window.conditionEditor) {
        window.conditionEditor.setValue('');
    }
    if (window.actionEditor) {
        window.actionEditor.setValue('');
    }
    
    // Default to code editor mode
    document.getElementById('modeCodeEditor').checked = true;
    document.getElementById('codeEditorMode').classList.remove('d-none');
    document.getElementById('structuredMode').classList.add('d-none');
    
    // Show the modal
    const modal = bootstrap.Modal.getInstance(document.getElementById('ruleModal'));
    modal.show();
}

// Edit an existing rule
function editRule(ruleId) {
    // Find the rule
    const rule = allRules.find(r => r.RULE_ID === ruleId);
    
    if (!rule) {
        showToast('Error', 'Rule not found', 'error');
        return;
    }
    
    // Reset the form
    document.getElementById('ruleForm').reset();
    
    // Set values
    document.getElementById('ruleId').value = rule.RULE_ID;
    document.getElementById('ruleName').value = rule.RULE_NAME || '';
    document.getElementById('ruleClass').value = rule.GFC_ID || '';
    document.getElementById('ruleType').value = rule.RULE_TYPE || 'Standard';
    document.getElementById('ruleDescription').value = rule.DESCRIPTION || '';
    
    // Load class fields if class is selected
    if (rule.GFC_ID) {
        loadFieldsForClass(rule.GFC_ID);
    }
    
    // Set CodeMirror editors if they exist
    if (window.conditionEditor) {
        window.conditionEditor.setValue(rule.CONDITION_CODE || '');
    }
    if (window.actionEditor) {
        window.actionEditor.setValue(rule.ACTION_CODE || '');
    }
    
    // Set modal title
    document.getElementById('modalTitle').textContent = 'Edit Rule';
    
    // Default to code editor mode
    document.getElementById('modeCodeEditor').checked = true;
    document.getElementById('codeEditorMode').classList.remove('d-none');
    document.getElementById('structuredMode').classList.add('d-none');
    
    // Load rule lines
    loadRuleLines(rule.RULE_ID);
    
    // Show the modal
    const modal = bootstrap.Modal.getInstance(document.getElementById('ruleModal'));
    modal.show();
}

// Save rule
function saveRule() {
    const ruleId = document.getElementById('ruleId').value;
    const ruleName = document.getElementById('ruleName').value;
    const classId = document.getElementById('ruleClass').value;
    const ruleType = document.getElementById('ruleType').value;
    const description = document.getElementById('ruleDescription').value;
    
    // Validate required fields
    if (!ruleName) {
        showToast('Error', 'Rule name is required', 'error');
        return;
    }
    
    if (!classId) {
        showToast('Error', 'Please select a class', 'error');
        return;
    }
    
    // Get condition and action code based on mode
    let conditionCode = '';
    let actionCode = '';
    
    if (document.getElementById('modeCodeEditor').checked) {
        // Code editor mode
        conditionCode = window.conditionEditor.getValue();
        actionCode = window.actionEditor.getValue();
    } else {
        // Structured mode - generate code from lines
        generateCodeFromLines();
        conditionCode = window.conditionEditor.getValue();
        actionCode = window.actionEditor.getValue();
    }
    
    // Prepare data
    const data = {
        ruleName: ruleName,
        classId: classId,
        ruleType: ruleType,
        description: description,
        conditionCode: conditionCode,
        actionCode: actionCode
    };
    
    let url = '/rules/add_rule';
    let method = 'POST';
    
    if (ruleId) {
        // Update existing rule
        url = '/rules/update_rule';
        method = 'PUT';
        data.ruleId = ruleId;
    }
    
    // Send request
    fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            // If new rule was created, now save rule lines
            if (!ruleId && result.id) {
                if (currentRuleLines.conditions.length > 0 || currentRuleLines.actions.length > 0) {
                    return saveRuleLinesToServer(result.id).then(() => result);
                }
            }
            return result;
        } else {
            throw new Error(result.message || 'Unknown error');
        }
    })
    .then(result => {
        showToast('Success', result.message);
        
        // Hide the modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('ruleModal'));
        modal.hide();
        
        // Reload rules
        loadRules();
    })
    .catch(error => {
        showToast('Error', error.message, 'error');
        console.error('Error saving rule:', error);
    });
}

// Confirm delete rule
function confirmDeleteRule(ruleId) {
    const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
    
    if (confirmDeleteBtn) {
        confirmDeleteBtn.onclick = function() {
            deleteRule(ruleId);
        };
    }
    
    // Show the modal
    const modal = bootstrap.Modal.getInstance(document.getElementById('deleteModal'));
    modal.show();
}

// Delete rule
function deleteRule(ruleId) {
    fetch(`/rules/delete_rule/${ruleId}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            showToast('Success', result.message);
            
            // Hide the modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('deleteModal'));
            modal.hide();
            
            // Reload rules
            loadRules();
        } else {
            throw new Error(result.message || 'Unknown error');
        }
    })
    .catch(error => {
        showToast('Error', error.message, 'error');
        console.error('Error deleting rule:', error);
    });
}

// Function Selector
function openFunctionSelector(target) {
    // Set the selected target (condition or action)
    if (target === 'condition') {
        document.getElementById('insertTargetCondition').checked = true;
    } else {
        document.getElementById('insertTargetAction').checked = true;
    }
    
    // Show the modal
    const modal = bootstrap.Modal.getInstance(document.getElementById('functionSelectorModal'));
    modal.show();
}

// Select function from function selector
function selectFunction(functionId, functionName) {
    document.getElementById('selectedFunctionId').value = functionId;
    document.getElementById('selectedFunctionName').value = functionName;
    
    // Enable the select button
    document.getElementById('selectFunctionBtn').disabled = false;
}

// Insert selected function
function insertSelectedFunction() {
    const functionId = document.getElementById('selectedFunctionId').value;
    const functionName = document.getElementById('selectedFunctionName').value;
    
    if (!functionId || !functionName) {
        showToast('Error', 'Please select a function', 'error');
        return;
    }
    
    // Determine target editor
    const isCondition = document.getElementById('insertTargetCondition').checked;
    const editor = isCondition ? window.conditionEditor : window.actionEditor;
    
    if (!editor) {
        showToast('Error', 'Editor not found', 'error');
        return;
    }
    
    // Find the function
    const func = allFunctions.find(f => f.GBF_ID == functionId);
    
    if (!func) {
        showToast('Error', 'Function not found', 'error');
        return;
    }
    
    // Generate function call template
    let params = [];
    for (let i = 0; i < func.PARAM_COUNT; i++) {
        params.push(`param${i+1}`);
    }
    
    const functionCall = `${functionName}(${params.join(', ')});\n`;
    
    // Insert at cursor position or at the end
    const cursor = editor.getCursor();
    editor.replaceRange(functionCall, cursor);
    
    // Hide the modal
    const modal = bootstrap.Modal.getInstance(document.getElementById('functionSelectorModal'));
    modal.hide();
}

// Field Selector
function openFieldSelector(target) {
    // Set the selected target (condition or action)
    if (target === 'condition') {
        document.getElementById('insertTargetCondition2').checked = true;
    } else {
        document.getElementById('insertTargetAction2').checked = true;
    }
    
    // Populate fields list
    const fieldsList = document.getElementById('fieldsList');
    if (fieldsList) {
        fieldsList.innerHTML = '';
        
        if (classFields.length === 0) {
            // No class selected or no fields available
            fieldsList.innerHTML = `
                <tr>
                    <td colspan="3" class="text-center text-muted py-3">
                        <i class="fas fa-info-circle me-2"></i>
                        No fields available. Please select a class for the rule.
                    </td>
                </tr>
            `;
        } else {
            classFields.forEach(field => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${field.GF_NAME}</td>
                    <td>${field.GF_TYPE}</td>
                    <td class="text-end">
                        <button class="btn btn-sm btn-primary" onclick="selectField('${field.GF_ID}', '${field.GF_NAME}')">
                            <i class="fas fa-check me-1"></i>Select
                        </button>
                    </td>
                `;
                fieldsList.appendChild(row);
            });
        }
    }
    
    // Show the modal
    const modal = bootstrap.Modal.getInstance(document.getElementById('fieldSelectorModal'));
    modal.show();
}

// Select field from field selector
function selectField(fieldId, fieldName) {
    document.getElementById('selectedFieldId').value = fieldId;
    document.getElementById('selectedFieldName').value = fieldName;
    
    // Enable the select button
    document.getElementById('selectFieldBtn').disabled = false;
}

// Insert selected field
function insertSelectedField() {
    const fieldName = document.getElementById('selectedFieldName').value;
    
    if (!fieldName) {
        showToast('Error', 'Please select a field', 'error');
        return;
    }
    
    // Determine target editor
    const isCondition = document.getElementById('insertTargetCondition2').checked;
    const editor = isCondition ? window.conditionEditor : window.actionEditor;
    
    if (!editor) {
        showToast('Error', 'Editor not found', 'error');
        return;
    }
    
    // Generate field reference
    const fieldReference = `fields.${fieldName}`;
    
    // Insert at cursor position
    const cursor = editor.getCursor();
    editor.replaceRange(fieldReference, cursor);
    
    // Hide the modal
    const modal = bootstrap.Modal.getInstance(document.getElementById('fieldSelectorModal'));
    modal.hide();
}

// Test code
function testCode(type) {
    let code = '';
    
    if (type === 'condition') {
        code = window.conditionEditor.getValue();
    } else {
        code = window.actionEditor.getValue();
    }
    
    if (!code.trim()) {
        showToast('Error', 'Please enter some code to test', 'error');
        return;
    }
    
    // Send code for testing
    fetch('/rules/test_code', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            code: code,
            type: type
        })
    })
    .then(response => response.json())
    .then(result => {
        displayTestResults(type, result);
    })
    .catch(error => {
        console.error('Error testing code:', error);
        displayTestResults(type, {
            success: false,
            error: error.message || 'An error occurred during testing'
        });
    });
}

// Display test results
function displayTestResults(type, result) {
    const resultsContainer = document.getElementById(`${type}Results`);
    const resultsContent = document.getElementById(`${type}ResultsContent`);
    
    if (!resultsContainer || !resultsContent) return;
    
    // Show the container
    resultsContainer.classList.remove('d-none');
    
    if (result.success) {
        resultsContainer.classList.remove('alert-danger');
        resultsContainer.classList.add('alert-success');
        resultsContent.innerHTML = `
            <strong>Success!</strong> Code executed successfully.
            <div class="mt-2"><strong>Result:</strong> <code>${JSON.stringify(result.result)}</code></div>
        `;
    } else {
        resultsContainer.classList.remove('alert-success');
        resultsContainer.classList.add('alert-danger');
        resultsContent.innerHTML = `
            <strong>Error!</strong> Code execution failed.
            <div class="mt-2"><strong>Error:</strong> <code>${result.error}</code></div>
        `;
    }
}

// Toggle between code editor and structured mode
function toggleRuleCreationMode() {
    const mode = document.querySelector('input[name="ruleCreationMode"]:checked').value;
    
    if (mode === 'codeEditor') {
        document.getElementById('codeEditorMode').classList.remove('d-none');
        document.getElementById('structuredMode').classList.add('d-none');
        
        // If we have rule lines, generate code for the editors
        if ((currentRuleLines.conditions && currentRuleLines.conditions.length > 0) || 
            (currentRuleLines.actions && currentRuleLines.actions.length > 0)) {
            generateCodeFromLines();
        }
    } else { // structured mode
        // Check if code in editors is different from what would be generated
        let generatedConditionCode = '';
        if (currentRuleLines.conditions && currentRuleLines.conditions.length > 0) {
            const sortedConditions = [...currentRuleLines.conditions].sort((a, b) => a.sequenceNum - b.sequenceNum);
            generatedConditionCode = sortedConditions.map(line => {
                const params = line.parameters.map(param => {
                    if (param.fieldId && param.fieldName) return `fields.${param.fieldName}`;
                    if (param.literalValue !== null && param.literalValue !== undefined) {
                        if (param.fieldType === 'STRING' || typeof param.literalValue === 'string') return `'${param.literalValue.replace(/'/g, "\\'")}'`;
                        return param.literalValue;
                    }
                    return 'null';
                }).join(', ');
                return `${line.functionName}(${params});`;
            }).join('\n');
        }

        let generatedActionCode = '';
        if (currentRuleLines.actions && currentRuleLines.actions.length > 0) {
            const sortedActions = [...currentRuleLines.actions].sort((a, b) => a.sequenceNum - b.sequenceNum);
            generatedActionCode = sortedActions.map(line => {
                const params = line.parameters.map(param => {
                    if (param.fieldId && param.fieldName) return `fields.${param.fieldName}`;
                    if (param.literalValue !== null && param.literalValue !== undefined) {
                         if (param.fieldType === 'STRING' || typeof param.literalValue === 'string') return `'${param.literalValue.replace(/'/g, "\\'")}'`;
                        return param.literalValue;
                    }
                    return 'null';
                }).join(', ');
                return `${line.functionName}(${params});`;
            }).join('\n');
        }

        const currentConditionCode = window.conditionEditor ? window.conditionEditor.getValue().trim() : '';
        const currentActionCode = window.actionEditor ? window.actionEditor.getValue().trim() : '';

        if (generatedConditionCode.trim() !== currentConditionCode || generatedActionCode.trim() !== currentActionCode) {
            if (!confirm("Switching to Structured Mode will discard any manual changes made in the Code Editor and regenerate from existing structured lines. Are you sure you want to continue?")) {
                document.getElementById('modeCodeEditor').checked = true; // Revert radio button
                // The UI should remain in code editor mode, so no need to toggle classes here,
                // as the radio button change might trigger this function again or the state is already correct.
                // If the radio button change itself doesn't re-trigger toggleRuleCreationMode, 
                // or to be absolutely sure the UI is in the correct state:
                // document.getElementById('codeEditorMode').classList.remove('d-none');
                // document.getElementById('structuredMode').classList.add('d-none');
                return; // Abort the switch
            }
        }

        document.getElementById('codeEditorMode').classList.add('d-none');
        document.getElementById('structuredMode').classList.remove('d-none');
        
        // If we have code in the editors, we could try to parse it (advanced feature)
        // For now, we'll just show what we have in the structured mode
        renderRuleLines();
    }
}

// Load rule lines when editing a rule
function loadRuleLines(ruleId) {
    if (!ruleId) {
        // New rule, no lines to load
        renderRuleLines();
        return;
    }
    
    fetch(`/rules/get_rule_lines/${ruleId}`)
        .then(response => response.json())
        .then(data => {
            // Reset current rule lines
            currentRuleLines = { conditions: [], actions: [] };
            
            // Process and categorize the lines
            data.forEach(line => {
                const lineObj = {
                    id: line.LINE_ID,
                    functionId: line.FUNCTION_ID,
                    functionName: line.FUNC_NAME,
                    sequenceNum: line.SEQUENCE_NUM,
                    parameters: line.parameters.map(param => ({
                        id: param.PARAM_ID,
                        index: param.PARAM_INDEX,
                        fieldId: param.FIELD_ID,
                        fieldName: param.GF_NAME,
                        fieldType: param.GF_TYPE,
                        literalValue: param.LITERAL_VALUE
                    }))
                };
                
                if (line.IS_CONDITION) {
                    currentRuleLines.conditions.push(lineObj);
                } else {
                    currentRuleLines.actions.push(lineObj);
                }
            });
            
            // Render the lines in the UI
            renderRuleLines();
        })
        .catch(error => {
            showToast('Error', 'Failed to load rule lines', 'error');
            console.error('Error loading rule lines:', error);
        });
}

// Render rule lines to the UI
function renderRuleLines() {
    renderConditionLines();
    renderActionLines();
}

// Render condition lines
function renderConditionLines() {
    const conditionsList = document.getElementById('conditionLinesList');
    const noConditionsMessage = document.getElementById('noConditionLines');
    
    if (!conditionsList) return;
    
    // Clear the current content
    conditionsList.innerHTML = '';
    
    if (!currentRuleLines.conditions || currentRuleLines.conditions.length === 0) {
        if (noConditionsMessage) {
            conditionsList.appendChild(noConditionsMessage.cloneNode(true));
        } else {
            conditionsList.innerHTML = `
                <tr id="noConditionLines">
                    <td colspan="3" class="text-center text-muted py-3">
                        <i class="fas fa-info-circle me-2"></i>
                        No condition lines defined. Add a condition line to start.
                    </td>
                </tr>
            `;
        }
        return;
    }
    
    // Sort by sequence number
    const sortedConditions = [...currentRuleLines.conditions].sort((a, b) => a.sequenceNum - b.sequenceNum);
    
    // Render each condition line
    sortedConditions.forEach((line, index) => {
        // Format parameters for display
        const paramDisplay = formatParametersForDisplay(line.parameters);
        
        const lineRow = document.createElement('tr');
        lineRow.setAttribute('data-line-id', line.id || `temp-${index}`);
        lineRow.innerHTML = `
            <td>${line.functionName}</td>
            <td>${paramDisplay}</td>
            <td class="text-end">
                <button class="btn btn-sm btn-warning me-1" onclick="editRuleLine(${line.id || `'temp-${index}'`}, true)">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-sm btn-danger" onclick="deleteRuleLine(${line.id || `'temp-${index}'`}, true)">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        `;
        
        conditionsList.appendChild(lineRow);
    });
}

// Render action lines
function renderActionLines() {
    const actionsList = document.getElementById('actionLinesList');
    const noActionsMessage = document.getElementById('noActionLines');
    
    if (!actionsList) return;
    
    // Clear the current content
    actionsList.innerHTML = '';
    
    if (!currentRuleLines.actions || currentRuleLines.actions.length === 0) {
        if (noActionsMessage) {
            actionsList.appendChild(noActionsMessage.cloneNode(true));
        } else {
            actionsList.innerHTML = `
                <tr id="noActionLines">
                    <td colspan="3" class="text-center text-muted py-3">
                        <i class="fas fa-info-circle me-2"></i>
                        No action lines defined. Add an action line to start.
                    </td>
                </tr>
            `;
        }
        return;
    }
    
    // Sort by sequence number
    const sortedActions = [...currentRuleLines.actions].sort((a, b) => a.sequenceNum - b.sequenceNum);
    
    // Render each action line
    sortedActions.forEach((line, index) => {
        // Format parameters for display
        const paramDisplay = formatParametersForDisplay(line.parameters);
        
        const lineRow = document.createElement('tr');
        lineRow.setAttribute('data-line-id', line.id || `temp-${index}`);
        lineRow.innerHTML = `
            <td>${line.functionName}</td>
            <td>${paramDisplay}</td>
            <td class="text-end">
                <button class="btn btn-sm btn-warning me-1" onclick="editRuleLine(${line.id || `'temp-${index}'`}, false)">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-sm btn-danger" onclick="deleteRuleLine(${line.id || `'temp-${index}'`}, false)">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        `;
        
        actionsList.appendChild(lineRow);
    });
}

// Format parameters for display in the rule lines list
function formatParametersForDisplay(parameters) {
    if (!parameters || parameters.length === 0) {
        return '<span class="text-muted">No parameters</span>';
    }
    
    return parameters.map(param => {
        if (param.fieldId && param.fieldName) {
            return `<span class="badge bg-primary">${param.fieldName}</span>`;
        } else if (param.literalValue !== null && param.literalValue !== undefined) {
            return `<span class="badge bg-secondary">${param.literalValue}</span>`;
        } else {
            return `<span class="badge bg-light text-dark">Empty</span>`;
        }
    }).join(' ');
}

// Generate code from rule lines
function generateCodeFromLines() {
    if (!window.conditionEditor || !window.actionEditor) return;
    
    // Process conditions
    let conditionCode = '';
    if (currentRuleLines.conditions && currentRuleLines.conditions.length > 0) {
        // Sort by sequence number
        const sortedConditions = [...currentRuleLines.conditions].sort((a, b) => a.sequenceNum - b.sequenceNum);
        
        // Generate code
        conditionCode = sortedConditions.map(line => {
            const params = line.parameters.map(param => {
                if (param.fieldId && param.fieldName) {
                    return `fields.${param.fieldName}`;
                } else if (param.literalValue !== null && param.literalValue !== undefined) {
                    // Add quotes for string literals
                    if (param.fieldType === 'STRING' || typeof param.literalValue === 'string') {
                        return `'${param.literalValue}'`;
                    } else {
                        return param.literalValue;
                    }
                } else {
                    return 'null';
                }
            }).join(', ');
            
            return `${line.functionName}(${params});`;
        }).join('\n');
    }
    
    // Process actions
    let actionCode = '';
    if (currentRuleLines.actions && currentRuleLines.actions.length > 0) {
        // Sort by sequence number
        const sortedActions = [...currentRuleLines.actions].sort((a, b) => a.sequenceNum - b.sequenceNum);
        
        // Generate code
        actionCode = sortedActions.map(line => {
            const params = line.parameters.map(param => {
                if (param.fieldId && param.fieldName) {
                    return `fields.${param.fieldName}`;
                } else if (param.literalValue !== null && param.literalValue !== undefined) {
                    // Add quotes for string literals
                    if (param.fieldType === 'STRING' || typeof param.literalValue === 'string') {
                        return `'${param.literalValue}'`;
                    } else {
                        return param.literalValue;
                    }
                } else {
                    return 'null';
                }
            }).join(', ');
            
            return `${line.functionName}(${params});`;
        }).join('\n');
    }
    
    // Set the code in the editors
    window.conditionEditor.setValue(conditionCode);
    window.actionEditor.setValue(actionCode);
}

// Add a new rule line
function addRuleLine(isCondition) {
    // Reset the rule line form
    document.getElementById('ruleLineForm').reset();
    document.getElementById('lineId').value = '';
    document.getElementById('isCondition').value = isCondition ? '1' : '0';
    
    // Set modal title
    document.getElementById('ruleLineModalTitle').textContent = `Add ${isCondition ? 'Condition' : 'Action'} Line`;
    
    // Calculate default sequence number (last + 10)
    const lines = isCondition ? currentRuleLines.conditions : currentRuleLines.actions;
    let seqNum = 10;
    if (lines && lines.length > 0) {
        const maxSeq = Math.max(...lines.map(l => l.sequenceNum || 0));
        seqNum = maxSeq + 10;
    }
    document.getElementById('sequenceNum').value = seqNum;
    
    // Clear parameters container
    document.getElementById('parametersContainer').innerHTML = `
        <div class="text-center text-muted py-3">
            <i class="fas fa-info-circle me-2"></i>
            Select a function to set parameters.
        </div>
    `;
    
    // Show the modal
    ruleLineModal.show();
}

// Edit an existing rule line
function editRuleLine(lineId, isCondition) {
    // Find the line to edit
    const lines = isCondition ? currentRuleLines.conditions : currentRuleLines.actions;
    const line = lines.find(l => {
        if (typeof lineId === 'string' && lineId.startsWith('temp-')) {
            // Handle temporary lines
            return `temp-${l.tempIndex}` === lineId;
        } else {
            return l.id === lineId;
        }
    });
    
    if (!line) {
        showToast('Error', 'Rule line not found', 'error');
        return;
    }
    
    // Set the current editing line
    currentEditingLine = {
        id: line.id,
        isCondition: isCondition,
        tempId: typeof lineId === 'string' ? lineId : null
    };
    
    // Reset the rule line form and set values
    document.getElementById('ruleLineForm').reset();
    document.getElementById('lineId').value = line.id || '';
    document.getElementById('isCondition').value = isCondition ? '1' : '0';
    document.getElementById('sequenceNum').value = line.sequenceNum || 0;
    document.getElementById('functionSelect').value = line.functionId;
    
    // Set modal title
    document.getElementById('ruleLineModalTitle').textContent = `Edit ${isCondition ? 'Condition' : 'Action'} Line`;
    
    // IMPORTANT FIX: Pass the existing parameters to the handleFunctionSelection function
    handleFunctionSelection(line.parameters); // This was already correct as per the prompt.

    // Show the modal
    ruleLineModal.show();
}

// Handle function selection in rule line modal
function handleFunctionSelection(existingParams = null) {
    const functionId = document.getElementById('functionSelect').value;
    const parametersContainer = document.getElementById('parametersContainer');
    
    // Clear previous parameters
    parametersContainer.innerHTML = '';
    
    if (!functionId) {
        parametersContainer.innerHTML = `
            <div class="text-center text-muted py-3">
                <i class="fas fa-info-circle me-2"></i>
                Select a function to set parameters.
            </div>
        `;
        return;
    }
    
    // Find the selected function
    const func = allFunctions.find(f => f.GBF_ID == functionId);
    
    if (!func) {
        console.error('Function not found with ID:', functionId);
        showToast('Error', 'Function not found', 'error');
        return;
    }
    
    const paramCount = func.PARAM_COUNT || 0;
    console.log(`Function ${func.FUNC_NAME || func.name} has ${paramCount} parameters`);
    
    // Get function parameters if available
    let funcParams = [];
    if (func.parameters) {
        funcParams = func.parameters;
    }
    
    // Create input fields for each parameter
    for (let i = 0; i < paramCount; i++) {
        // Get parameter name from func.parameters if available, otherwise use default
        const paramName = funcParams[i]?.PARAM_NAME || `Parameter ${i+1}`;
        
        // Check if we have existing parameter values
        let existingParam = null;
        if (existingParams && existingParams[i]) {
            existingParam = existingParams[i];
        }
        
        // Create parameter group
        const paramGroup = document.createElement('div');
        paramGroup.className = 'mb-3 parameter-group';
        paramGroup.setAttribute('data-param-index', i);
        
        // Create parameter label and controls
        paramGroup.innerHTML = `
            <label class="form-label">${paramName}</label>
            <div class="input-group">
                <select class="form-select param-source" data-param-index="${i}" onchange="toggleParameterValueType(this)">
                    <option value="field" ${existingParam && existingParam.fieldId ? 'selected' : ''}>Field</option>
                    <option value="literal" ${existingParam && existingParam.literalValue !== null && existingParam.literalValue !== undefined && (existingParam.fieldId === null || existingParam.fieldId === undefined) ? 'selected' : ''}>Literal Value</option>
                </select>
                <div class="field-selector ${existingParam && existingParam.fieldId ? '' : 'd-none'}">
                    <select class="form-select param-field" data-param-index="${i}">
                        <option value="">Select Field</option>
                        ${classFields.map(field => `
                            <option value="${field.GF_ID}" ${existingParam && existingParam.fieldId && existingParam.fieldId == field.GF_ID ? 'selected' : ''}>
                                ${field.GF_NAME}
                            </option>
                        `).join('')}
                    </select>
                </div>
                <div class="literal-value ${existingParam && existingParam.literalValue !== null && existingParam.literalValue !== undefined && (existingParam.fieldId === null || existingParam.fieldId === undefined) ? '' : 'd-none'}">
                    <input type="text" class="form-control param-literal" data-param-index="${i}" 
                        value="${existingParam && (existingParam.literalValue !== null && existingParam.literalValue !== undefined) ? existingParam.literalValue : ''}">
                </div>
            </div>
        `;
        
        parametersContainer.appendChild(paramGroup);
    }
    
    if (paramCount === 0) {
        parametersContainer.innerHTML = `
            <div class="alert alert-info">
                This function has no parameters.
            </div>
        `;
    }
}

// Toggle between field and literal value for parameters
function toggleParameterValueType(selectElement) {
    const paramIndex = selectElement.getAttribute('data-param-index');
    const paramGroup = selectElement.closest('.parameter-group');
    const fieldSelector = paramGroup.querySelector('.field-selector');
    const literalValue = paramGroup.querySelector('.literal-value');
    
    const selectedValue = selectElement.value;
    
    if (selectedValue === 'field') {
        fieldSelector.classList.remove('d-none');
        literalValue.classList.add('d-none');
    } else {
        fieldSelector.classList.add('d-none');
        literalValue.classList.remove('d-none');
    }
}

// Save rule line
function saveRuleLine() {
    const lineId = document.getElementById('lineId').value;
    const isCondition = document.getElementById('isCondition').value === '1';
    const functionId = document.getElementById('functionSelect').value;
    const sequenceNum = parseInt(document.getElementById('sequenceNum').value) || 0;
    
    if (!functionId) {
        showToast('Error', 'Please select a function', 'error');
        return;
    }
    
    // Find the selected function
    const func = allFunctions.find(f => f.GBF_ID == functionId || f.FUNC_ID == functionId);
    
    if (!func) {
        showToast('Error', 'Function not found', 'error');
        return;
    }
    
    // Get function name
    const functionName = func.FUNC_NAME || func.name;
    
    // Collect parameters
    const parameters = [];
    const paramCount = func.PARAM_COUNT || 0;
    
    for (let i = 0; i < paramCount; i++) {
        const paramGroup = document.querySelector(`.parameter-group[data-param-index="${i}"]`);
        
        if (paramGroup) {
            const paramSource = paramGroup.querySelector('.param-source').value;
            
            if (paramSource === 'field') {
                const fieldId = paramGroup.querySelector('.param-field').value;
                if (fieldId) {
                    const field = classFields.find(f => f.GF_ID == fieldId);
                    parameters.push({
                        index: i,
                        fieldId: parseInt(fieldId),
                        fieldName: field ? field.GF_NAME : '',
                        fieldType: field ? field.GF_TYPE : '',
                        literalValue: null
                    });
                } else {
                    parameters.push({
                        index: i,
                        fieldId: null,
                        fieldName: '',
                        fieldType: '',
                        literalValue: null
                    });
                }
            } else {
                const literalValue = paramGroup.querySelector('.param-literal').value;
                parameters.push({
                    index: i,
                    fieldId: null,
                    fieldName: '',
                    fieldType: '',
                    literalValue: literalValue
                });
            }
        }
    }
    
    // Create or update the line object
    const lineObj = {
        id: lineId || null,
        functionId: parseInt(functionId),
        functionName: functionName,
        sequenceNum: sequenceNum,
        parameters: parameters,
        isTemp: !lineId || lineId.toString().startsWith('temp-')
    };
    
    // Add or update in the appropriate array
    if (currentEditingLine) {
        // Update existing line
        const lines = isCondition ? currentRuleLines.conditions : currentRuleLines.actions;
        const lineIndex = lines.findIndex(l => {
            if (currentEditingLine.tempId && currentEditingLine.tempId.startsWith('temp-')) {
                return currentEditingLine.tempId === `temp-${l.tempIndex}`;
            } else {
                return l.id === currentEditingLine.id;
            }
        });
        
        if (lineIndex >= 0) {
            lines[lineIndex] = lineObj;
        } else {
            // Not found, add as new
            lineObj.tempIndex = Date.now();
            lines.push(lineObj);
        }
    } else {
        // Add new line
        lineObj.tempIndex = Date.now();
        if (isCondition) {
            if (!currentRuleLines.conditions) currentRuleLines.conditions = [];
            currentRuleLines.conditions.push(lineObj);
        } else {
            if (!currentRuleLines.actions) currentRuleLines.actions = [];
            currentRuleLines.actions.push(lineObj);
        }
    }
    
    // Reset current editing line
    currentEditingLine = null;
    
    // Hide the modal and render the updated lines
    ruleLineModal.hide();
    renderRuleLines();
    
    // If we're in code editor mode, also update the code
    if (document.getElementById('modeCodeEditor').checked) {
        generateCodeFromLines();
    }
}

// Delete a rule line
function deleteRuleLine(lineId, isCondition) {
    const lines = isCondition ? currentRuleLines.conditions : currentRuleLines.actions;
    
    let lineIndex;
    if (typeof lineId === 'string' && lineId.startsWith('temp-')) {
        // Handle temporary lines
        lineIndex = lines.findIndex(l => `temp-${l.tempIndex}` === lineId);
    } else {
        lineIndex = lines.findIndex(l => l.id === lineId);
    }
    
    if (lineIndex >= 0) {
        // For server-persisted lines, we need to delete from server if the rule exists
        const line = lines[lineIndex];
        const ruleId = document.getElementById('ruleId').value;
        
        if (ruleId && line.id && !line.isTemp) {
            fetch(`/rules/delete_rule_line/${line.id}`, {
                method: 'DELETE'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    lines.splice(lineIndex, 1);
                    renderRuleLines();
                    
                    // If we're in code editor mode, also update the code
                    if (document.getElementById('modeCodeEditor').checked) {
                        generateCodeFromLines();
                    }
                    
                    showToast('Success', data.message);
                } else {
                    showToast('Error', data.message, 'error');
                }
            })
            .catch(error => {
                showToast('Error', 'An error occurred while deleting the rule line', 'error');
                console.error('Error:', error);
            });
        } else {
            // For temporary lines or new rules, just remove from our array
            lines.splice(lineIndex, 1);
            renderRuleLines();
            
            // If we're in code editor mode, also update the code
            if (document.getElementById('modeCodeEditor').checked) {
                generateCodeFromLines();
            }
        }
    }
}

// Save rule lines to server
function saveRuleLinesToServer(ruleId) {
    if (!ruleId) {
        return Promise.reject('No rule ID provided');
    }
    
    // Process all rule lines (both conditions and actions)
    const allLines = [
        ...currentRuleLines.conditions.map(line => ({...line, isCondition: true})),
        ...currentRuleLines.actions.map(line => ({...line, isCondition: false}))
    ];
    
    // Create a chain of promises to save each line sequentially
    let savePromise = Promise.resolve();
    
    allLines.forEach(line => {
        savePromise = savePromise.then(() => {
            return saveSingleRuleLine(ruleId, line);
        });
    });
    
    return savePromise;
}

// Save a single rule line to the server
function saveSingleRuleLine(ruleId, line) {
    const data = {
        ruleId: ruleId,
        functionId: line.functionId,
        isCondition: line.isCondition,
        sequenceNum: line.sequenceNum,
        parameters: line.parameters.map(p => ({
            fieldId: p.fieldId,
            literalValue: p.literalValue
        }))
    };
    
    return fetch('/rules/add_rule_line', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (!result.success) {
            showToast('Error', `Error saving rule line: ${result.message}`, 'error');
            throw new Error(result.message);
        }
        return result;
    });
}

// Search rules
function searchRules() {
    const searchTerm = document.getElementById('searchRules').value.toLowerCase();
    const ruleType = document.getElementById('filterRuleType').value;
    const classFilter = document.getElementById('filterClass').value;
    
    let filteredRules = allRules;
    
    // Apply search filter
    if (searchTerm) {
        filteredRules = filteredRules.filter(rule => 
            rule.RULE_NAME.toLowerCase().includes(searchTerm) || 
            (rule.DESCRIPTION && rule.DESCRIPTION.toLowerCase().includes(searchTerm))
        );
    }
    
    // Apply rule type filter
    if (ruleType) {
        filteredRules = filteredRules.filter(rule => rule.RULE_TYPE === ruleType);
    }
    
    // Apply class filter
    if (classFilter) {
        filteredRules = filteredRules.filter(rule => rule.GFC_ID === parseInt(classFilter));
    }
    
    renderRules(filteredRules);
    
    // Update rule count
    const ruleCount = document.getElementById('ruleCount');
    if (ruleCount) {
        ruleCount.textContent = `${filteredRules.length} rules`;
    }
}

// Filter rules
function filterRules() {
    // Reuse search function as it handles both search and filter
    searchRules();
}

// Show toast notification
function showToast(title, message, type = 'success') {
    // Check if we have the showToast function from base.html
    if (typeof window.showToast === 'function') {
        window.showToast(title, message, type);
        return;
    }
    
    // Fallback toast implementation
    const toast = document.createElement('div');
    toast.className = `toast position-fixed top-0 end-0 m-3 bg-${type === 'success' ? 'success' : type === 'error' ? 'danger' : 'warning'} text-white`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="toast-header">
            <strong class="me-auto">${title}</strong>
            <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">
            ${message}
        </div>
    `;
    
    document.body.appendChild(toast);
    
    // Use Bootstrap toast if available
    if (typeof bootstrap !== 'undefined') {
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
    } else {
        // Simple fallback
        toast.style.display = 'block';
        setTimeout(() => {
            toast.style.display = 'none';
            document.body.removeChild(toast);
        }, 3000);
    }
}