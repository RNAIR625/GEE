// Global variables for function management
let currentFunctionId = null;
let deleteType = ''; // 'function' or 'parameter'
let deleteId = null;
let allFunctions = [];
let functionParameters = {};
let currentFunctionPage = 1;
let currentFunctionSearch = '';

// Modal instances
let functionModal = null;
let parameterModal = null;
let deleteModal = null;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap modals
    const functionModalElement = document.getElementById('functionModal');
    if (functionModalElement) {
        functionModal = new bootstrap.Modal(functionModalElement);
    }
    
    const parameterModalElement = document.getElementById('parameterModal');
    if (parameterModalElement) {
        parameterModal = new bootstrap.Modal(parameterModalElement);
    }
    
    const deleteModalElement = document.getElementById('deleteModal');
    if (deleteModalElement) {
        deleteModal = new bootstrap.Modal(deleteModalElement);
    }
    
    // Initialize page
    loadFunctions();
    
    // Hide parameters section until a function is selected
    const parametersContainer = document.getElementById('parametersContainer');
    if (parametersContainer) {
        parametersContainer.style.display = 'none';
    }
    
    // Set up delete confirmation handler
    const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener('click', function() {
            if (deleteType === 'function') {
                deleteFunction(deleteId);
            } else if (deleteType === 'parameter') {
                deleteParameter(deleteId);
            }
        });
    }
});

// ======================================
// FUNCTION MANAGEMENT
// ======================================

// Load all functions
function loadFunctions() {
    fetch('/functions/get_functions')
        .then(response => response.json())
        .then(data => {
            allFunctions = data;
            updateFunctionsList();
            updateSummaryData();
        })
        .catch(error => {
            console.error('Error loading functions:', error);
            showToast('Error', 'Failed to load functions', 'error');
            allFunctions = [];
            updateFunctionsList();
            updateSummaryData();
        });
}

// Update summary statistics
function updateSummaryData() {
    // Update function count
    const functionCountElement = document.getElementById('functionCount');
    if (functionCountElement) {
        functionCountElement.textContent = allFunctions.length || 0;
    }
    
    // Calculate total parameter count
    let totalParams = 0;
    allFunctions.forEach(func => {
        totalParams += func.PARAM_COUNT || 0;
    });
    
    const parameterCountElement = document.getElementById('parameterCount');
    if (parameterCountElement) {
        parameterCountElement.textContent = totalParams;
    }
}

