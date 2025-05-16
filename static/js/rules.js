// Rules Management JavaScript

// Global variables
let allRules = [];
let allClasses = [];
let allFields = [];
let allFunctions = [];
let currentDeleteId = null;
let selectedClass = null;
let classFields = [];

// Bootstrap modal instances
let ruleModal;
let deleteModal;
let functionSelectorModal;
let fieldSelectorModal;
let ruleLineModal;
let currentRuleLines = { conditions: [], actions: [] };
let currentEditingLine = null;

document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap modals
    ruleModal = new bootstrap.Modal(document.getElementById('ruleModal'));
    deleteModal = new bootstrap.Modal(document.getElementById('deleteModal'));
    functionSelectorModal = new bootstrap.Modal(document.getElementById('functionSelectorModal'));
    fieldSelectorModal = new bootstrap.Modal(document.getElementById('fieldSelectorModal'));
    ruleLineModal = new bootstrap.Modal(document.getElementById('ruleLineModal'));
    
    // Setup event listeners
    document.getElementById('saveRuleBtn').addEventListener('click', saveRule);
    document.getElementById('confirmDeleteBtn').addEventListener('click', confirmDelete);
    document.getElementById('insertFunctionBtn').addEventListener('click', () => openFunctionSelector('condition'));
    document.getElementById('insertFieldBtn').addEventListener('click', () => openFieldSelector('condition'));
    document.getElementById('selectFunctionBtn').addEventListener('click', insertSelectedFunction);
    document.getElementById('selectFieldBtn').addEventListener('click', insertSelectedField);
    document.getElementById('testConditionBtn').addEventListener('click', testCondition);
    document.getElementById('testActionBtn').addEventListener('click', testAction);
    document.getElementById('saveLineBtn').addEventListener('click', saveRuleLine);
    
    // Add class change listener
    document.getElementById('ruleClass').addEventListener('change', handleClassChange);
    
    // Add event listeners for rule creation mode toggle
    document.querySelectorAll('input[name="ruleCreationMode"]').forEach(input => {
        input.addEventListener('change', toggleRuleCreationMode);
    });
    
    // Add event listener for function selection in rule line modal
    document.getElementById('functionSelect').addEventListener('change', handleFunctionSelection);
    
    // Load data
    loadRules();
    loadClasses();
    loadFields();
    loadFunctions();
    
    // Initialize code editors
    initializeCodeEditors();
});

// Load rules
function loadRules() {
    fetch('/rules/get_rules')
        .then(response => response.json())
        .then(data => {
            allRules = data;
            renderRules(data);
            
            // Update rule count
            document.getElementById('ruleCount').textContent = `${data.length} rules`;
        })
        .catch(error => {
            showToast('Error', 'Failed to load rules', 'error');
            console.error('Error loading rules:', error);
        });
}

// Load classes for dropdown
function loadClasses() {
    fetch('/class/get_classes')
        .then(response => response.json())
        .then(data => {
            allClasses = data;
            populateClassDropdown(data);
            populateClassFilter(data);
        })
        .catch(error => {
            showToast('Error', 'Failed to load classes', 'error');
            console.error('Error loading classes:', error);
        });
}

// Load fields
function loadFields() {
    fetch('/fields/get_fields')
        .then(response => response.json())
        .then(data => {
            allFields = data;
            // We'll populate the field selector when a class is selected
        })
        .catch(error => {
            showToast('Error', 'Failed to load fields', 'error');
            console.error('Error loading fields:', error);
        });
}

// Load functions
function loadFunctions() {
    fetch('/function/get_functions')
        .then(response => response.json())
        .then(data => {
            if (Array.isArray(data)) {
                allFunctions = data;
                populateFunctionSelector(data);
                populateFunctionDropdown(data);
            } else {
                console.error('Function data is not an array:', data);
                showToast('Error', 'Function data has unexpected format', 'error');
            }
        })
        .catch(error => {
            showToast('Error', 'Failed to load functions', 'error');
            console.error('Error loading functions:', error);
        });
}

