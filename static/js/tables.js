// Tables Management JavaScript

// Global variables
let allTables = [];
let selectedTables = [];
let currentDeleteId = null;
let currentConnectionHandle = null;
let connections = {};
let app_runtime_id = null;

// Bootstrap modal instances
let tableModal;
let deleteModal;
let importModal;

document.addEventListener('DOMContentLoaded', function() {
    // Initialize app_runtime_id from window
    app_runtime_id = window.app_runtime_id;
    
    // Initialize Bootstrap modals
    tableModal = new bootstrap.Modal(document.getElementById('tableModal'));
    deleteModal = new bootstrap.Modal(document.getElementById('deleteModal'));
    importModal = new bootstrap.Modal(document.getElementById('importModal'));
    
    // Setup event listeners
    document.getElementById('testQueryBtn').addEventListener('click', testQuery);
    document.getElementById('saveTableBtn').addEventListener('click', saveTable);
    document.getElementById('confirmDeleteBtn').addEventListener('click', confirmDelete);
    document.getElementById('startImportBtn').addEventListener('click', startImport);
    
    // Load tables and connections
    loadTables();
    loadConnections();
    loadEnvironmentConfigs();
});

// Load active database connections
function loadConnections() {
    if (!app_runtime_id) {
        console.error('app_runtime_id not available');
        return;
    }
    
    fetch(`/tables/get_active_connections_for_tables?app_runtime_id=${app_runtime_id}`)
        .then(response => response.json())
        .then(data => {
            connections = data;
            updateConnectionSelector(data);
        })
        .catch(error => {
            console.error('Error loading connections:', error);
            showToast('Error', 'Failed to load database connections', 'error');
        });
}

// Update connection selector dropdown
function updateConnectionSelector(connectionsData) {
    const select = document.getElementById('connectionSelect');
    // Keep the first option (Internal Database)
    select.innerHTML = '<option value="">Internal Database (GEE.db)</option>';
    
    // Add active connections
    for (const [handle, details] of Object.entries(connectionsData)) {
        // Get the environment name from the config ID
        const envName = details.env_name || 'Unknown Environment';
        const dbType = details.db_type || 'Unknown';
        
        // Create option with handle as value
        select.innerHTML += `<option value="${handle}">${envName} (${dbType})</option>`;
    }
}

// Change active connection
function changeConnection() {
    const connectionSelect = document.getElementById('connectionSelect');
    const connectionInfo = document.getElementById('connectionInfo');
    const importActions = document.getElementById('importActions');
    const importSelectedBtn = document.getElementById('importSelectedBtn');
    
    // Get selected connection handle
    currentConnectionHandle = connectionSelect.value;
    
    // Clear selected tables
    selectedTables = [];
    document.getElementById('selectAllTables').checked = false;
    
    // Update connection info
    if (currentConnectionHandle) {
        const connection = connections[currentConnectionHandle];
        if (connection) {
            connectionInfo.innerHTML = `
                <div class="row">
                    <div class="col-md-6">
                        <strong>Environment:</strong> ${connection.env_name || 'Unknown'}<br>
                        <strong>Database Type:</strong> ${connection.db_type || 'Unknown'}<br>
                        <strong>Connection Handle:</strong> ${currentConnectionHandle}
                    </div>
                    <div class="col-md-6">
                        <strong>Status:</strong> <span class="badge bg-success">Active</span><br>
                        <strong>Created:</strong> ${connection.created || 'Unknown'}<br>
                        <strong>Config ID:</strong> ${connection.config_id || 'Unknown'}
                    </div>
                </div>
            `;
            connectionInfo.classList.add('active');
            
            // Show import actions for external connections
            importActions.classList.add('active');
            importSelectedBtn.classList.remove('d-none');
        }
    } else {
        connectionInfo.classList.remove('active');
        importActions.classList.remove('active');
        importSelectedBtn.classList.add('d-none');
    }
    
    // Load tables for selected connection
    loadTables(currentConnectionHandle);
}

