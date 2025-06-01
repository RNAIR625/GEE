// Global variables for storing data
let allRules = [];
let allFunctions = [];
let allClasses = [];
let allChildClasses = [];
let classFields = [];
let currentRuleLines = { conditions: [], actions: [] };
let currentEditingLine = null;
let ruleLineModal = null;

// Initialize the page when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap modals
    const ruleModal = document.getElementById('ruleModal');
    if (ruleModal) {
        const ruleModalInstance = new bootstrap.Modal(ruleModal);
        
        // Add event listener for when modal is fully hidden
        ruleModal.addEventListener('hidden.bs.modal', function() {
            console.log('Rule modal hidden, refreshing rules...');
            // Small delay to ensure any ongoing operations complete
            setTimeout(loadRules, 100);
        });
    }
    
    const ruleLineModalElement = document.getElementById('ruleLineModal');
    if (ruleLineModalElement) {
        // Use getOrCreateInstance to ensure we don't create duplicate instances
        ruleLineModal = bootstrap.Modal.getOrCreateInstance(ruleLineModalElement);
        console.log('Rule line modal initialized:', ruleLineModal);
    } else {
        console.error('ruleLineModal element not found in DOM');
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
        const deleteModalInstance = new bootstrap.Modal(deleteModal);
        
        // Add event listener for when delete modal is fully hidden
        deleteModal.addEventListener('hidden.bs.modal', function() {
            console.log('Delete modal hidden, refreshing rules...');
            // Small delay to ensure any ongoing operations complete
            setTimeout(loadRules, 100);
        });
    }
    
    // Code editor mode removed - only structured mode available
    
    // Structured mode is always active (code editor mode removed)
    
    // Set up event listeners for buttons
    const saveRuleBtn = document.getElementById('saveRuleBtn');
    if (saveRuleBtn) {
        saveRuleBtn.addEventListener('click', saveRule);
    }
    
    const saveLineBtn = document.getElementById('saveLineBtn');
    if (saveLineBtn) {
        saveLineBtn.addEventListener('click', saveRuleLine);
    }
    
    // Function and field selector buttons removed (code editor mode deprecated)
    
    // Code editor button functionality removed (structured mode only)
    
    // Function select change handler
    const functionSelect = document.getElementById('functionSelect');
    if (functionSelect) {
        functionSelect.addEventListener('change', () => handleFunctionSelection());
    }
    
    // Rule class change handler
    const ruleClassSelect = document.getElementById('ruleClass');
    if (ruleClassSelect) {
        ruleClassSelect.addEventListener('change', function() {
            const selectedClassId = this.value;
            if (selectedClassId) {
                loadChildClassesForParent(selectedClassId).then(() => {
                    loadFieldsForClass(selectedClassId).then(() => {
                        // Refresh any open parameter dropdowns
                        refreshParameterFieldDropdowns();
                    });
                });
            } else {
                allChildClasses = [];
                classFields = [];
                refreshParameterFieldDropdowns();
            }
        });
    }
    
    // Load initial data
    loadRules();
    loadClasses();
    loadFunctions();
});

// Load all rules
function loadRules() {
    console.log('Loading rules...');
    return fetch('/rules/get_rules')
        .then(response => {
            console.log('Rules response status:', response.status);
            return response.json();
        })
        .then(data => {
            console.log('Rules data received:', data.length, 'rules');
            allRules = data;
            renderRules(data);
            return data;
        })
        .catch(error => {
            console.error('Error loading rules:', error);
            showToast('Error', 'Failed to load rules', 'error');
            throw error;
        });
}

