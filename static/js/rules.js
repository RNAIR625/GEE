// Rules Management JavaScript

// Global variables
let allRules = [];
let allClasses = [];
let allFields = [];
let allFunctions = [];
let currentDeleteId = null;

// Bootstrap modal instances
let ruleModal;
let deleteModal;
let functionSelectorModal;
let fieldSelectorModal;

document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap modals
    ruleModal = new bootstrap.Modal(document.getElementById('ruleModal'));
    deleteModal = new bootstrap.Modal(document.getElementById('deleteModal'));
    functionSelectorModal = new bootstrap.Modal(document.getElementById('functionSelectorModal'));
    fieldSelectorModal = new bootstrap.Modal(document.getElementById('fieldSelectorModal'));
    
    // Setup event listeners
    document.getElementById('saveRuleBtn').addEventListener('click', saveRule);
    document.getElementById('confirmDeleteBtn').addEventListener('click', confirmDelete);
    document.getElementById('insertFunctionBtn').addEventListener('click', openFunctionSelector);
    document.getElementById('insertFieldBtn').addEventListener('click', openFieldSelector);
    document.getElementById('selectFunctionBtn').addEventListener('click', insertSelectedFunction);
    document.getElementById('selectFieldBtn').addEventListener('click', insertSelectedField);
    document.getElementById('testConditionBtn').addEventListener('click', testCondition);
    document.getElementById('testActionBtn').addEventListener('click', testAction);
    
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
            populateFieldSelector(data);
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
            allFunctions = data;
            populateFunctionSelector(data);
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

// Populate field selector
function populateFieldSelector(fields) {
    const fieldList = document.getElementById('fieldsList');
    fieldList.innerHTML = '';
    
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
    functionList.innerHTML = '';
    
    functions.forEach(func => {
        functionList.innerHTML += `
            <tr data-function-id="${func.GBF_ID}" data-function-name="${func.FUNC_NAME}" class="function-row">
                <td>${func.FUNC_NAME}</td>
                <td>${func.PARAM_COUNT} params</td>
                <td class="text-end">
                    <button class="btn btn-sm btn-primary" onclick="selectFunction(${func.GBF_ID})">Select</button>
                </td>
            </tr>
        `;
    });
}

// Render rules to the table
function renderRules(rules) {
    const tableBody = document.getElementById('ruleList');
    const noRulesMessage = document.getElementById('noRulesMessage');
    
    tableBody.innerHTML = '';
    
    if (rules.length === 0) {
        noRulesMessage.classList.remove('d-none');
        return;
    }
    
    noRulesMessage.classList.add('d-none');
    
    rules.forEach(rule => {
        const ruleType = rule.RULE_TYPE || 'Standard';
        const className = allClasses.find(c => c.GFC_ID === rule.GFC_ID)?.FIELD_CLASS_NAME || 'None';
        const updateDate = formatDate(rule.UPDATE_DATE || rule.CREATE_DATE);
        
        // Build the row
        const row = `
            <tr data-id="${rule.RULE_ID}">
                <td class="fw-medium">${rule.RULE_NAME}</td>
                <td>${className}</td>
                <td>${ruleType}</td>
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
    // Initialize condition editor
    window.conditionEditor = CodeMirror.fromTextArea(document.getElementById('conditionCode'), {
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
    window.actionEditor = CodeMirror.fromTextArea(document.getElementById('actionCode'), {
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

// Open the rule modal for creating a new rule
function openNewRuleModal() {
    document.getElementById('modalTitle').textContent = 'Add New Rule';
    document.getElementById('ruleForm').reset();
    document.getElementById('ruleId').value = '';
    
    // Reset CodeMirror editors
    window.conditionEditor.setValue('');
    window.actionEditor.setValue('');
    
    // Reset test results
    document.getElementById('conditionResults').classList.add('d-none');
    document.getElementById('actionResults').classList.add('d-none');
    
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
        
        // Load the condition and action code
        window.conditionEditor.setValue(rule.CONDITION_CODE || '');
        window.actionEditor.setValue(rule.ACTION_CODE || '');
        
        // Reset test results
        document.getElementById('conditionResults').classList.add('d-none');
        document.getElementById('actionResults').classList.add('d-none');
        
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
    const conditionCode = window.conditionEditor.getValue();
    const actionCode = window.actionEditor.getValue();
    
    if (!ruleName) {
        showToast('Error', 'Rule Name is required', 'error');
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
            ruleModal.hide();
            loadRules();
            showToast('Success', result.message);
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
function openFunctionSelector() {
    functionSelectorModal.show();
}

// Open field selector
function openFieldSelector() {
    fieldSelectorModal.show();
}

// Select a function from the list
function selectFunction(functionId) {
    const func = allFunctions.find(f => f.GBF_ID === functionId);
    if (func) {
        document.getElementById('selectedFunctionId').value = functionId;
        document.getElementById('selectedFunctionName').value = func.FUNC_NAME;
    }
}

// Select a field from the list
function selectField(fieldId) {
    const field = allFields.find(f => f.GF_ID === fieldId);
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
    
    // Create function template
    const functionTemplate = `${functionName}()`;
    
    // Insert into the selected editor
    if (insertTarget === 'condition') {
        insertAtCursor(window.conditionEditor, functionTemplate);
    } else {
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
    if (insertTarget === 'condition') {
        insertAtCursor(window.conditionEditor, fieldTemplate);
    } else {
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
            type: 'condition'
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
            type: 'action'
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
    document.getElementById('ruleCount').textContent = `${filteredRules.length} rules`;
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