// Populate the class dropdown
function populateClassDropdown(classes) {
    const dropdown = document.getElementById('ruleClass');
    dropdown.innerHTML = '<option value="">Select Class</option>';
    
    classes.forEach(cls => {
        dropdown.innerHTML += `<option value="${cls.GFC_ID}">${cls.FIELD_CLASS_NAME}</option>`;
    });
}

// Populate the class filter dropdown
function populateClassFilter(classes) {
    const filterDropdown = document.getElementById('filterClass');
    if (filterDropdown) {
        filterDropdown.innerHTML = '<option value="">All Classes</option>';
        
        classes.forEach(cls => {
            filterDropdown.innerHTML += `<option value="${cls.GFC_ID}">${cls.FIELD_CLASS_NAME}</option>`;
        });
    }
}

// Populate the function dropdown
function populateFunctionDropdown(functions) {
    const dropdown = document.getElementById('functionSelect');
    dropdown.innerHTML = '<option value="">Select Function</option>';
    
    functions.forEach(func => {
        const funcId = func.GBF_ID || func.FUNC_ID || 0;
        const funcName = func.FUNC_NAME || func.name || 'Unknown Function';
        dropdown.innerHTML += `<option value="${funcId}">${funcName}</option>`;
    });
}

// Handle class change event
function handleClassChange() {
    const classId = document.getElementById('ruleClass').value;
    selectedClass = classId ? parseInt(classId) : null;
    
    // Update the available fields based on the selected class
    if (selectedClass) {
        // Filter fields for this class
        classFields = allFields.filter(field => field.GFC_ID === selectedClass);
    } else {
        classFields = [];
    }
    
    // Update the field selector if it's open
    populateFieldSelector(classFields);
    
    // Update the field button's state
    const insertFieldBtn = document.getElementById('insertFieldBtn');
    if (insertFieldBtn) {
        if (classFields.length === 0) {
            insertFieldBtn.disabled = true;
            insertFieldBtn.title = "Select a class first to enable field selection";
        } else {
            insertFieldBtn.disabled = false;
            insertFieldBtn.title = "";
        }
    }
}

// Populate field selector based on selected class
function populateFieldSelector(fields) {
    const fieldList = document.getElementById('fieldsList');
    if (!fieldList) return;
    
    fieldList.innerHTML = '';
    
    if (fields.length === 0) {
        fieldList.innerHTML = `
            <tr>
                <td colspan="3" class="text-center text-muted py-3">
                    <i class="fas fa-info-circle me-2"></i>
                    ${selectedClass ? 'No fields available for this class.' : 'Please select a class first.'}
                </td>
            </tr>
        `;
        return;
    }
    
    fields.forEach(field => {
        fieldList.innerHTML += `
            <tr data-field-id="${field.GF_ID}" data-field-name="${field.GF_NAME}" class="field-row">
                <td>${field.GF_NAME}</td>
                <td>${field.GF_TYPE}</td>
                <td class="text-end">
                    <button class="btn btn-sm btn-primary" onclick="selectField(${field.GF_ID})">Select</button>
                </td>
            </tr>
        `;
    });
}

// Populate function selector
function populateFunctionSelector(functions) {
    const functionList = document.getElementById('functionsList');
    if (!functionList) return;
    
    functionList.innerHTML = '';
    
    if (!Array.isArray(functions) || functions.length === 0) {
        functionList.innerHTML = `
            <tr>
                <td colspan="3" class="text-center text-muted py-3">
                    <i class="fas fa-info-circle me-2"></i>
                    No functions available. Please create functions first.
                </td>
            </tr>
        `;
        return;
    }
    
    functions.forEach(func => {
        // Make sure we have required properties and provide fallbacks
        const funcId = func.GBF_ID || func.FUNC_ID || 0;
        const funcName = func.FUNC_NAME || func.name || 'Unknown Function';
        const paramCount = func.PARAM_COUNT || 0;
        
        functionList.innerHTML += `
            <tr data-function-id="${funcId}" data-function-name="${funcName}" class="function-row">
                <td>${funcName}</td>
                <td>${paramCount} params</td>
                <td class="text-end">
                    <button class="btn btn-sm btn-primary" onclick="selectFunction(${funcId})">Select</button>
                </td>
            </tr>
        `;
    });
}