// Update functions list table
function updateFunctionsList() {
    const tableBody = document.getElementById('functionTableBody');
    if (!tableBody) return;
    
    tableBody.innerHTML = '';
    
    // If no functions, show placeholder
    if (allFunctions.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="3" class="text-center py-4">
                    <div class="text-muted">
                        <i class="fas fa-info-circle me-2"></i>
                        No functions found. Create your first function to get started.
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    // Populate table view
    allFunctions.forEach(func => {
        const row = `
            <tr data-id="${func.GBF_ID}" class="function-item ${currentFunctionId === func.GBF_ID ? 'selected-function' : ''}">
                <td>
                    <a href="javascript:void(0)" onclick="viewParameters(${func.GBF_ID}, '${func.FUNC_NAME}')" class="text-decoration-none text-dark">
                        <div><strong>${func.FUNC_NAME}</strong></div>
                        <small class="text-muted">${func.DESCRIPTION || 'No description'}</small>
                    </a>
                </td>
                <td>
                    <span class="badge bg-secondary">${func.PARAM_COUNT || 0}</span>
                </td>
                <td>
                    <div class="function-actions">
                        <button class="btn btn-warning btn-sm" onclick="editFunction(${func.GBF_ID})">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-danger btn-sm" onclick="confirmDeleteFunction(${func.GBF_ID}, '${func.FUNC_NAME}')">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
        tableBody.innerHTML += row;
    });
}

// Open modal for creating new function
function openNewFunctionModal() {
    const modalTitle = document.getElementById('functionModalTitle');
    const functionForm = document.getElementById('functionForm');
    const gbfIdField = document.getElementById('gbfId');
    
    if (modalTitle) modalTitle.textContent = 'Add New Function';
    if (functionForm) functionForm.reset();
    if (gbfIdField) gbfIdField.value = '';
    
    if (functionModal) functionModal.show();
}

// Open modal for editing existing function
function editFunction(gbfId) {
    const func = allFunctions.find(f => f.GBF_ID === gbfId);
    
    if (func) {
        const modalTitle = document.getElementById('functionModalTitle');
        const gbfIdField = document.getElementById('gbfId');
        const funcNameField = document.getElementById('funcName');
        const funcDescField = document.getElementById('funcDescription');
        
        if (modalTitle) modalTitle.textContent = 'Edit Function';
        if (gbfIdField) gbfIdField.value = gbfId;
        if (funcNameField) funcNameField.value = func.FUNC_NAME;
        if (funcDescField) funcDescField.value = func.DESCRIPTION || '';
        
        if (functionModal) functionModal.show();
    } else {
        showToast('Error', 'Function not found', 'error');
    }
}

// Save function (create or update)
function saveFunction() {
    const gbfId = document.getElementById('gbfId').value;
    const funcName = document.getElementById('funcName').value;
    const description = document.getElementById('funcDescription').value;

    if (!funcName) {
        showToast('Error', 'Function Name is required!', 'error');
        return;
    }

    const data = {
        functionName: funcName,
        description: description,
        paramCount: 0, // Will be updated when parameters are added
        returnType: 'void' // Default return type
    };

    const method = gbfId ? 'PUT' : 'POST';
    const url = gbfId ? '/functions/update_function' : '/functions/add_function';
    
    if (gbfId) {
        data.functionId = parseInt(gbfId);
    }

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
            if (functionModal) functionModal.hide();
            loadFunctions(); // Reload functions from server
            updateSummaryData();

            // If we're editing the currently selected function, update UI
            if (currentFunctionId === parseInt(gbfId)) {
                const selectedFunctionName = document.getElementById('selectedFunctionName');
                if (selectedFunctionName) {
                    selectedFunctionName.textContent = funcName;
                }
            }

            showToast('Success', result.message);
        } else {
            showToast('Error', result.message, 'error');
        }
    })
    .catch(error => {
        showToast('Error', 'An error occurred while saving the function', 'error');
        console.error('Error:', error);
    });
}

// Confirm function deletion
function confirmDeleteFunction(gbfId, funcName) {
    deleteType = 'function';
    deleteId = gbfId;
    
    const deleteModalTitle = document.getElementById('deleteModalTitle');
    const deleteModalBody = document.getElementById('deleteModalBody');
    
    if (deleteModalTitle) {
        deleteModalTitle.textContent = 'Delete Function';
    }
    if (deleteModalBody) {
        deleteModalBody.textContent = `Are you sure you want to delete the function "${funcName}"? This will also delete all associated parameters.`;
    }
    
    if (deleteModal) deleteModal.show();
}

// Delete function
function deleteFunction(gbfId) {
    fetch(`/functions/delete_function/${gbfId}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(result => {
        if (deleteModal) deleteModal.hide();
        
        if (result.success) {
            // If we're deleting the currently selected function, hide parameter section
            if (currentFunctionId === gbfId) {
                resetParameterSection();
            }

            // Reload functions from server
            loadFunctions();

            showToast('Success', result.message);
        } else {
            showToast('Error', result.message, 'error');
        }
    })
    .catch(error => {
        if (deleteModal) deleteModal.hide();
        showToast('Error', 'An error occurred while deleting the function', 'error');
        console.error('Error:', error);
    });
}

// ======================================
// PARAMETER MANAGEMENT
// ======================================

// View parameters for a function
function viewParameters(gbfId, funcName) {
    currentFunctionId = gbfId;
    
    const selectedFunctionName = document.getElementById('selectedFunctionName');
    const noParametersPlaceholder = document.getElementById('noParametersPlaceholder');
    const parametersContainer = document.getElementById('parametersContainer');
    const addParameterBtn = document.getElementById('addParameterBtn');
    
    if (selectedFunctionName) {
        selectedFunctionName.textContent = funcName;
    }
    
    // Show parameter section and enable add parameter button
    if (noParametersPlaceholder) {
        noParametersPlaceholder.style.display = 'none';
    }
    if (parametersContainer) {
        parametersContainer.style.display = 'block';
    }
    if (addParameterBtn) {
        addParameterBtn.disabled = false;
    }
    
    // Highlight the selected function row
    const rows = document.querySelectorAll('#functionTableBody tr');
    rows.forEach(row => {
        if (row.getAttribute('data-id') == gbfId) {
            row.classList.add('selected-function');
        } else {
            row.classList.remove('selected-function');
        }
    });
    
    loadParameters(gbfId);
}

// Reset parameter section to default state
function resetParameterSection() {
    currentFunctionId = null;
    
    const selectedFunctionName = document.getElementById('selectedFunctionName');
    const noParametersPlaceholder = document.getElementById('noParametersPlaceholder');
    const parametersContainer = document.getElementById('parametersContainer');
    const addParameterBtn = document.getElementById('addParameterBtn');
    
    if (selectedFunctionName) {
        selectedFunctionName.textContent = 'No function selected';
    }
    if (noParametersPlaceholder) {
        noParametersPlaceholder.style.display = 'block';
    }
    if (parametersContainer) {
        parametersContainer.style.display = 'none';
    }
    if (addParameterBtn) {
        addParameterBtn.disabled = true;
    }
}

// Load parameters for a function
function loadParameters(gbfId) {
    loadParametersForFunction(gbfId);
}

// Load parameters from server
function loadParametersForFunction(functionId) {
    fetch(`/functions/get_function_parameters/${functionId}`)
        .then(response => response.json())
        .then(data => {
            // Cache the parameters
            functionParameters[functionId] = data;
            renderParameters(data);
        })
        .catch(error => {
            console.error('Error loading parameters:', error);
            showToast('Error', 'Failed to load function parameters', 'error');
            // Initialize empty parameters array
            functionParameters[functionId] = [];
            renderParameters([]);
        });
}

// Render parameters in the table
function renderParameters(parameters) {
    const tableBody = document.getElementById('parameterTableBody');
    if (!tableBody) return;
    
    tableBody.innerHTML = '';
    
    if (!Array.isArray(parameters) || parameters.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center py-4">
                    <div class="text-muted">
                        <i class="fas fa-info-circle me-2"></i>
                        No parameters defined for this function yet.
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    // Sort parameters by sequence
    const sortedParams = [...parameters].sort((a, b) => (a.GBF_SEQ || 0) - (b.GBF_SEQ || 0));
    
    sortedParams.forEach(param => {
        const row = `
            <tr>
                <td>
                    <span class="sequence-number">${param.GBF_SEQ || 1}</span>
                </td>
                <td>
                    <strong>${param.PARAM_NAME}</strong>
                </td>
                <td>
                    <span class="badge bg-info param-type-badge">${param.PARAM_TYPE}</span>
                </td>
                <td>
                    <span class="badge ${param.PARAM_IO_TYPE === 'INPUT' ? 'bg-success' : 'bg-warning'} param-type-badge">
                        ${param.PARAM_IO_TYPE}
                    </span>
                </td>
                <td>
                    <small class="text-muted">${param.DESCRIPTION || 'No description'}</small>
                </td>
                <td>
                    <button class="btn btn-warning btn-sm me-1" onclick="editParameter(${param.GBFP_ID})">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-danger btn-sm" onclick="confirmDeleteParameter(${param.GBFP_ID}, '${param.PARAM_NAME}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `;
        tableBody.innerHTML += row;
    });
}

// Open modal for creating new parameter
function openNewParamModal() {
    if (!currentFunctionId) {
        showToast('Error', 'Please select a function first', 'error');
        return;
    }
    
    const modalTitle = document.getElementById('parameterModalTitle');
    const parameterForm = document.getElementById('parameterForm');
    const gbfpIdField = document.getElementById('gbfpId');
    const paramFunctionIdField = document.getElementById('paramFunctionId');
    
    if (modalTitle) modalTitle.textContent = 'Add New Parameter';
    if (parameterForm) parameterForm.reset();
    if (gbfpIdField) gbfpIdField.value = '';
    if (paramFunctionIdField) paramFunctionIdField.value = currentFunctionId;
    
    // Set default sequence number
    const currentParams = functionParameters[currentFunctionId] || [];
    const maxSequence = currentParams.length > 0 ? Math.max(...currentParams.map(p => p.GBF_SEQ || 0)) : 0;
    const paramSequenceField = document.getElementById('paramSequence');
    if (paramSequenceField) {
        paramSequenceField.value = maxSequence + 1;
    }
    
    if (parameterModal) parameterModal.show();
}

// Edit existing parameter
function editParameter(gbfpId) {
    const allParams = Object.values(functionParameters).flat();
    const param = allParams.find(p => p.GBFP_ID === gbfpId);
    
    if (param) {
        const modalTitle = document.getElementById('parameterModalTitle');
        const gbfpIdField = document.getElementById('gbfpId');
        const paramFunctionIdField = document.getElementById('paramFunctionId');
        const paramNameField = document.getElementById('paramName');
        const paramTypeField = document.getElementById('paramType');
        const paramIOTypeField = document.getElementById('paramIOType');
        const paramSequenceField = document.getElementById('paramSequence');
        const paramDescField = document.getElementById('paramDescription');
        
        if (modalTitle) modalTitle.textContent = 'Edit Parameter';
        if (gbfpIdField) gbfpIdField.value = gbfpId;
        if (paramFunctionIdField) paramFunctionIdField.value = param.GBF_ID;
        if (paramNameField) paramNameField.value = param.PARAM_NAME;
        if (paramTypeField) paramTypeField.value = param.PARAM_TYPE;
        if (paramIOTypeField) paramIOTypeField.value = param.PARAM_IO_TYPE;
        if (paramSequenceField) paramSequenceField.value = param.GBF_SEQ || 1;
        if (paramDescField) paramDescField.value = param.DESCRIPTION || '';
        
        if (parameterModal) parameterModal.show();
    } else {
        showToast('Error', 'Parameter not found', 'error');
    }
}

// Save parameter (create or update)
function saveParameter() {
    const gbfpId = document.getElementById('gbfpId').value;
    const functionId = document.getElementById('paramFunctionId').value;
    const paramName = document.getElementById('paramName').value;
    const paramType = document.getElementById('paramType').value;
    const paramIOType = document.getElementById('paramIOType').value;
    const paramSequence = document.getElementById('paramSequence').value;
    const paramDescription = document.getElementById('paramDescription').value;

    if (!paramName || !paramType || !paramIOType) {
        showToast('Error', 'Parameter Name, Type, and I/O Type are required!', 'error');
        return;
    }

    const data = {
        gbfId: parseInt(functionId),
        paramName: paramName,
        paramType: paramType,
        paramIOType: paramIOType,
        sequence: parseInt(paramSequence) || 1,
        description: paramDescription
    };

    const method = gbfpId ? 'PUT' : 'POST';
    const url = gbfpId ? '/functions/update_function_parameter' : '/functions/add_function_parameter';
    
    if (gbfpId) {
        data.gbfpId = parseInt(gbfpId);
    }

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
            if (parameterModal) parameterModal.hide();
            
            // Reload parameters for current function
            if (currentFunctionId) {
                loadParametersForFunction(currentFunctionId);
            }
            
            // Update function list to refresh parameter counts
            loadFunctions();
            
            showToast('Success', result.message);
        } else {
            showToast('Error', result.message, 'error');
        }
    })
    .catch(error => {
        showToast('Error', 'An error occurred while saving the parameter', 'error');
        console.error('Error:', error);
    });
}

// Confirm parameter deletion
function confirmDeleteParameter(gbfpId, paramName) {
    deleteType = 'parameter';
    deleteId = gbfpId;
    
    const deleteModalTitle = document.getElementById('deleteModalTitle');
    const deleteModalBody = document.getElementById('deleteModalBody');
    
    if (deleteModalTitle) {
        deleteModalTitle.textContent = 'Delete Parameter';
    }
    if (deleteModalBody) {
        deleteModalBody.textContent = `Are you sure you want to delete the parameter "${paramName}"?`;
    }
    
    if (deleteModal) deleteModal.show();
}

// Delete parameter
function deleteParameter(gbfpId) {
    fetch(`/functions/delete_function_parameter/${gbfpId}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(result => {
        if (deleteModal) deleteModal.hide();
        
        if (result.success) {
            // Reload parameters for current function
            if (currentFunctionId) {
                loadParametersForFunction(currentFunctionId);
            }
            
            // Update function list to refresh parameter counts
            loadFunctions();
            
            showToast('Success', result.message);
        } else {
            showToast('Error', result.message, 'error');
        }
    })
    .catch(error => {
        if (deleteModal) deleteModal.hide();
        showToast('Error', 'An error occurred while deleting the parameter', 'error');
        console.error('Error:', error);
    });
}

// ======================================
// UTILITY FUNCTIONS
// ======================================

// Show toast notification
function showToast(title, message, type = 'success') {
    // Use global showToast if available
    if (typeof window.showToast === 'function') {
        window.showToast(title, message, type);
        return;
    }
    
    // Fallback alert
    alert(`${title}: ${message}`);
}