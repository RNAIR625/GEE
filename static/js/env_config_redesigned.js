// Redesigned Environment Configuration JavaScript

// Global variables
let allEnvironments = [];
let currentDeleteId = null;
let currentDeleteType = null; // 'environment' or 'database'
let environmentModal;
let databaseModal;
let deleteModal;
let currentConnectionHandle = null;
let currentDbConfigId = null;
let activeConnections = {};
let app_runtime_id = window.app_runtime_id || 'default';

document.addEventListener('DOMContentLoaded', function() {
    // Initialize modals
    environmentModal = new bootstrap.Modal(document.getElementById('environmentModal'));
    databaseModal = new bootstrap.Modal(document.getElementById('databaseModal'));
    deleteModal = new bootstrap.Modal(document.getElementById('deleteModal'));
    
    // Load environments and active connections
    loadEnvironments();
    loadActiveConnections();
    
    // Set interval to refresh active connections every 30 seconds
    setInterval(loadActiveConnections, 30000);
});

// Load all environments with their database configurations
function loadEnvironments() {
    fetch('/env_config/get_env_configs')
        .then(response => response.json())
        .then(data => {
            allEnvironments = data;
            renderEnvironments(data);
            updateStatistics(data);
        })
        .catch(error => {
            console.error('Error loading environments:', error);
            showToast('Error', 'Failed to load environments', 'error');
        });
}

// Render environments with nested database configurations
function renderEnvironments(environments) {
    const container = document.getElementById('environmentsList');
    const noEnvMessage = document.getElementById('noEnvironmentsMessage');
    
    container.innerHTML = '';
    
    if (environments.length === 0) {
        noEnvMessage.classList.remove('d-none');
        return;
    }
    
    noEnvMessage.classList.add('d-none');
    
    environments.forEach(env => {
        const envCard = createEnvironmentCard(env);
        container.appendChild(envCard);
    });
}

// Create environment card with collapsible database list
function createEnvironmentCard(environment) {
    const card = document.createElement('div');
    card.className = 'environment-card';
    card.setAttribute('data-env-id', environment.ENV_ID);
    
    const databases = environment.databases || [];
    const dbCount = databases.length;
    const activeDbCount = databases.filter(db => db.STATUS === 'active').length;
    
    // Environment header
    const header = document.createElement('div');
    header.className = 'environment-header collapsed';
    header.setAttribute('data-bs-toggle', 'collapse');
    header.setAttribute('data-bs-target', `#env-${environment.ENV_ID}`);
    header.innerHTML = `
        <div class="d-flex justify-content-between align-items-center">
            <div class="d-flex align-items-center">
                <i class="fas fa-chevron-down collapse-icon me-3"></i>
                <div>
                    <h5 class="mb-0">${environment.ENV_NAME}</h5>
                    <small class="opacity-75">${environment.DESCRIPTION || 'No description'}</small>
                </div>
                <span class="env-type-badge env-type-${environment.ENV_TYPE}">${environment.ENV_TYPE}</span>
            </div>
            <div class="d-flex align-items-center">
                <span class="badge bg-light text-dark me-2">${dbCount} database${dbCount !== 1 ? 's' : ''}</span>
                <div class="dropdown" onclick="event.stopPropagation();">
                    <button class="btn btn-sm btn-outline-light" type="button" data-bs-toggle="dropdown">
                        <i class="fas fa-ellipsis-v"></i>
                    </button>
                    <ul class="dropdown-menu">
                        <li><a class="dropdown-item" href="#" onclick="addDatabaseConfig(${environment.ENV_ID})">
                            <i class="fas fa-plus me-2"></i>Add Database
                        </a></li>
                        <li><a class="dropdown-item" href="#" onclick="editEnvironment(${environment.ENV_ID})">
                            <i class="fas fa-edit me-2"></i>Edit Environment
                        </a></li>
                        <li><hr class="dropdown-divider"></li>
                        <li><a class="dropdown-item text-danger" href="#" onclick="deleteEnvironment(${environment.ENV_ID})">
                            <i class="fas fa-trash me-2"></i>Delete Environment
                        </a></li>
                    </ul>
                </div>
            </div>
        </div>
    `;
    
    // Environment body (collapsible)
    const body = document.createElement('div');
    body.className = 'collapse environment-body';
    body.id = `env-${environment.ENV_ID}`;
    
    if (databases.length === 0) {
        body.innerHTML = `
            <div class="text-center py-4">
                <i class="fas fa-database fa-2x text-muted mb-3"></i>
                <p class="text-muted mb-3">No databases configured for this environment</p>
                <button class="add-database-btn" onclick="addDatabaseConfig(${environment.ENV_ID})">
                    <i class="fas fa-plus me-2"></i>Add First Database
                </button>
            </div>
        `;
    } else {
        // Add databases
        databases.forEach(db => {
            const dbItem = createDatabaseItem(db, environment);
            body.appendChild(dbItem);
        });
        
        // Add "Add Database" button at the bottom
        const addDbContainer = document.createElement('div');
        addDbContainer.className = 'text-center py-3 bg-light';
        addDbContainer.innerHTML = `
            <button class="add-database-btn" onclick="addDatabaseConfig(${environment.ENV_ID})">
                <i class="fas fa-plus me-2"></i>Add Another Database
            </button>
        `;
        body.appendChild(addDbContainer);
    }
    
    card.appendChild(header);
    card.appendChild(body);
    
    // Add event listener for collapse toggle
    header.addEventListener('click', function() {
        setTimeout(() => {
            header.classList.toggle('collapsed');
        }, 150);
    });
    
    return card;
}