// Render rules to the table
function renderRules(rules) {
    const tableBody = document.getElementById('ruleList');
    const noRulesMessage = document.getElementById('noRulesMessage');
    
    if (!tableBody || !noRulesMessage) return;
    
    tableBody.innerHTML = '';
    
    if (rules.length === 0) {
        noRulesMessage.classList.remove('d-none');
        return;
    }
    
    noRulesMessage.classList.add('d-none');
    
    rules.forEach(rule => {
        const ruleType = rule.RULE_TYPE || 'Standard';
        // Find class name from the class ID
        const className = allClasses.find(c => c.GFC_ID === rule.GFC_ID)?.FIELD_CLASS_NAME || 'None';
        const updateDate = formatDate(rule.UPDATE_DATE || rule.CREATE_DATE);
        
        // Build the row
        const row = `
            <tr data-id="${rule.RULE_ID}">
                <td class="fw-medium">${rule.RULE_NAME}</td>
                <td>${className}</td>
                <td><span class="rule-type-badge rule-type-${ruleType.toLowerCase()}">${ruleType}</span></td>
                <td>${rule.DESCRIPTION || '<span class="text-muted">No description</span>'}</td>
                <td>${updateDate || '-'}</td>
                <td class="text-end">
                    <button class="btn btn-warning btn-sm me-1" onclick="editRule(${rule.RULE_ID})">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-danger btn-sm" onclick="deleteRule(${rule.RULE_ID})">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `;
        
        tableBody.innerHTML += row;
    });
}

// Format date
function formatDate(dateString) {
    if (!dateString) return '';
    
    try {
        const date = new Date(dateString);
        return date.toLocaleString();
    } catch (e) {
        return dateString;
    }
}

// Initialize code editors
function initializeCodeEditors() {
    if (typeof CodeMirror === 'undefined') {
        console.warn('CodeMirror is not available. Code editors will not be initialized.');
        return;
    }

    const conditionCodeElement = document.getElementById('conditionCode');
    const actionCodeElement = document.getElementById('actionCode');

    if (conditionCodeElement && actionCodeElement) {
        // Initialize condition editor
        window.conditionEditor = CodeMirror.fromTextArea(conditionCodeElement, {
            mode: 'javascript',
            theme: 'default',
            lineNumbers: true,
            autoCloseBrackets: true,
            matchBrackets: true,
            indentUnit: 4,
            tabSize: 4,
            lineWrapping: true,
            extraKeys: {
                "Ctrl-Space": "autocomplete"
            }
        });
        
        // Initialize action editor
        window.actionEditor = CodeMirror.fromTextArea(actionCodeElement, {
            mode: 'javascript',
            theme: 'default',
            lineNumbers: true,
            autoCloseBrackets: true,
            matchBrackets: true,
            indentUnit: 4,
            tabSize: 4,
            lineWrapping: true,
            extraKeys: {
                "Ctrl-Space": "autocomplete"
            }
        });
        
        // Set custom height
        window.conditionEditor.setSize(null, 150);
        window.actionEditor.setSize(null, 150);
    }
}