// Load tables
function loadTables(connectionHandle = null) {
    let url = '/tables/get_tables';
    if (connectionHandle) {
        url += `?connection_handle=${connectionHandle}`;
    }

    fetch(url)
        .then(response => response.json())
        .then(data => {
            allTables = data;
            renderTables(data);
            
            // Update table count
            document.getElementById('tableCount').textContent = `${data.length} tables`;
        })
        .catch(error => {
            showToast('Error', 'Failed to load tables', 'error');
            console.error('Error loading tables:', error);
        });
}

// Render tables to the table
function renderTables(tables) {
    const tableBody = document.getElementById('tableList');
    const noTablesMessage = document.getElementById('noTablesMessage');
    
    tableBody.innerHTML = '';
    
    if (tables.length === 0) {
        noTablesMessage.classList.remove('d-none');
        return;
    }
    
    noTablesMessage.classList.add('d-none');
    
    tables.forEach(table => {
        const tableId = table.GEC_ID || table.TABLE_NAME;
        const tableType = table.TABLE_TYPE || 'UNKNOWN';
        const typeClass = `table-type-${tableType}`;
        const typeLabel = getTableTypeLabel(tableType);
        const isExternal = tableType === 'EXTERNAL';
        const updateDate = formatDate(table.UPDATE_DATE || table.CREATE_DATE);
        
        // Generate checkbox based on table type
        const checkbox = isExternal ? 
            `<div class="form-check">
                <input class="form-check-input table-checkbox" type="checkbox" value="${table.TABLE_NAME}" 
                    data-id="${tableId}" onchange="toggleTableSelection(this)">
            </div>` : 
            '';
        
        // Generate action buttons based on table type
        const actionButtons = isExternal ? 
            `<button class="btn btn-info btn-sm me-1" onclick="viewTableDetails('${table.TABLE_NAME}')">
                <i class="fas fa-eye"></i>
            </button>` : 
            `<div class="btn-group">
                <button class="btn btn-warning btn-sm me-1" onclick="editTable(${table.GEC_ID})">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-danger btn-sm" onclick="deleteTable(${table.GEC_ID})">
                    <i class="fas fa-trash"></i>
                </button>
            </div>`;
        
        // Build the row
        const row = `
            <tr data-id="${tableId}" data-name="${table.TABLE_NAME}" data-type="${tableType}">
                <td class="checkbox-cell">${checkbox}</td>
                <td class="fw-medium">${table.TABLE_NAME}</td>
                <td>
                    <span class="table-type-badge ${typeClass}">${typeLabel}</span>
                    ${table.SOURCE ? `<span class="connection-badge">${table.SOURCE}</span>` : ''}
                </td>
                <td>${table.DESCRIPTION || '<span class="text-muted">No description</span>'}</td>
                <td>${updateDate || '-'}</td>
                <td class="action-cell">${actionButtons}</td>
            </tr>
        `;
        
        tableBody.innerHTML += row;
    });
}