// Create database item within environment
function createDatabaseItem(database, environment) {
    const item = document.createElement('div');
    item.className = 'database-item';
    item.setAttribute('data-db-id', database.DB_CONFIG_ID);
    
    // Check if this database has an active connection
    const dbConnections = Object.values(activeConnections).filter(conn => 
        conn.db_config_id && parseInt(conn.db_config_id) === parseInt(database.DB_CONFIG_ID)
    );
    const isConnected = dbConnections.length > 0;
    
    const connectionStatus = isConnected ? 
        '<span class="connection-badge connection-active">Connected</span>' : 
        '<span class="connection-badge connection-inactive">Not Connected</span>';
    
    // Format last tested time
    const lastTested = database.LAST_TESTED ? 
        new Date(database.LAST_TESTED).toLocaleString() : 
        'Never';
    
    item.innerHTML = `
        <div class="d-flex justify-content-between align-items-center">
            <div class="flex-grow-1">
                <div class="d-flex align-items-center mb-2">
                    <h6 class="mb-0 me-2">${database.DB_DISPLAY_NAME}</h6>
                    <span class="db-type-badge db-type-${database.DB_TYPE}">${database.DB_TYPE}</span>
                    ${database.IS_PRIMARY ? '<span class="primary-badge">PRIMARY</span>' : ''}
                    ${connectionStatus}
                </div>
                <div class="d-flex align-items-center text-muted small">
                    <span class="me-3">
                        <i class="fas fa-database me-1"></i>${database.DB_NAME}
                    </span>
                    ${database.DB_HOST ? `
                        <span class="me-3">
                            <i class="fas fa-server me-1"></i>${database.DB_HOST}:${database.DB_PORT || 'default'}
                        </span>
                    ` : ''}
                    <span>
                        <i class="fas fa-clock me-1"></i>Last tested: ${lastTested}
                    </span>
                </div>
            </div>
            <div class="database-actions">
                <div class="btn-group">
                    <button class="btn btn-sm btn-info" onclick="testDatabaseConnectionDirect(${database.DB_CONFIG_ID})" 
                            title="Test Connection">
                        <i class="fas fa-plug"></i>
                    </button>
                    <button class="btn btn-sm btn-warning" onclick="editDatabaseConfig(${database.DB_CONFIG_ID})" 
                            title="Edit Database">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="deleteDatabaseConfig(${database.DB_CONFIG_ID})" 
                            title="Delete Database">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        </div>
    `;
    
    return item;
}