// Open the rule modal for creating a new rule
function openNewRuleModal() {
    document.getElementById('modalTitle').textContent = 'Add New Rule';
    document.getElementById('ruleForm').reset();
    document.getElementById('ruleId').value = '';
    
    // Reset CodeMirror editors if they exist
    if (window.conditionEditor && window.actionEditor) {
        window.conditionEditor.setValue('');
        window.actionEditor.setValue('');
    }
    
    // Reset test results
    const conditionResults = document.getElementById('conditionResults');
    const actionResults = document.getElementById('actionResults');
    if (conditionResults) conditionResults.classList.add('d-none');
    if (actionResults) actionResults.classList.add('d-none');
    
    // Reset selected class
    selectedClass = null;
    classFields = [];
    
    // Disable field button initially
    const insertFieldBtn = document.getElementById('insertFieldBtn');
    if (insertFieldBtn) insertFieldBtn.disabled = true;
    
    // Reset rule lines
    currentRuleLines = { conditions: [], actions: [] };
    
    // Reset rule creation mode
    document.getElementById('modeCodeEditor').checked = true;
    document.getElementById('codeEditorMode').classList.remove('d-none');
    document.getElementById('structuredMode').classList.add('d-none');
    
    ruleModal.show();
}

// Edit rule
function editRule(ruleId) {
    // Find rule in the allRules array
    const rule = allRules.find(r => r.RULE_ID === ruleId);
    
    if (rule) {
        document.getElementById('modalTitle').textContent = 'Edit Rule';
        document.getElementById('ruleId').value = rule.RULE_ID;
        document.getElementById('ruleName').value = rule.RULE_NAME;
        document.getElementById('ruleClass').value = rule.GFC_ID || '';
        document.getElementById('ruleType').value = rule.RULE_TYPE || 'Standard';
        document.getElementById('ruleDescription').value = rule.DESCRIPTION || '';
        
        // Set selected class
        selectedClass = rule.GFC_ID ? parseInt(rule.GFC_ID) : null;
        
        // Update fields for this class
        if (selectedClass) {
            classFields = allFields.filter(field => field.GFC_ID === selectedClass);
            const insertFieldBtn = document.getElementById('insertFieldBtn');
            if (insertFieldBtn) insertFieldBtn.disabled = false;
        } else {
            classFields = [];
            const insertFieldBtn = document.getElementById('insertFieldBtn');
            if (insertFieldBtn) insertFieldBtn.disabled = true;
        }
        
        // Load the condition and action code
        if (window.conditionEditor && window.actionEditor) {
            window.conditionEditor.setValue(rule.CONDITION_CODE || '');
            window.actionEditor.setValue(rule.ACTION_CODE || '');
        }
        
        // Reset test results
        const conditionResults = document.getElementById('conditionResults');
        const actionResults = document.getElementById('actionResults');
        if (conditionResults) conditionResults.classList.add('d-none');
        if (actionResults) actionResults.classList.add('d-none');
        
        // Reset rule creation mode
        document.getElementById('modeCodeEditor').checked = true;
        document.getElementById('codeEditorMode').classList.remove('d-none');
        document.getElementById('structuredMode').classList.add('d-none');
        
        // Load rule lines if this is an existing rule
        currentRuleLines = { conditions: [], actions: [] };
        loadRuleLines(rule.RULE_ID);
        
        ruleModal.show();
    } else {
        showToast('Error', 'Rule not found', 'error');
    }
}

// Delete rule
function deleteRule(ruleId) {
    currentDeleteId = ruleId;
    deleteModal.show();
}