// Force refresh rules list (for debugging/manual refresh)
function forceRefreshRules() {
    console.log('Force refreshing rules...');
    loadRules().then(() => {
        console.log('Rules force refresh completed');
    }).catch(error => {
        console.error('Force refresh failed:', error);
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
        
        // Add options for each class - filter to show only parent classes
        classes.filter(cls => !cls.PARENT_GFC_ID).forEach(cls => {
            const option = document.createElement('option');
            option.value = cls.GFC_ID;
            option.textContent = cls.FIELD_CLASS_NAME;
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
        
        // Add options for each class - filter to show only parent classes
        classes.filter(cls => !cls.PARENT_GFC_ID).forEach(cls => {
            const option = document.createElement('option');
            option.value = cls.GFC_ID;
            option.textContent = cls.FIELD_CLASS_NAME;
            ruleClassDropdown.appendChild(option);
        });
    }
}

// Load child classes for a parent class
function loadChildClassesForParent(parentClassId) {
    if (!parentClassId) {
        allChildClasses = [];
        return Promise.resolve([]);
    }
    
    return fetch(`/fields/get_child_classes/${parentClassId}`)
        .then(response => response.json())
        .then(data => {
            allChildClasses = data;
            return data;
        })
        .catch(error => {
            console.error('Error loading child classes:', error);
            showToast('Error', 'Failed to load child classes for the selected parent class', 'error');
            return [];
        });
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
    console.log('Rendering rules:', rules ? rules.length : 0, 'rules');
    const ruleList = document.getElementById('ruleList');
    const noRulesMessage = document.getElementById('noRulesMessage');
    
    if (!ruleList) {
        console.error('ruleList element not found');
        return;
    }
    
    // Clear the current content
    ruleList.innerHTML = '';
    
    if (!rules || rules.length === 0) {
        console.log('No rules to display');
        if (noRulesMessage) {
            noRulesMessage.style.display = 'block';
        }
        // Update rule count
        const ruleCount = document.getElementById('ruleCount');
        if (ruleCount) {
            ruleCount.textContent = '0 rules';
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
                className = cls.FIELD_CLASS_NAME;
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
    
    // Reset rule lines completely
    currentRuleLines = { conditions: [], actions: [] };
    
    // Reset any global state variables
    currentEditingLine = null;
    allChildClasses = [];
    classFields = [];
    
    // Show structured mode (only mode available)
    document.getElementById('structuredMode').classList.remove('d-none');
    
    // Clear and render empty rule lines
    renderRuleLines();
    
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
    
    // Set modal title
    document.getElementById('modalTitle').textContent = 'Edit Rule';
    
    // Show structured mode (only mode available)
    document.getElementById('structuredMode').classList.remove('d-none');
    
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
    
    // Get condition and action code from structured mode (only mode available)
    let conditionCode = '';
    let actionCode = '';
    
    // Generate code from structured lines
    const generatedCode = generateCodeFromLines();
    conditionCode = generatedCode.conditionCode || '';
    actionCode = generatedCode.actionCode || '';
    
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
        
        // Hide the modal (refresh will happen via modal event listener)
        const modal = bootstrap.Modal.getInstance(document.getElementById('ruleModal'));
        if (modal) {
            modal.hide();
        }
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
    console.log('Deleting rule with ID:', ruleId);
    
    fetch(`/rules/delete_rule/${ruleId}`, {
        method: 'DELETE'
    })
    .then(response => {
        console.log('Delete response status:', response.status);
        return response.json();
    })
    .then(result => {
        console.log('Delete result:', result);
        if (result.success) {
            showToast('Success', result.message || 'Rule deleted successfully');
            
            // Hide the modal (refresh will happen via modal event listener)
            const modal = bootstrap.Modal.getInstance(document.getElementById('deleteModal'));
            if (modal) {
                modal.hide();
            }
        } else {
            throw new Error(result.message || 'Unknown error occurred');
        }
    })
    .catch(error => {
        console.error('Error deleting rule:', error);
        showToast('Error', error.message || 'Failed to delete rule', 'error');
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
    
    // Code editor functionality removed - structured mode only
    showToast('Error', 'Function insertion is only available in structured mode', 'error');
    return;
    
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
    
    // Code editor functionality removed - structured mode only
    showToast('Error', 'Field insertion is only available in structured mode', 'error');
    return;
    
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
    // Code editor functionality removed - structured mode only
    showToast('Error', 'Code testing is only available in structured mode', 'error');
    return;
    
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

// Code editor mode removed - only structured mode available
function toggleRuleCreationMode() {
    // Structured mode is the only available mode
    document.getElementById('structuredMode').classList.remove('d-none');
    renderRuleLines();
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
    
    // Return the generated codes instead of setting them in editors
    return {
        conditionCode: conditionCode,
        actionCode: actionCode
    };
}

// Add a new rule line
function addRuleLine(isCondition) {
    try {
        console.log('addRuleLine called with isCondition:', isCondition);
        console.log('ruleLineModal object:', ruleLineModal);
        
        // Check if modal exists
        if (!ruleLineModal) {
            console.error('ruleLineModal is not initialized');
            alert('Error: Modal not initialized. Please refresh the page.');
            return;
        }
        
        // Double check the modal element exists
        const modalElement = document.getElementById('ruleLineModal');
        if (!modalElement) {
            console.error('ruleLineModal element not found in DOM');
            alert('Error: Modal element not found. Please refresh the page.');
            return;
        }
        
        console.log('Modal element found:', modalElement);
        
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
        
        // Load fields for the currently selected class
        const selectedClassId = document.getElementById('ruleClass').value;
        if (selectedClassId && classFields.length === 0) {
            loadFieldsForClass(selectedClassId);
        }
        
        // Clear and hide parameter containers
        const formulaContainer = document.getElementById('functionFormulaContainer');
        const inputContainer = document.getElementById('inputParametersContainer');
        const outputContainer = document.getElementById('outputParametersContainer');
        const noParamsMessage = document.getElementById('noParametersMessage');
        
        if (formulaContainer) formulaContainer.classList.add('d-none');
        if (inputContainer) inputContainer.classList.add('d-none');
        if (outputContainer) outputContainer.classList.add('d-none');
        if (noParamsMessage) noParamsMessage.style.display = 'block';
        
        // Show the modal
        console.log('Showing modal...');
        try {
            ruleLineModal.show();
        } catch (error) {
            console.error('Error showing modal with stored instance:', error);
            // Fallback: try to get a fresh instance
            try {
                const freshModal = bootstrap.Modal.getOrCreateInstance(modalElement);
                freshModal.show();
                ruleLineModal = freshModal; // Update the stored instance
            } catch (fallbackError) {
                console.error('Fallback modal show also failed:', fallbackError);
                alert('Error opening modal. Please refresh the page.');
            }
        }
        
    } catch (error) {
        console.error('Error in addRuleLine:', error);
        alert('Error opening rule line modal: ' + error.message);
    }
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
    
    // IMPORTANT FIX: Format existing parameters properly for the parameter generation
    const formattedExistingParams = {};
    if (line.parameters && line.parameters.length > 0) {
        line.parameters.forEach((param, index) => {
            // For now, assume all are input parameters. This might need refinement based on function definition
            formattedExistingParams[`input_${index}`] = param;
        });
    }
    
    // Pass the existing parameters to the handleFunctionSelection function
    handleFunctionSelection(formattedExistingParams);
    
    // Show the modal
    ruleLineModal.show();
}

// Handle function selection in rule line modal
function handleFunctionSelection(existingParams = null) {
    const functionId = document.getElementById('functionSelect').value;
    
    // Hide all sections initially
    document.getElementById('functionFormulaContainer').classList.add('d-none');
    document.getElementById('inputParametersContainer').classList.add('d-none');
    document.getElementById('outputParametersContainer').classList.add('d-none');
    document.getElementById('noParametersMessage').style.display = 'block';
    
    if (!functionId) {
        return;
    }
    
    // Find the selected function
    const func = allFunctions.find(f => f.GBF_ID == functionId || f.FUNC_ID == functionId);
    
    if (!func) {
        console.error('Function not found with ID:', functionId);
        showToast('Error', 'Function not found', 'error');
        return;
    }
    
    const paramCount = func.PARAM_COUNT || 0;
    console.log(`Function ${func.FUNC_NAME || func.name} has ${paramCount} parameters`);
    
    // Hide the "no parameters" message
    document.getElementById('noParametersMessage').style.display = 'none';
    
    if (paramCount === 0) {
        // Show just the function formula for functions with no parameters
        showFunctionFormula(func.FUNC_NAME, [], []);
        return;
    }
    
    // Fetch function parameters from the server
    fetch(`/functions/get_function_parameters/${functionId}`)
        .then(response => response.json())
        .then(funcParams => {
            generateInputOutputParameterSections(func, funcParams, existingParams);
        })
        .catch(error => {
            console.error('Error loading function parameters:', error);
            // Fallback to generic parameter names
            const genericParams = [];
            for (let i = 0; i < paramCount; i++) {
                genericParams.push({
                    PARAM_NAME: `Parameter ${i + 1}`,
                    PARAM_TYPE: 'VARCHAR',
                    PARAM_IO_TYPE: 'INPUT',
                    GBF_SEQ: i + 1
                });
            }
            generateInputOutputParameterSections(func, genericParams, existingParams);
        });
}

// Generate parameter input fields
function generateParameterInputs(funcParams, existingParams = null) {
    const parametersContainer = document.getElementById('parametersContainer');
    
    if (!funcParams || funcParams.length === 0) {
        parametersContainer.innerHTML = `
            <div class="alert alert-info">
                This function has no parameters.
            </div>
        `;
        return;
    }
    
    // Sort parameters by sequence
    funcParams.sort((a, b) => (a.GBF_SEQ || 0) - (b.GBF_SEQ || 0));
    
    // Create input fields for each parameter
    funcParams.forEach((param, index) => {
        const paramName = param.PARAM_NAME || `Parameter ${index + 1}`;
        const paramType = param.PARAM_TYPE || 'VARCHAR';
        const paramDescription = param.DESCRIPTION || '';
        
        // Check if we have existing parameter values
        let existingParam = null;
        if (existingParams && existingParams[index]) {
            existingParam = existingParams[index];
        }
        
        // Determine default selection and visibility
        let defaultSelection = '';
        let fieldSelectorClass = 'd-none';
        let literalValueClass = 'd-none';
        
        if (existingParam) {
            if (existingParam.fieldId) {
                defaultSelection = 'field';
                fieldSelectorClass = '';
            } else if (existingParam.literalValue !== undefined && existingParam.literalValue !== null) {
                defaultSelection = 'literal';
                literalValueClass = '';
            }
        }
        
        // Create parameter group
        const paramGroup = document.createElement('div');
        paramGroup.className = 'mb-3 parameter-group';
        paramGroup.setAttribute('data-param-index', index);
        
        // Create parameter label and controls
        paramGroup.innerHTML = `
            <label class="form-label">
                ${paramName} 
                <span class="text-muted">(${paramType})</span>
                ${paramDescription ? `<small class="form-text text-muted d-block">${paramDescription}</small>` : ''}
            </label>
            <div class="input-group">
                <select class="form-select param-source" data-param-index="${index}" onchange="toggleParameterValueType(this)">
                    <option value="">Select...</option>
                    <option value="field" ${defaultSelection === 'field' ? 'selected' : ''}>Field</option>
                    <option value="literal" ${defaultSelection === 'literal' ? 'selected' : ''}>Literal Value</option>
                </select>
                <div class="field-selector ${fieldSelectorClass}">
                    <select class="form-select param-field" data-param-index="${index}">
                        <option value="">Select Field</option>
                    </select>
                </div>
                <div class="literal-value ${literalValueClass}">
                    <input type="text" class="form-control param-literal" data-param-index="${index}" 
                        placeholder="Enter ${paramType.toLowerCase()} value"
                        value="${existingParam && existingParam.literalValue !== undefined ? existingParam.literalValue : ''}">
                </div>
            </div>
        `;
        
        parametersContainer.appendChild(paramGroup);
        
        // Populate field dropdown for this parameter if field mode is selected
        if (defaultSelection === 'field') {
            const fieldDropdown = paramGroup.querySelector('.param-field');
            if (fieldDropdown) {
                populateFieldDropdown(fieldDropdown);
                
                // Set the selected value if we have existing parameter data
                if (existingParam && existingParam.fieldId) {
                    fieldDropdown.value = existingParam.fieldId;
                }
            }
        }
    });
}

// Show function formula in the format: output = function(input_params)
function showFunctionFormula(functionName, inputParams, outputParams) {
    const formulaContainer = document.getElementById('functionFormulaContainer');
    const formulaElement = document.getElementById('functionFormula');
    
    // Build the formula
    let formula = '';
    
    // Output side
    if (outputParams && outputParams.length > 0) {
        const outputNames = outputParams.map(p => p.PARAM_NAME || 'output');
        formula += outputNames.join(', ') + ' = ';
    } else {
        formula += 'result = ';
    }
    
    // Function name and input parameters
    formula += functionName + '(';
    if (inputParams && inputParams.length > 0) {
        const inputNames = inputParams.map(p => p.PARAM_NAME || 'input');
        formula += inputNames.join(', ');
    }
    formula += ')';
    
    formulaElement.textContent = formula;
    formulaContainer.classList.remove('d-none');
}

// Generate input/output parameter sections
function generateInputOutputParameterSections(func, funcParams, existingParams = null) {
    if (!funcParams || funcParams.length === 0) {
        showFunctionFormula(func.FUNC_NAME, [], []);
        return;
    }
    
    // Sort parameters by sequence
    funcParams.sort((a, b) => (a.GBF_SEQ || 0) - (b.GBF_SEQ || 0));
    
    // Separate input and output parameters
    const inputParams = funcParams.filter(p => (p.PARAM_IO_TYPE || 'INPUT') === 'INPUT');
    const outputParams = funcParams.filter(p => (p.PARAM_IO_TYPE || 'INPUT') === 'OUTPUT');
    
    // Show function formula
    showFunctionFormula(func.FUNC_NAME, inputParams, outputParams);
    
    // Generate input parameters section
    if (inputParams.length > 0) {
        generateParameterSection('input', inputParams, existingParams);
    }
    
    // Generate output parameters section
    if (outputParams.length > 0) {
        generateParameterSection('output', outputParams, existingParams);
    }
}

// Generate parameter section (input or output)
function generateParameterSection(type, params, existingParams = null) {
    const isInput = type === 'input';
    const containerElement = document.getElementById(isInput ? 'inputParametersContainer' : 'outputParametersContainer');
    const listElement = document.getElementById(isInput ? 'inputParametersList' : 'outputParametersList');
    
    // Clear previous content
    listElement.innerHTML = '';
    
    params.forEach((param, index) => {
        const paramName = param.PARAM_NAME || `Parameter ${index + 1}`;
        const paramType = param.PARAM_TYPE || 'VARCHAR';
        const paramDescription = param.DESCRIPTION || '';
        const paramIndex = `${type}_${index}`;
        
        // Check for existing parameter values
        let existingParam = null;
        if (existingParams && existingParams[paramIndex]) {
            existingParam = existingParams[paramIndex];
        }
        
        // Determine default selection and visibility
        let defaultSelection = '';
        let fieldSelectorClass = 'd-none';
        let literalValueClass = 'd-none';
        
        if (existingParam) {
            if (existingParam.fieldId) {
                defaultSelection = 'field';
                fieldSelectorClass = '';
            } else if (existingParam.literalValue !== undefined && existingParam.literalValue !== null) {
                defaultSelection = 'literal';
                literalValueClass = '';
            }
        }
        
        // Create parameter group
        const paramGroup = document.createElement('div');
        paramGroup.className = 'mb-3 parameter-group';
        paramGroup.setAttribute('data-param-index', paramIndex);
        paramGroup.setAttribute('data-param-type', type);
        
        // Different UI for input vs output parameters
        if (isInput) {
            // Input parameters: user selects field or literal value
            paramGroup.innerHTML = `
                <label class="form-label">
                    ${paramName} 
                    <span class="text-muted">(${paramType})</span>
                    ${paramDescription ? `<small class="form-text text-muted d-block">${paramDescription}</small>` : ''}
                </label>
                <div class="row">
                    <div class="col-md-4">
                        <select class="form-select param-source" data-param-index="${paramIndex}" onchange="toggleParameterValueType(this)">
                            <option value="">Select Source...</option>
                            <option value="field" ${defaultSelection === 'field' ? 'selected' : ''}>Field Value</option>
                            <option value="literal" ${defaultSelection === 'literal' ? 'selected' : ''}>Literal Value</option>
                        </select>
                    </div>
                    <div class="col-md-8">
                        <div class="field-selector ${fieldSelectorClass}">
                            <div class="row">
                                <div class="col-md-6">
                                    <select class="form-select param-child-class mb-2" data-param-index="${paramIndex}" onchange="onChildClassChange(this)">
                                        <option value="">Select Child Class</option>
                                    </select>
                                </div>
                                <div class="col-md-6">
                                    <select class="form-select param-field" data-param-index="${paramIndex}">
                                        <option value="">Select Field</option>
                                    </select>
                                </div>
                            </div>
                        </div>
                        <div class="literal-value ${literalValueClass}">
                            <input type="text" class="form-control param-literal" data-param-index="${paramIndex}" 
                                   placeholder="Enter ${paramType.toLowerCase()} value" 
                                   value="${existingParam && existingParam.literalValue ? existingParam.literalValue : ''}">
                        </div>
                    </div>
                </div>
            `;
        } else {
            // Output parameters: user selects target field
            paramGroup.innerHTML = `
                <label class="form-label">
                    ${paramName} → Target Field
                    <span class="text-muted">(${paramType})</span>
                    ${paramDescription ? `<small class="form-text text-muted d-block">${paramDescription}</small>` : ''}
                </label>
                <div class="row">
                    <div class="col-md-6">
                        <select class="form-select param-child-class mb-2" data-param-index="${paramIndex}" onchange="onChildClassChange(this)">
                            <option value="">Select Child Class</option>
                        </select>
                    </div>
                    <div class="col-md-6">
                        <select class="form-select param-field" data-param-index="${paramIndex}">
                            <option value="">Select Target Field</option>
                        </select>
                    </div>
                </div>
            `;
        }
        
        listElement.appendChild(paramGroup);
        
        // If this parameter has an existing field selection, we need to load the child class data
        if (existingParam && existingParam.fieldId && isInput && defaultSelection === 'field') {
            // Find the field and load its parent class
            const childClassDropdown = paramGroup.querySelector('.param-child-class');
            const fieldDropdown = paramGroup.querySelector('.param-field');
            
            if (childClassDropdown && fieldDropdown && existingParam.fieldId) {
                // Load field details to determine which child class it belongs to
                fetch(`/fields/get_fields`)
                    .then(response => response.json())
                    .then(allFields => {
                        const existingField = allFields.find(f => f.GF_ID == existingParam.fieldId);
                        if (existingField) {
                            // Populate child class dropdown with the field's class
                            populateChildClassDropdown(childClassDropdown);
                            
                            // Set the child class value if it's different from parent
                            if (existingField.GFC_ID) {
                                childClassDropdown.value = existingField.GFC_ID;
                                
                                // Load fields for this class and set the field value
                                fetch(`/fields/get_fields_by_class/${existingField.GFC_ID}`)
                                    .then(response => response.json())
                                    .then(fields => {
                                        fieldDropdown.innerHTML = '<option value="">Select Field</option>';
                                        fields.forEach(field => {
                                            const option = document.createElement('option');
                                            option.value = field.GF_ID;
                                            option.textContent = field.GF_NAME;
                                            option.setAttribute('data-type', field.GF_TYPE);
                                            if (field.GF_ID == existingParam.fieldId) {
                                                option.selected = true;
                                            }
                                            fieldDropdown.appendChild(option);
                                        });
                                    });
                            }
                        }
                    })
                    .catch(error => {
                        console.error('Error loading field details for existing parameter:', error);
                    });
            }
        } else if (existingParam && existingParam.fieldId && !isInput) {
            // For output parameters, just populate normally
            const fieldDropdown = paramGroup.querySelector('.param-field');
            if (fieldDropdown) {
                populateFieldDropdown(fieldDropdown);
                fieldDropdown.value = existingParam.fieldId;
            }
        }
    });
    
    // Show the container
    containerElement.classList.remove('d-none');
    
    // Populate child class and field dropdowns for parameters without existing values
    refreshParameterChildClassDropdowns();
    refreshParameterFieldDropdowns();
}

// Toggle between field and literal value for parameters
function toggleParameterValueType(selectElement) {
    const paramIndex = selectElement.getAttribute('data-param-index');
    const paramGroup = selectElement.closest('.parameter-group');
    const fieldSelector = paramGroup.querySelector('.field-selector');
    const literalValue = paramGroup.querySelector('.literal-value');
    
    const selectedValue = selectElement.value;
    
    // Hide both initially
    fieldSelector.classList.add('d-none');
    literalValue.classList.add('d-none');
    
    if (selectedValue === 'field') {
        fieldSelector.classList.remove('d-none');
        
        // If switching to field mode, ensure both child class and field dropdowns are populated
        const childClassDropdown = paramGroup.querySelector('.param-child-class');
        const fieldDropdown = paramGroup.querySelector('.param-field');
        if (childClassDropdown) {
            populateChildClassDropdown(childClassDropdown);
        }
        if (fieldDropdown) {
            populateFieldDropdown(fieldDropdown);
        }
    } else if (selectedValue === 'literal') {
        literalValue.classList.remove('d-none');
        
        // Focus on the literal input
        const literalInput = paramGroup.querySelector('.param-literal');
        if (literalInput) {
            setTimeout(() => literalInput.focus(), 100);
        }
    }
    // If selectedValue is empty ("Select..."), both remain hidden
}

// Refresh all parameter child class dropdowns
function refreshParameterChildClassDropdowns() {
    const paramChildClassDropdowns = document.querySelectorAll('.param-child-class');
    paramChildClassDropdowns.forEach(dropdown => {
        populateChildClassDropdown(dropdown);
    });
}

// Refresh all parameter field dropdowns with current classFields
function refreshParameterFieldDropdowns() {
    const paramFieldDropdowns = document.querySelectorAll('.param-field');
    paramFieldDropdowns.forEach(dropdown => {
        populateFieldDropdown(dropdown);
    });
}

// Populate a single child class dropdown
function populateChildClassDropdown(dropdown) {
    if (!dropdown) return;
    
    const currentValue = dropdown.value;
    dropdown.innerHTML = '<option value="">Select Child Class</option>';
    
    // Add parent class as an option if no child classes exist
    const selectedParentClassId = document.getElementById('ruleClass').value;
    if (selectedParentClassId && allChildClasses.length === 0) {
        const parentClass = allClasses.find(cls => cls.GFC_ID == selectedParentClassId);
        if (parentClass) {
            const option = document.createElement('option');
            option.value = parentClass.GFC_ID;
            option.textContent = `${parentClass.FIELD_CLASS_NAME} (Parent)`;
            if (parentClass.GFC_ID == currentValue) {
                option.selected = true;
            }
            dropdown.appendChild(option);
        }
    }
    
    // Add child classes
    allChildClasses.forEach(childClass => {
        const option = document.createElement('option');
        option.value = childClass.GFC_ID;
        option.textContent = childClass.FIELD_CLASS_NAME;
        if (childClass.GFC_ID == currentValue) {
            option.selected = true;
        }
        dropdown.appendChild(option);
    });
}

// Handle child class change - load fields for selected child class
function onChildClassChange(selectElement) {
    const selectedChildClassId = selectElement.value;
    const paramIndex = selectElement.getAttribute('data-param-index');
    
    // Find the corresponding field dropdown
    const paramGroup = selectElement.closest('.parameter-group');
    const fieldDropdown = paramGroup.querySelector('.param-field');
    
    if (selectedChildClassId) {
        // Load fields for the selected child class
        fetch(`/fields/get_fields_by_class/${selectedChildClassId}`)
            .then(response => response.json())
            .then(fields => {
                // Clear and populate the field dropdown
                fieldDropdown.innerHTML = '<option value="">Select Field</option>';
                fields.forEach(field => {
                    const option = document.createElement('option');
                    option.value = field.GF_ID;
                    option.textContent = field.GF_NAME;
                    option.setAttribute('data-type', field.GF_TYPE);
                    fieldDropdown.appendChild(option);
                });
            })
            .catch(error => {
                console.error('Error loading fields for child class:', error);
                showToast('Error', 'Failed to load fields for the selected child class', 'error');
            });
    } else {
        // Clear the field dropdown if no child class is selected
        fieldDropdown.innerHTML = '<option value="">Select Field</option>';
    }
}

// Populate a single field dropdown
function populateFieldDropdown(dropdown) {
    if (!dropdown) return;
    
    const currentValue = dropdown.value;
    dropdown.innerHTML = '<option value="">Select Field</option>';
    
    classFields.forEach(field => {
        const option = document.createElement('option');
        option.value = field.GF_ID;
        option.textContent = field.GF_NAME;
        option.setAttribute('data-type', field.GF_TYPE);
        if (field.GF_ID == currentValue) {
            option.selected = true;
        }
        dropdown.appendChild(option);
    });
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
    
    // Collect parameters from both input and output sections
    const parameters = [];
    
    // Get all parameter groups (both input and output)
    const paramGroups = document.querySelectorAll('.parameter-group');
    
    paramGroups.forEach((paramGroup, index) => {
        const paramIndex = paramGroup.getAttribute('data-param-index');
        const paramType = paramGroup.getAttribute('data-param-type');
        
        if (paramType === 'input') {
            // Input parameters can be field or literal
            const paramSource = paramGroup.querySelector('.param-source');
            if (paramSource && paramSource.value === 'field') {
                const fieldSelect = paramGroup.querySelector('.param-field');
                const fieldId = fieldSelect ? fieldSelect.value : null;
                if (fieldId) {
                    // Try to find field in classFields first
                    let field = classFields.find(f => f.GF_ID == fieldId);
                    
                    // If not found, get the field name and type from the select option
                    if (!field && fieldSelect.selectedOptions.length > 0) {
                        const selectedOption = fieldSelect.selectedOptions[0];
                        field = {
                            GF_ID: fieldId,
                            GF_NAME: selectedOption.textContent,
                            GF_TYPE: selectedOption.getAttribute('data-type') || 'VARCHAR'
                        };
                    }
                    
                    parameters.push({
                        index: parameters.length,
                        fieldId: parseInt(fieldId),
                        fieldName: field ? field.GF_NAME : '',
                        fieldType: field ? field.GF_TYPE : 'VARCHAR',
                        literalValue: null
                    });
                } else {
                    parameters.push({
                        index: parameters.length,
                        fieldId: null,
                        fieldName: '',
                        fieldType: '',
                        literalValue: null
                    });
                }
            } else if (paramSource && paramSource.value === 'literal') {
                const literalInput = paramGroup.querySelector('.param-literal');
                const literalValue = literalInput ? literalInput.value : '';
                parameters.push({
                    index: parameters.length,
                    fieldId: null,
                    fieldName: '',
                    fieldType: '',
                    literalValue: literalValue
                });
            } else {
                // No source selected
                parameters.push({
                    index: parameters.length,
                    fieldId: null,
                    fieldName: '',
                    fieldType: '',
                    literalValue: null
                });
            }
        } else if (paramType === 'output') {
            // Output parameters are always field assignments
            const fieldSelect = paramGroup.querySelector('.param-field');
            const fieldId = fieldSelect ? fieldSelect.value : null;
            if (fieldId) {
                // Try to find field in classFields first
                let field = classFields.find(f => f.GF_ID == fieldId);
                
                // If not found, get the field name and type from the select option
                if (!field && fieldSelect.selectedOptions.length > 0) {
                    const selectedOption = fieldSelect.selectedOptions[0];
                    field = {
                        GF_ID: fieldId,
                        GF_NAME: selectedOption.textContent,
                        GF_TYPE: selectedOption.getAttribute('data-type') || 'VARCHAR'
                    };
                }
                
                parameters.push({
                    index: parameters.length,
                    fieldId: parseInt(fieldId),
                    fieldName: field ? field.GF_NAME : '',
                    fieldType: field ? field.GF_TYPE : 'VARCHAR',
                    literalValue: null
                });
            } else {
                parameters.push({
                    index: parameters.length,
                    fieldId: null,
                    fieldName: '',
                    fieldType: '',
                    literalValue: null
                });
            }
        }
    });
    
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
    
    // Code editor mode removed - only structured mode available
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
                    
                    // Code editor mode removed - only structured mode available
                    
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
            
            // Code editor mode removed - only structured mode available
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

// Bulk Delete Functions for Rules
function toggleAllRules(selectAllCheckbox) {
    const checkboxes = document.querySelectorAll('.rule-checkbox');
    checkboxes.forEach(checkbox => {
        checkbox.checked = selectAllCheckbox.checked;
    });
    updateBulkDeleteRulesButton();
}

function updateBulkDeleteRulesButton() {
    const selectedCheckboxes = document.querySelectorAll('.rule-checkbox:checked');
    const bulkDeleteBtn = document.getElementById('bulkDeleteRulesBtn');
    const selectAllCheckbox = document.getElementById('selectAllRules');
    
    if (selectedCheckboxes.length > 0) {
        bulkDeleteBtn.style.display = 'inline-block';
        bulkDeleteBtn.innerHTML = `<i class="fas fa-trash me-2"></i>Delete Selected (${selectedCheckboxes.length})`;
    } else {
        bulkDeleteBtn.style.display = 'none';
    }

    // Update select all checkbox state
    const allCheckboxes = document.querySelectorAll('.rule-checkbox');
    if (selectedCheckboxes.length === allCheckboxes.length) {
        selectAllCheckbox.checked = true;
        selectAllCheckbox.indeterminate = false;
    } else if (selectedCheckboxes.length > 0) {
        selectAllCheckbox.checked = false;
        selectAllCheckbox.indeterminate = true;
    } else {
        selectAllCheckbox.checked = false;
        selectAllCheckbox.indeterminate = false;
    }
}

function bulkDeleteRules() {
    const selectedCheckboxes = document.querySelectorAll('.rule-checkbox:checked');
    if (selectedCheckboxes.length === 0) {
        alert('Please select rules to delete');
        return;
    }

    const selectedIds = Array.from(selectedCheckboxes).map(cb => cb.value);
    const confirmMessage = `Are you sure you want to delete ${selectedIds.length} selected rule(s)? This will also delete all associated rule lines and parameters. This action cannot be undone.`;
    
    if (confirm(confirmMessage)) {
        fetch('/rules/bulk_delete_rules', {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                rule_ids: selectedIds
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                loadRules();
                document.getElementById('selectAllRules').checked = false;
                updateBulkDeleteRulesButton();
                showToast('Success', `Successfully deleted ${data.deleted_count} rule(s). ${data.skipped_count > 0 ? data.skipped_count + ' rules were skipped due to dependencies.' : ''}`);
            } else {
                showToast('Error', data.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showToast('Error', 'Error during bulk delete operation', 'error');
        });
    }
}