// Update statistics display
function updateStatistics(environments) {
    const envCount = environments.length;
    const dbCount = environments.reduce((total, env) => total + (env.databases ? env.databases.length : 0), 0);
    const activeConnCount = Object.keys(activeConnections).length;
    
    // Count recently tested (within last 24 hours)
    const oneDayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);
    const lastTestedCount = environments.reduce((total, env) => {
        if (!env.databases) return total;
        return total + env.databases.filter(db => 
            db.LAST_TESTED && new Date(db.LAST_TESTED) > oneDayAgo
        ).length;
    }, 0);
    
    document.getElementById('envCount').textContent = envCount;
    document.getElementById('dbCount').textContent = dbCount;
    document.getElementById('activeConnCount').textContent = activeConnCount;
    document.getElementById('lastTestedCount').textContent = lastTestedCount;
}

// Filter environments based on search and filters
function filterEnvironments() {
    const searchTerm = document.getElementById('searchEnvironments').value.toLowerCase();
    const envTypeFilter = document.getElementById('filterEnvType').value;
    const dbTypeFilter = document.getElementById('filterDbType').value;
    
    let filteredEnvironments = allEnvironments.filter(env => {
        // Environment type filter
        if (envTypeFilter && env.ENV_TYPE !== envTypeFilter) {
            return false;
        }
        
        // Search filter
        if (searchTerm) {
            const envNameMatch = env.ENV_NAME.toLowerCase().includes(searchTerm);
            const descMatch = env.DESCRIPTION && env.DESCRIPTION.toLowerCase().includes(searchTerm);
            const dbMatch = env.databases && env.databases.some(db => 
                db.DB_DISPLAY_NAME.toLowerCase().includes(searchTerm) ||
                db.DB_NAME.toLowerCase().includes(searchTerm)
            );
            
            if (!envNameMatch && !descMatch && !dbMatch) {
                return false;
            }
        }
        
        // Database type filter
        if (dbTypeFilter) {
            if (!env.databases || !env.databases.some(db => db.DB_TYPE === dbTypeFilter)) {
                return false;
            }
        }
        
        return true;
    });
    
    renderEnvironments(filteredEnvironments);
}

// Clear all filters
function clearFilters() {
    document.getElementById('searchEnvironments').value = '';
    document.getElementById('filterEnvType').value = '';
    document.getElementById('filterDbType').value = '';
    renderEnvironments(allEnvironments);
}

// Open new environment modal
function openNewEnvironmentModal() {
    document.getElementById('envModalTitle').textContent = 'Add New Environment';
    document.getElementById('environmentForm').reset();
    document.getElementById('envId').value = '';
    environmentModal.show();
}

// Save environment
function saveEnvironment() {
    const envId = document.getElementById('envId').value;
    const envName = document.getElementById('envName').value;
    const envType = document.getElementById('envType').value;
    const description = document.getElementById('envDescription').value;
    
    if (!envName.trim()) {
        showToast('Error', 'Environment name is required', 'error');
        return;
    }
    
    const data = {
        envId: envId,
        envName: envName.trim(),
        envType: envType,
        description: description.trim()
    };
    
    const method = envId ? 'PUT' : 'POST';
    const url = envId ? '/env_config/update_environment' : '/env_config/add_environment';
    
    fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            environmentModal.hide();
            loadEnvironments();
            showToast('Success', result.message);
        } else {
            showToast('Error', result.message, 'error');
        }
    })
    .catch(error => {
        showToast('Error', 'An error occurred while saving the environment', 'error');
        console.error('Error:', error);
    });
}

// Edit environment
function editEnvironment(envId) {
    const environment = allEnvironments.find(env => env.ENV_ID === envId);
    
    if (environment) {
        document.getElementById('envModalTitle').textContent = 'Edit Environment';
        document.getElementById('envId').value = environment.ENV_ID;
        document.getElementById('envName').value = environment.ENV_NAME;
        document.getElementById('envType').value = environment.ENV_TYPE;
        document.getElementById('envDescription').value = environment.DESCRIPTION || '';
        environmentModal.show();
    } else {
        showToast('Error', 'Environment not found', 'error');
    }
}

// Delete environment
function deleteEnvironment(envId) {
    const environment = allEnvironments.find(env => env.ENV_ID === envId);
    if (!environment) return;
    
    currentDeleteId = envId;
    currentDeleteType = 'environment';
    
    const dbCount = environment.databases ? environment.databases.length : 0;
    document.getElementById('deleteMessage').textContent = 
        `Are you sure you want to delete the environment "${environment.ENV_NAME}"?`;
    document.getElementById('deleteWarning').textContent = 
        `This will delete the environment and all ${dbCount} database configuration(s) within it. This action cannot be undone.`;
    
    deleteModal.show();
}