// Get table type label
function getTableTypeLabel(type) {
    switch(type) {
        case 'R': return 'Reference';
        case 'F': return 'Application';
        case 'I': return 'Imported';
        case 'EXTERNAL': return 'External';
        default: return type;
    }
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

// Toggle table selection
function toggleTableSelection(checkbox) {
    const tableName = checkbox.value;
    
    if (checkbox.checked) {
        if (!selectedTables.includes(tableName)) {
            selectedTables.push(tableName);
        }
    } else {
        const index = selectedTables.indexOf(tableName);
        if (index !== -1) {
            selectedTables.splice(index, 1);
        }
    }
    
    // Update import button text
    updateImportButton();
}

// Toggle select all tables
function toggleSelectAll() {
    const selectAllCheckbox = document.getElementById('selectAllTables');
    const tableCheckboxes = document.querySelectorAll('.table-checkbox');
    
    // Clear selected tables array
    selectedTables = [];
    
    // Check or uncheck all checkboxes
    tableCheckboxes.forEach(checkbox => {
        checkbox.checked = selectAllCheckbox.checked;
        
        // Add to selected tables if checked
        if (selectAllCheckbox.checked) {
            selectedTables.push(checkbox.value);
        }
    });
    
    // Update import button text
    updateImportButton();
}

// Deselect all tables
function deselectAllTables() {
    document.getElementById('selectAllTables').checked = false;
    
    const tableCheckboxes = document.querySelectorAll('.table-checkbox');
    tableCheckboxes.forEach(checkbox => {
        checkbox.checked = false;
    });
    
    selectedTables = [];
    updateImportButton();
}

// Update import button text
function updateImportButton() {
    const importBtn = document.getElementById('importBtn');
    const importSelectedBtn = document.getElementById('importSelectedBtn');
    
    if (selectedTables.length > 0) {
        const text = `Import Selected Tables (${selectedTables.length})`;
        importBtn.textContent = text;
        importSelectedBtn.innerHTML = `<i class="fas fa-file-import me-2"></i>${text}`;
        importSelectedBtn.disabled = false;
    } else {
        importBtn.textContent = 'Import Tables';
        importSelectedBtn.innerHTML = '<i class="fas fa-file-import me-2"></i>Import Selected';
        importSelectedBtn.disabled = true;
    }
}

// Load environment configurations
function loadEnvironmentConfigs() {
    fetch('/tables/get_environment_configs')
        .then(response => response.json())
        .then(data => {
            const envSelect = document.getElementById('environmentSelect');
            envSelect.innerHTML = '<option value="">Select Environment...</option>';
            
            data.forEach(env => {
                envSelect.innerHTML += `<option value="${env.GT_ID}">${env.ENV_NAME} (${env.DB_TYPE})</option>`;
            });
        })
        .catch(error => {
            console.error('Error loading environment configs:', error);
            showToast('Error', 'Failed to load environment configurations', 'error');
        });
}

// Load tables from selected environment
function loadTablesFromEnvironment() {
    const envSelect = document.getElementById('environmentSelect');
    const tablesSelect = document.getElementById('availableTablesSelect');
    const tableNameInput = document.getElementById('tableName');
    const selectedEnvironmentIdInput = document.getElementById('selectedEnvironmentId');
    
    // Clear previous selections
    tablesSelect.innerHTML = '<option value="">Select a table...</option>';
    tableNameInput.value = '';
    
    const envId = envSelect.value;
    if (!envId) {
        selectedEnvironmentIdInput.value = '';
        return;
    }
    
    // Store the selected environment ID for test query use
    selectedEnvironmentIdInput.value = envId;
    
    // Show loading indicator
    tablesSelect.innerHTML = '<option value="">Loading tables...</option>';
    
    fetch(`/tables/get_tables_from_environment?config_id=${envId}`)
        .then(response => response.json())
        .then(data => {
            tablesSelect.innerHTML = '<option value="">Select a table...</option>';
            
            if (!data.success) {
                tablesSelect.innerHTML = '<option value="">Error loading tables</option>';
                showToast('Error', data.message || 'Failed to load tables', 'error');
                return;
            }
            
            const tables = data.tables || [];
            if (tables.length === 0) {
                tablesSelect.innerHTML = '<option value="">No tables found</option>';
                return;
            }
            
            tables.forEach(table => {
                tablesSelect.innerHTML += `<option value="${JSON.stringify(table).replace(/"/g, '&quot;')}">${table.display_name}</option>`;
            });
        })
        .catch(error => {
            console.error('Error loading tables from environment:', error);
            tablesSelect.innerHTML = '<option value="">Error loading tables</option>';
            showToast('Error', 'Failed to load tables from environment', 'error');
        });
}

// Select table from list
function selectTableFromList() {
    const tablesSelect = document.getElementById('availableTablesSelect');
    const tableNameInput = document.getElementById('tableName');
    const queryInput = document.getElementById('tableQuery');
    
    const selectedValue = tablesSelect.value;
    if (!selectedValue) {
        tableNameInput.value = '';
        return;
    }
    
    try {
        const tableInfo = JSON.parse(selectedValue.replace(/&quot;/g, '"'));
        tableNameInput.value = tableInfo.display_name;
        
        // Set a basic SELECT query for the table
        queryInput.value = `SELECT * FROM ${tableInfo.actual_name}`;
    } catch (error) {
        console.error('Error parsing table selection:', error);
        showToast('Error', 'Error selecting table', 'error');
    }
}

// Open new table modal
function openNewTableModal() {
    document.getElementById('modalTitle').textContent = 'Add New Table';
    document.getElementById('tableForm').reset();
    document.getElementById('gecId').value = '';
    document.getElementById('currentConnection').value = '';
    document.getElementById('queryResults').classList.add('d-none');
    
    // Reset environment and table selections
    document.getElementById('environmentSelect').value = '';
    document.getElementById('availableTablesSelect').innerHTML = '<option value="">Select a table...</option>';
    document.getElementById('selectedEnvironmentId').value = '';
    
    // Enable all form fields
    document.getElementById('tableName').readOnly = true; // Keep readonly until table is selected
    document.getElementById('tableType').disabled = false;
    document.getElementById('tableQuery').readOnly = false;
    document.getElementById('tableDescription').readOnly = false;
    document.getElementById('saveTableBtn').style.display = 'block';
    
    tableModal.show();
}

// Edit table
function editTable(gecId) {
    // Find table in the allTables array
    const table = allTables.find(t => t.GEC_ID === gecId);
    
    if (table) {
        document.getElementById('modalTitle').textContent = 'Edit Table';
        document.getElementById('gecId').value = table.GEC_ID;
        document.getElementById('tableName').value = table.TABLE_NAME;
        document.getElementById('tableType').value = table.TABLE_TYPE;
        document.getElementById('tableQuery').value = table.QUERY || '';
        document.getElementById('tableDescription').value = table.DESCRIPTION || '';
        document.getElementById('currentConnection').value = '';
        
        // Enable all form fields
        document.getElementById('tableName').readOnly = false;
        document.getElementById('tableType').disabled = false;
        document.getElementById('tableQuery').readOnly = false;
        document.getElementById('tableDescription').readOnly = false;
        document.getElementById('saveTableBtn').style.display = 'block';
        
        // Hide query results section
        document.getElementById('queryResults').classList.add('d-none');
        
        tableModal.show();
    } else {
        showToast('Error', 'Table not found', 'error');
    }
}

// View table details (used for external tables)
function viewTableDetails(tableName) {
    // Find table in the allTables array
    const table = allTables.find(t => t.TABLE_NAME === tableName);
    
    if (table) {
        document.getElementById('modalTitle').textContent = 'View External Table';
        document.getElementById('gecId').value = '';
        document.getElementById('tableName').value = table.TABLE_NAME;
        document.getElementById('tableType').value = table.TABLE_TYPE || 'EXTERNAL';
        document.getElementById('tableQuery').value = table.QUERY || '';
        document.getElementById('tableDescription').value = table.DESCRIPTION || '';
        document.getElementById('currentConnection').value = currentConnectionHandle;
        
        // Make fields read-only for external tables
        document.getElementById('tableName').readOnly = true;
        document.getElementById('tableType').disabled = true;
        document.getElementById('tableQuery').readOnly = false; // Allow query testing
        document.getElementById('tableDescription').readOnly = true;
        document.getElementById('saveTableBtn').style.display = 'none';
        
        // Auto-test the query to show table structure
        testQuery();
        
        tableModal.show();
    } else {
        showToast('Error', 'Table not found', 'error');
    }
}

// Delete table
function deleteTable(gecId) {
    currentDeleteId = gecId;
    deleteModal.show();
}

// Confirm delete
function confirmDelete() {
    if (!currentDeleteId) return;
    
    fetch(`/tables/delete_table/${currentDeleteId}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            deleteModal.hide();
            loadTables();
            showToast('Success', data.message);
        } else {
            showToast('Error', data.message, 'error');
        }
    })
    .catch(error => {
        showToast('Error', 'An error occurred while deleting the table', 'error');
        console.error('Error:', error);
    });
}

// Save table
function saveTable() {
    const gecId = document.getElementById('gecId').value;
    const tableName = document.getElementById('tableName').value;
    const tableType = document.getElementById('tableType').value;
    const query = document.getElementById('tableQuery').value;
    const description = document.getElementById('tableDescription').value;
    
    if (!tableName) {
        showToast('Error', 'Table Name is required', 'error');
        return;
    }
    
    if (!tableType) {
        showToast('Error', 'Table Type is required', 'error');
        return;
    }
    
    const data = {
        gecId: gecId,
        tableName: tableName,
        tableType: tableType,
        query: query,
        description: description
    };
    
    const method = gecId ? 'PUT' : 'POST';
    const url = gecId ? '/tables/update_table' : '/tables/add_table';

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
            tableModal.hide();
            loadTables();
            showToast('Success', result.message);
        } else {
            showToast('Error', result.message, 'error');
        }
    })
    .catch(error => {
        showToast('Error', 'An error occurred while saving the table', 'error');
        console.error('Error:', error);
    });
}

// Test query
function testQuery() {
    const query = document.getElementById('tableQuery').value;
    const connHandle = document.getElementById('currentConnection').value || currentConnectionHandle;
    const selectedEnvironmentId = document.getElementById('selectedEnvironmentId').value;
    
    if (!query) {
        showToast('Warning', 'Please enter a query to test', 'warning');
        return;
    }
    
    // Only allow SELECT queries for safety
    if (!query.trim().toUpperCase().startsWith('SELECT')) {
        showToast('Error', 'Only SELECT queries are allowed for testing', 'error');
        return;
    }
    
    // Prepare request data
    const requestData = {
        query: query
    };
    
    // Add connection handle if using external connection
    if (connHandle) {
        requestData.connection_handle = connHandle;
    } else if (selectedEnvironmentId) {
        // If no connection handle but we have a selected environment, use that
        requestData.environment_config_id = selectedEnvironmentId;
    }
    
    // Show loading indicator
    document.getElementById('queryResults').classList.remove('d-none');
    document.getElementById('resultsBody').innerHTML = `
        <tr>
            <td colspan="10" class="text-center">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <div class="mt-2">Executing query...</div>
            </td>
        </tr>
    `;
    
    fetch('/tables/test_query', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestData)
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            displayQueryResults(result.columns, result.data);
            showToast('Success', result.message);
        } else {
            document.getElementById('queryResults').classList.remove('d-none');
            document.getElementById('resultsBody').innerHTML = `
                <tr>
                    <td colspan="10" class="text-center text-danger">
                        <i class="fas fa-exclamation-circle me-2"></i>
                        ${result.message}
                    </td>
                </tr>
            `;
            showToast('Error', result.message, 'error');
        }
    })
    .catch(error => {
        document.getElementById('queryResults').classList.remove('d-none');
        document.getElementById('resultsBody').innerHTML = `
            <tr>
                <td colspan="10" class="text-center text-danger">
                    <i class="fas fa-exclamation-circle me-2"></i>
                    An error occurred while executing the query
                </td>
            </tr>
        `;
        showToast('Error', 'An error occurred while testing the query', 'error');
        console.error('Error:', error);
    });
}

// Display query test results
function displayQueryResults(columns, data) {
    const resultsContainer = document.getElementById('queryResults');
    const headerRow = document.getElementById('resultsHeader');
    const bodyContent = document.getElementById('resultsBody');
    
    // Show the results container
    resultsContainer.classList.remove('d-none');
    
    // Build header
    headerRow.innerHTML = '<tr>' + columns.map(col => `<th>${col}</th>`).join('') + '</tr>';
    
    // Build body
    bodyContent.innerHTML = '';
    
    if (data.length === 0) {
        bodyContent.innerHTML = `<tr><td colspan="${columns.length}" class="text-center text-muted">No results found</td></tr>`;
        return;
    }
    
    data.forEach(row => {
        let rowHtml = '<tr>';
        columns.forEach(col => {
            const value = row[col];
            rowHtml += `<td>${value !== null ? value : '<span class="text-muted">NULL</span>'}</td>`;
        });
        rowHtml += '</tr>';
        
        bodyContent.innerHTML += rowHtml;
    });
}

// Search tables
function searchTables() {
    const searchTerm = document.getElementById('searchTables').value.toLowerCase();
    const tableType = document.getElementById('filterTableType').value;
    
    let filteredTables = allTables;
    
    // Apply search filter
    if (searchTerm) {
        filteredTables = filteredTables.filter(table => 
            table.TABLE_NAME.toLowerCase().includes(searchTerm) || 
            (table.DESCRIPTION && table.DESCRIPTION.toLowerCase().includes(searchTerm))
        );
    }
    
    // Apply table type filter
    if (tableType) {
        filteredTables = filteredTables.filter(table => table.TABLE_TYPE === tableType);
    }
    
    renderTables(filteredTables);
    
    // Update table count
    document.getElementById('tableCount').textContent = `${filteredTables.length} tables`;
}

// Filter tables by type
function filterTables() {
    // Reuse search function as it handles both search and filter
    searchTables();
}

// Show import modal
function showImportModal() {
    if (selectedTables.length === 0) {
        showToast('Warning', 'Please select at least one table to import', 'warning');
        return;
    }
    
    if (!currentConnectionHandle) {
        showToast('Error', 'No external connection selected', 'error');
        return;
    }
    
    const connection = connections[currentConnectionHandle];
    const envName = connection ? connection.env_name : 'Unknown Environment';
    
    document.getElementById('importSourceName').textContent = envName;
    
    // Populate tables list
    const tablesList = document.getElementById('importTablesList');
    tablesList.innerHTML = '';
    
    selectedTables.forEach(tableName => {
        tablesList.innerHTML += `
            <tr data-name="${tableName}">
                <td>${tableName}</td>
                <td><span class="badge bg-secondary">Pending</span></td>
            </tr>
        `;
    });
    
    // Hide progress bar
    document.getElementById('importProgress').classList.add('d-none');
    
    // Show the modal
    importModal.show();
}

// Start import process
function startImport() {
    if (selectedTables.length === 0 || !currentConnectionHandle) {
        importModal.hide();
        return;
    }
    
    // Show progress bar
    const progressBar = document.getElementById('importProgressBar');
    document.getElementById('importProgress').classList.remove('d-none');
    progressBar.style.width = '0%';
    
    // Disable import button
    document.getElementById('startImportBtn').disabled = true;
    
    // Process each table
    let importedCount = 0;
    const totalTables = selectedTables.length;
    
    // Process tables one by one
    function processNextTable(index) {
        if (index >= selectedTables.length) {
            // All tables processed
            setTimeout(() => {
                // Complete the progress bar
                progressBar.style.width = '100%';
                
                // Re-enable import button
                document.getElementById('startImportBtn').disabled = false;
                
                // Close modal after a delay
                setTimeout(() => {
                    importModal.hide();
                    
                    // Show success message
                    if (importedCount > 0) {
                        showToast('Success', `Successfully imported ${importedCount} table(s)`, 'success');
                        
                        // Reload tables to show imported ones
                        loadTables();
                        
                        // Clear selection
                        selectedTables = [];
                        document.getElementById('selectAllTables').checked = false;
                        updateImportButton();
                    } else {
                        showToast('Warning', 'No tables were imported', 'warning');
                    }
                }, 1000);
            }, 500);
            return;
        }
        
        const tableName = selectedTables[index];
        const tableRow = document.querySelector(`#importTablesList tr[data-name="${tableName}"]`);
        
        // Update status to "Processing"
        tableRow.cells[1].innerHTML = '<span class="badge bg-info">Processing</span>';
        
        // Update progress bar
        const progress = Math.round((index / totalTables) * 100);
        progressBar.style.width = `${progress}%`;
        
        // Import the table
        fetch('/tables/import_table_structure', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                connection_handle: currentConnectionHandle,
                table_name: tableName
            })
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                // Update status to "Success"
                tableRow.cells[1].innerHTML = '<span class="badge bg-success">Imported</span>';
                importedCount++;
            } else {
                // Update status to "Failed"
                tableRow.cells[1].innerHTML = `<span class="badge bg-danger" title="${result.message}">Failed</span>`;
            }
            
            // Process next table
            setTimeout(() => processNextTable(index + 1), 500);
        })
        .catch(error => {
            // Update status to "Error"
            tableRow.cells[1].innerHTML = '<span class="badge bg-danger">Error</span>';
            
            // Process next table
            setTimeout(() => processNextTable(index + 1), 500);
        });
    }
    
    // Start processing tables
    processNextTable(0);
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