// Confirm delete
function confirmDelete() {
    if (!currentDeleteId) return;
    
    fetch(`/rules/delete_rule/${currentDeleteId}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            deleteModal.hide();
            loadRules();
            showToast('Success', data.message);
        } else {
            showToast('Error', data.message, 'error');
        }
    })
    .catch(error => {
        showToast('Error', 'An error occurred while deleting the rule', 'error');
        console.error('Error:', error);
    });
}

// Save rule
function saveRule() {
    const ruleId = document.getElementById('ruleId').value;
    const ruleName = document.getElementById('ruleName').value;
    const classId = document.getElementById('ruleClass').value;
    const ruleType = document.getElementById('ruleType').value;
    const description = document.getElementById('ruleDescription').value;
    
    // Check which mode we're in
    const mode = document.querySelector('input[name="ruleCreationMode"]:checked').value;
    
    // Get the code from the appropriate source
    let conditionCode = '';
    let actionCode = '';
    
    if (mode === 'codeEditor') {
        conditionCode = window.conditionEditor ? window.conditionEditor.getValue() : '';
        actionCode = window.actionEditor ? window.actionEditor.getValue() : '';
    } else {
        // For structured mode, generate code from the rule lines
        generateCodeFromLines();
        conditionCode = window.conditionEditor ? window.conditionEditor.getValue() : '';
        actionCode = window.actionEditor ? window.actionEditor.getValue() : '';
    }
    
    // Validate required fields
    if (!ruleName) {
        showToast('Error', 'Rule Name is required', 'error');
        return;
    }
    
    if (!classId) {
        showToast('Error', 'Class selection is required', 'error');
        return;
    }
    
    const data = {
        ruleId: ruleId,
        ruleName: ruleName,
        classId: classId,
        ruleType: ruleType,
        description: description,
        conditionCode: conditionCode,
        actionCode: actionCode
    };
    
    const method = ruleId ? 'PUT' : 'POST';
    const url = ruleId ? '/rules/update_rule' : '/rules/add_rule';

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
            // If we just created a new rule and have rule lines, save them
            if (!ruleId && result.id && (
                currentRuleLines.conditions.length > 0 || 
                currentRuleLines.actions.length > 0
            )) {
                saveRuleLinesToServer(result.id)
                    .then(() => {
                        ruleModal.hide();
                        loadRules();
                        showToast('Success', result.message);
                    });
            } else {
                ruleModal.hide();
                loadRules();
                showToast('Success', result.message);
            }
        } else {
            showToast('Error', result.message, 'error');
        }
    })
    .catch(error => {
        showToast('Error', 'An error occurred while saving the rule', 'error');
        console.error('Error:', error);
    });
}

// Open function selector
function openFunctionSelector(target) {
    if (allFunctions.length === 0) {
        showToast('Warning', 'No functions available. Please create functions first.', 'warning');
        return;
    }
    
    // Set the target for inserting the function (condition or action)
    document.querySelector('input[name="insertTarget"][value="' + target + '"]').checked = true;
    
    functionSelectorModal.show();
}

// Open field selector
function openFieldSelector(target) {
    if (!selectedClass) {
        showToast('Warning', 'Please select a class first', 'warning');
        return;
    }
    
    if (classFields.length === 0) {
        showToast('Warning', 'No fields available for this class', 'warning');
        return;
    }
    
    // Set the target for inserting the field (condition or action)
    document.querySelector('input[name="insertTarget"][value="' + target + '"]').checked = true;
    
    populateFieldSelector(classFields);
    fieldSelectorModal.show();
}

// Select a function from the list
function selectFunction(functionId) {
    const func = allFunctions.find(f => f.GBF_ID === functionId || f.FUNC_ID === functionId);
    if (func) {
        document.getElementById('selectedFunctionId').value = functionId;
        document.getElementById('selectedFunctionName').value = func.FUNC_NAME || func.name;
    }
}

// Select a field from the list
function selectField(fieldId) {
    const field = classFields.find(f => f.GF_ID === fieldId);
    if (field) {
        document.getElementById('selectedFieldId').value = fieldId;
        document.getElementById('selectedFieldName').value = field.GF_NAME;
    }
}

// Insert selected function
function insertSelectedFunction() {
    const functionName = document.getElementById('selectedFunctionName').value;
    
    if (!functionName) {
        showToast('Warning', 'Please select a function', 'warning');
        return;
    }
    
    // Get selected insert target (condition or action)
    const insertTarget = document.querySelector('input[name="insertTarget"]:checked').value;
    
    // Create function template with parameter placeholders
    const func = allFunctions.find(f => f.FUNC_NAME === functionName || f.name === functionName);
    const paramCount = func ? (func.PARAM_COUNT || 0) : 0;
    
    let functionTemplate = `${functionName}(`;
    for (let i = 0; i < paramCount; i++) {
        functionTemplate += i > 0 ? `, param${i+1}` : `param${i+1}`;
    }
    functionTemplate += ');';
    
    // Insert into the selected editor
    if (insertTarget === 'condition' && window.conditionEditor) {
        insertAtCursor(window.conditionEditor, functionTemplate);
    } else if (window.actionEditor) {
        insertAtCursor(window.actionEditor, functionTemplate);
    }
    
    functionSelectorModal.hide();
}

// Insert selected field
function insertSelectedField() {
    const fieldName = document.getElementById('selectedFieldName').value;
    
    if (!fieldName) {
        showToast('Warning', 'Please select a field', 'warning');
        return;
    }
    
    // Get selected insert target (condition or action)
    const insertTarget = document.querySelector('input[name="insertTarget"]:checked').value;
    
    // Create field reference template
    const fieldTemplate = `fields.${fieldName}`;
    
    // Insert into the selected editor
    if (insertTarget === 'condition' && window.conditionEditor) {
        insertAtCursor(window.conditionEditor, fieldTemplate);
    } else if (window.actionEditor) {
        insertAtCursor(window.actionEditor, fieldTemplate);
    }
    
    fieldSelectorModal.hide();
}

// Insert text at cursor position in CodeMirror editor
function insertAtCursor(editor, text) {
    const cursor = editor.getCursor();
    editor.replaceRange(text, cursor);
    editor.focus();
}

// Test condition code
function testCondition() {
    if (!window.conditionEditor) return;
    
    const code = window.conditionEditor.getValue();
    
    if (!code) {
        showToast('Warning', 'Please enter condition code to test', 'warning');
        return;
    }
    
    // Send to server for testing
    fetch('/rules/test_code', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            code: code,
            type: 'condition',
            classId: selectedClass
        })
    })
    .then(response => response.json())
    .then(result => {
        displayTestResults('condition', result);
    })
    .catch(error => {
        showToast('Error', 'Error testing condition code', 'error');
        console.error('Error:', error);
    });
}

// Test action code
function testAction() {
    if (!window.actionEditor) return;
    
    const code = window.actionEditor.getValue();
    
    if (!code) {
        showToast('Warning', 'Please enter action code to test', 'warning');
        return;
    }
    
    // Send to server for testing
    fetch('/rules/test_code', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            code: code,
            type: 'action',
            classId: selectedClass
        })
    })
    .then(response => response.json())
    .then(result => {
        displayTestResults('action', result);
    })
    .catch(error => {
        showToast('Error', 'Error testing action code', 'error');
        console.error('Error:', error);
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
    
    // Load parameters
    handleFunctionSelection(line.parameters);
    
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
    const func = allFunctions.find(f => f.GBF_ID == functionId || f.FUNC_ID == functionId);
    
    if (!func) {
        showToast('Error', 'Function not found', 'error');
        return;
    }
    
    const paramCount = func.PARAM_COUNT || 0;
    
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
                    <option value="literal" ${existingParam && existingParam.literalValue !== undefined && existingParam.fieldId === null ? 'selected' : ''}>Literal Value</option>
                </select>
                <div class="field-selector ${existingParam && existingParam.fieldId ? '' : 'd-none'}">
                    <select class="form-select param-field" data-param-index="${i}">
                        <option value="">Select Field</option>
                        ${classFields.map(field => `
                            <option value="${field.GF_ID}" ${existingParam && existingParam.fieldId == field.GF_ID ? 'selected' : ''}>
                                ${field.GF_NAME}
                            </option>
                        `).join('')}
                    </select>
                </div>
                <div class="literal-value ${existingParam && existingParam.literalValue !== undefined && existingParam.fieldId === null ? '' : 'd-none'}">
                    <input type="text" class="form-control param-literal" data-param-index="${i}" 
                        value="${existingParam && existingParam.literalValue !== undefined ? existingParam.literalValue : ''}">
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