// Add database configuration to environment
function addDatabaseConfig(envId) {
    document.getElementById('dbModalTitle').textContent = 'Add Database Configuration';
    document.getElementById('databaseForm').reset();
    document.getElementById('dbConfigId').value = '';
    document.getElementById('selectedEnvId').value = envId;
    document.getElementById('isPrimary').checked = false;
    
    // Reset connection status
    updateConnectionStatus('');
    currentConnectionHandle = null;
    currentDbConfigId = null;
    
    databaseModal.show();
}

// Edit database configuration
function editDatabaseConfig(dbConfigId) {
    // Find the database configuration across all environments
    let database = null;
    let environment = null;
    
    for (const env of allEnvironments) {
        if (env.databases) {
            const db = env.databases.find(db => db.DB_CONFIG_ID === dbConfigId);
            if (db) {
                database = db;
                environment = env;
                break;
            }
        }
    }
    
    if (database && environment) {
        document.getElementById('dbModalTitle').textContent = 'Edit Database Configuration';
        document.getElementById('dbConfigId').value = database.DB_CONFIG_ID;
        document.getElementById('selectedEnvId').value = environment.ENV_ID;
        document.getElementById('dbDisplayName').value = database.DB_DISPLAY_NAME;
        document.getElementById('dbType').value = database.DB_TYPE;
        document.getElementById('dbName').value = database.DB_NAME;
        document.getElementById('dbUsername').value = database.DB_USERNAME || '';
        document.getElementById('dbHost').value = database.DB_HOST || '';
        document.getElementById('dbPort').value = database.DB_PORT || '';
        document.getElementById('dbPassword').value = database.DB_PASSWORD || '';
        document.getElementById('dbInstance').value = database.DB_INSTANCE || '';
        document.getElementById('isPrimary').checked = database.IS_PRIMARY === 1;
        document.getElementById('dbStatus').value = database.STATUS || 'active';
        
        // Set Oracle connection type if applicable
        if (database.DB_TYPE === 'Oracle') {
            const oracleConnType = database.ORACLE_CONN_TYPE || 'service';
            document.querySelector(`input[name="oracleConnType"][value="${oracleConnType}"]`).checked = true;
        }
        
        // Reset connection status
        updateConnectionStatus('');
        currentConnectionHandle = null;
        currentDbConfigId = dbConfigId;
        
        // Toggle database fields based on selected type
        toggleDatabaseFields();
        
        databaseModal.show();
    } else {
        showToast('Error', 'Database configuration not found', 'error');
    }
}

// Delete database configuration
function deleteDatabaseConfig(dbConfigId) {
    // Find the database configuration
    let database = null;
    
    for (const env of allEnvironments) {
        if (env.databases) {
            const db = env.databases.find(db => db.DB_CONFIG_ID === dbConfigId);
            if (db) {
                database = db;
                break;
            }
        }
    }
    
    if (!database) return;
    
    currentDeleteId = dbConfigId;
    currentDeleteType = 'database';
    
    document.getElementById('deleteMessage').textContent = 
        `Are you sure you want to delete the database configuration "${database.DB_DISPLAY_NAME}"?`;
    document.getElementById('deleteWarning').textContent = 
        'This will remove the database configuration and any associated connection handles.';
    
    deleteModal.show();
}

// Confirm delete action
function confirmDelete() {
    if (!currentDeleteId || !currentDeleteType) return;
    
    const url = currentDeleteType === 'environment' ? 
        `/env_config/delete_environment/${currentDeleteId}` : 
        `/env_config/delete_database_config/${currentDeleteId}`;
    
    fetch(url, { method: 'DELETE' })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                deleteModal.hide();
                loadEnvironments();
                loadActiveConnections();
                showToast('Success', result.message);
            } else {
                showToast('Error', result.message, 'error');
            }
        })
        .catch(error => {
            showToast('Error', 'An error occurred while deleting', 'error');
            console.error('Error:', error);
        });
}

// Save database configuration
function saveDatabaseConfig() {
    const dbConfigId = document.getElementById('dbConfigId').value;
    const envId = document.getElementById('selectedEnvId').value;
    const dbDisplayName = document.getElementById('dbDisplayName').value;
    const dbType = document.getElementById('dbType').value;
    const dbName = document.getElementById('dbName').value;
    const dbUsername = document.getElementById('dbUsername').value;
    const dbHost = document.getElementById('dbHost').value;
    const dbPort = document.getElementById('dbPort').value;
    const dbPassword = document.getElementById('dbPassword').value;
    const dbInstance = document.getElementById('dbInstance').value;
    const isPrimary = document.getElementById('isPrimary').checked;
    const status = document.getElementById('dbStatus').value;
    
    if (!dbDisplayName.trim() || !dbType || !dbName.trim()) {
        showToast('Error', 'Display name, database type, and database name are required', 'error');
        return;
    }
    
    // Database type specific validation
    if (dbType !== 'SQLite') {
        if (!dbUsername.trim() || !dbHost.trim() || !dbPort) {
            showToast('Error', 'Username, host, and port are required for network databases', 'error');
            return;
        }
    }
    
    // Get Oracle connection type if Oracle is selected
    let oracleConnType = 'service';
    if (dbType === 'Oracle') {
        const selectedType = document.querySelector('input[name="oracleConnType"]:checked');
        if (selectedType) {
            oracleConnType = selectedType.value;
        }
    }
    
    const data = {
        dbConfigId: dbConfigId,
        envId: envId,
        dbDisplayName: dbDisplayName.trim(),
        dbType: dbType,
        dbName: dbName.trim(),
        dbUsername: dbUsername.trim(),
        dbHost: dbHost.trim(),
        dbPort: dbPort,
        dbPassword: dbPassword,
        dbInstance: dbInstance.trim(),
        oracleConnType: oracleConnType,
        isPrimary: isPrimary,
        status: status
    };
    
    const method = dbConfigId ? 'PUT' : 'POST';
    const url = dbConfigId ? '/env_config/update_database_config' : '/env_config/add_database_config';
    
    fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            databaseModal.hide();
            loadEnvironments();
            showToast('Success', result.message);
        } else {
            showToast('Error', result.message, 'error');
        }
    })
    .catch(error => {
        showToast('Error', 'An error occurred while saving the database configuration', 'error');
        console.error('Error:', error);
    });
}

// Test database connection (from modal)
function testDatabaseConnection() {
    const dbConfigId = document.getElementById('dbConfigId').value;
    
    if (dbConfigId) {
        // Testing existing database config
        testDatabaseConnectionDirect(parseInt(dbConfigId));
    } else {
        // Testing new database config
        testNewDatabaseConnection();
    }
}

// Test connection for existing database configuration
function testDatabaseConnectionDirect(dbConfigId) {
    currentDbConfigId = dbConfigId;
    
    // Show testing status
    updateConnectionStatus(`
        <div class="d-flex align-items-center justify-content-center">
            <div class="spinner-border text-primary me-3" role="status">
                <span class="visually-hidden">Testing...</span>
            </div>
            <div>Testing database connection...</div>
        </div>
    `);
    
    fetch('/env_config/test_database_connection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            dbConfigId: dbConfigId,
            app_runtime_id: app_runtime_id
        })
    })
    .then(response => response.json())
    .then(result => {
        handleConnectionTestResult(result);
    })
    .catch(error => {
        updateConnectionStatus(`
            <div class="text-center">
                <div class="bg-danger text-white p-3 rounded-3 mb-3">
                    <i class="fas fa-exclamation-triangle fa-3x mb-2"></i>
                    <h5>Error</h5>
                </div>
                <p>An error occurred while testing the connection: ${error}</p>
            </div>
        `);
    });
}

// Test connection for new database configuration (from form data)
function testNewDatabaseConnection() {
    const envId = document.getElementById('selectedEnvId').value;
    const dbDisplayName = document.getElementById('dbDisplayName').value;
    const dbType = document.getElementById('dbType').value;
    const dbName = document.getElementById('dbName').value;
    const dbUsername = document.getElementById('dbUsername').value;
    const dbHost = document.getElementById('dbHost').value;
    const dbPort = document.getElementById('dbPort').value;
    const dbPassword = document.getElementById('dbPassword').value;
    const dbInstance = document.getElementById('dbInstance').value;
    
    if (!dbDisplayName.trim() || !dbType || !dbName.trim()) {
        showToast('Error', 'Display name, database type, and database name are required', 'error');
        return;
    }
    
    // Database type specific validation
    if (dbType !== 'SQLite') {
        if (!dbUsername.trim() || !dbHost.trim() || !dbPort) {
            showToast('Error', 'Username, host, and port are required for network databases', 'error');
            return;
        }
    }
    
    // Get environment name
    const environment = allEnvironments.find(env => env.ENV_ID === parseInt(envId));
    const envName = environment ? environment.ENV_NAME : 'Unknown';
    
    // Get Oracle connection type if Oracle is selected
    let oracleConnType = 'service';
    if (dbType === 'Oracle') {
        const selectedType = document.querySelector('input[name="oracleConnType"]:checked');
        if (selectedType) {
            oracleConnType = selectedType.value;
        }
    }
    
    const data = {
        envName: envName,
        dbDisplayName: dbDisplayName.trim(),
        dbType: dbType,
        dbName: dbName.trim(),
        dbUsername: dbUsername.trim(),
        dbHost: dbHost.trim(),
        dbPort: dbPort,
        dbPassword: dbPassword,
        dbInstance: dbInstance.trim(),
        oracleConnType: oracleConnType,
        app_runtime_id: app_runtime_id
    };
    
    // Show testing status
    updateConnectionStatus(`
        <div class="d-flex align-items-center justify-content-center">
            <div class="spinner-border text-primary me-3" role="status">
                <span class="visually-hidden">Testing...</span>
            </div>
            <div>Testing database connection...</div>
        </div>
    `);
    
    fetch('/env_config/test_connection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        handleConnectionTestResult(result);
    })
    .catch(error => {
        updateConnectionStatus(`
            <div class="text-center">
                <div class="bg-danger text-white p-3 rounded-3 mb-3">
                    <i class="fas fa-exclamation-triangle fa-3x mb-2"></i>
                    <h5>Error</h5>
                </div>
                <p>An error occurred while testing the connection: ${error}</p>
            </div>
        `);
    });
}

// Handle connection test result
function handleConnectionTestResult(result) {
    if (result.success) {
        currentConnectionHandle = result.handle;
        
        updateConnectionStatus(`
            <div class="text-center">
                <div class="bg-success text-white p-3 rounded-3 mb-3">
                    <i class="fas fa-check-circle fa-3x mb-2"></i>
                    <h5>Connection Successful!</h5>
                </div>
                <p>${result.message}</p>
                <div class="alert alert-info">
                    <p class="mb-0"><strong>Connection Handle:</strong> ${result.handle}</p>
                </div>
            </div>
        `);
        
        // Auto-refresh if connection was stored automatically
        if (result.auto_stored) {
            loadEnvironments();
            loadActiveConnections();
        }
    } else {
        updateConnectionStatus(`
            <div class="text-center">
                <div class="bg-danger text-white p-3 rounded-3 mb-3">
                    <i class="fas fa-times-circle fa-3x mb-2"></i>
                    <h5>Connection Failed!</h5>
                </div>
                <p>${result.message}</p>
            </div>
        `);
    }
}

// Update connection status display
function updateConnectionStatus(html) {
    const statusContainer = document.getElementById('connectionStatus');
    statusContainer.innerHTML = html;
}

// Toggle database fields based on selected type
function toggleDatabaseFields() {
    const dbType = document.getElementById('dbType').value;
    const usernameField = document.getElementById('usernameField');
    const hostField = document.getElementById('hostField');
    const portField = document.getElementById('portField');
    const serviceField = document.getElementById('serviceField');
    const oracleConnectionType = document.getElementById('oracleConnectionType');
    const dbNameHelp = document.getElementById('dbNameHelp');
    const serviceHelp = document.getElementById('serviceHelp');
    
    // Reset all fields
    const fieldsToToggle = [usernameField, hostField, portField, serviceField];
    fieldsToToggle.forEach(field => {
        if (field) {
            field.style.display = 'block';
            const input = field.querySelector('input');
            if (input) {
                input.required = false;
                input.disabled = false;
            }
        }
    });
    
    // Hide Oracle connection type by default
    if (oracleConnectionType) {
        oracleConnectionType.style.display = 'none';
    }
    
    switch(dbType) {
        case 'SQLite':
            // Hide network fields for SQLite
            hostField.style.display = 'none';
            portField.style.display = 'none';
            usernameField.style.display = 'none';
            serviceField.style.display = 'none';
            dbNameHelp.textContent = 'Path to SQLite database file (absolute or relative)';
            break;
            
        case 'Oracle':
            // Show all fields, set appropriate labels
            usernameField.querySelector('input').required = true;
            hostField.querySelector('input').required = true;
            portField.querySelector('input').required = true;
            document.getElementById('dbPort').value = document.getElementById('dbPort').value || '1521';
            oracleConnectionType.style.display = 'block';
            dbNameHelp.textContent = 'Database name or SID';
            serviceHelp.textContent = 'Oracle Service Name (e.g., ORCL, XE, XEPDB1)';
            break;
            
        case 'Postgres':
            // Show all fields except service (use dbName for database)
            usernameField.querySelector('input').required = true;
            hostField.querySelector('input').required = true;
            portField.querySelector('input').required = true;
            document.getElementById('dbPort').value = document.getElementById('dbPort').value || '5432';
            dbNameHelp.textContent = 'Database name';
            serviceHelp.textContent = 'Leave empty for PostgreSQL';
            break;
            
        case 'MySQL':
            // Show all fields for MySQL
            usernameField.querySelector('input').required = true;
            hostField.querySelector('input').required = true;
            portField.querySelector('input').required = true;
            document.getElementById('dbPort').value = document.getElementById('dbPort').value || '3306';
            dbNameHelp.textContent = 'Database/Schema name';
            serviceHelp.textContent = 'Leave empty for MySQL (not required)';
            break;
            
        default:
            // Clear help text for unknown types
            if (dbNameHelp) dbNameHelp.textContent = 'Database name';
            if (serviceHelp) serviceHelp.textContent = 'Service name or instance';
            break;
    }
}

// Toggle password visibility
function togglePasswordVisibility(inputId) {
    const input = document.getElementById(inputId);
    const icon = input.nextElementSibling;
    
    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash');
    } else {
        input.type = 'password';
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
    }
}

// Load active connections
function loadActiveConnections() {
    fetch(`/env_config/get_active_connections?app_runtime_id=${app_runtime_id}`)
        .then(response => response.json())
        .then(data => {
            activeConnections = data;
            renderActiveConnections(data);
            // Re-render environments to update connection status
            if (allEnvironments.length > 0) {
                renderEnvironments(allEnvironments);
            }
        })
        .catch(error => {
            console.error('Error loading active connections:', error);
        });
}

// Render active connections
function renderActiveConnections(connections) {
    const container = document.getElementById('activeConnections');
    const noConnectionsMessage = document.getElementById('noConnectionsMessage');
    
    container.innerHTML = '';
    
    if (Object.keys(connections).length === 0) {
        noConnectionsMessage.classList.remove('d-none');
        return;
    }
    
    noConnectionsMessage.classList.add('d-none');
    
    for (const [handle, details] of Object.entries(connections)) {
        const envName = details.env_name || 'Unknown Environment';
        const dbDisplayName = details.db_display_name || 'Unknown Database';
        
        container.innerHTML += `
            <div class="connection-item">
                <div class="d-flex justify-content-between">
                    <div>
                        <strong>${envName}</strong>
                        <div class="connection-info">
                            <span><i class="fas fa-database me-1"></i> ${dbDisplayName}</span>
                        </div>
                        <div class="connection-info">
                            <span><i class="fas fa-key me-1"></i> ${handle}</span>
                        </div>
                    </div>
                    <div>
                        <span class="connection-badge connection-active">Active</span>
                    </div>
                </div>
                <div class="connection-info mt-2">
                    <span><i class="far fa-clock me-1"></i> Created: ${details.created}</span>
                </div>
            </div>
        `;
    }
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