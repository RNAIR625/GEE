// Global variables for class management
let currentDeleteId = null;
let currentImportStep = 1;
let parsedSwaggerData = null;
let classModal = null;
let deleteModal = null;
let swaggerImportModal = null;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap modals
    console.log('Initializing modals...');
    const classModalElement = document.getElementById('classModal');
    if (classModalElement) {
        console.log('Found classModal element');
        if (typeof bootstrap !== 'undefined') {
            classModal = new bootstrap.Modal(classModalElement);
            console.log('classModal initialized');
        } else {
            console.error('Bootstrap not available');
        }
    } else {
        console.error('classModal element not found');
    }
    
    const deleteModalElement = document.getElementById('deleteModal');
    if (deleteModalElement) {
        deleteModal = new bootstrap.Modal(deleteModalElement);
    }
    
    const swaggerModalElement = document.getElementById('swaggerImportModal');
    if (swaggerModalElement) {
        swaggerImportModal = new bootstrap.Modal(swaggerModalElement);
    }
    
    // Load initial data
    loadClasses();
    loadExistingSwaggerFiles();
    
    // Add event listeners for edit and delete buttons (using event delegation)
    document.addEventListener('click', function(e) {
        if (e.target.closest('.edit-class-btn')) {
            console.log('Edit button clicked');
            const btn = e.target.closest('.edit-class-btn');
            const id = btn.dataset.id;
            const name = btn.dataset.name;
            const type = btn.dataset.type;
            const description = btn.dataset.description;
            const parentId = btn.dataset.parentId;
            console.log('Calling editClass with:', {id, name, type, description, parentId});
            editClass(id, name, type, description, parentId || null);
        }
        
        if (e.target.closest('.delete-class-btn')) {
            console.log('Delete button clicked');
            const btn = e.target.closest('.delete-class-btn');
            const id = btn.dataset.id;
            console.log('Calling deleteClass with id:', id);
            deleteClass(id);
        }
    });
});

// Global pagination variables
let currentPage = 1;
let currentSearch = '';

// Load all classes and display in hierarchical table
function loadClasses(page = 1, search = '') {
    currentPage = page;
    currentSearch = search;
    
    let url = `/classes/get_classes?page=${page}&per_page=10`;
    if (search) {
        url += `&search=${encodeURIComponent(search)}`;
    }
    
    fetch(url)
        .then(response => response.json())
        .then(response => {
            const data = response.data;
            const pagination = response.pagination;
            
            const tableBody = document.getElementById('classTableBody');
            tableBody.innerHTML = '';

            // Separate parent and child classes for hierarchical display
            const parentClasses = data.filter(cls => !cls.PARENT_GFC_ID);
            const childClasses = data.filter(cls => cls.PARENT_GFC_ID);
            
            // Display parent classes first
            parentClasses.forEach(cls => {
                const children = childClasses.filter(child => child.PARENT_GFC_ID === cls.GFC_ID);
                const row = createClassRow(cls, false, children);
                tableBody.innerHTML += row;
                
                // Display child classes underneath parent (initially collapsed)
                children.forEach(child => {
                    const childRow = createClassRow(child, true, [], cls.GFC_ID);
                    tableBody.innerHTML += childRow;
                });
            });
            
            // Display orphaned child classes (those whose parent was deleted)
            const orphanedChildren = childClasses.filter(child => 
                !parentClasses.find(parent => parent.GFC_ID === child.PARENT_GFC_ID)
            );
            orphanedChildren.forEach(cls => {
                const row = createClassRow(cls, false, []);
                tableBody.innerHTML += row;
            });
            
            // Update pagination controls
            updatePaginationControls(pagination);
        })
        .catch(error => {
            console.error('Error loading classes:', error);
            showToast('Error', 'Failed to load field classes', 'error');
        });
}

// Create a table row for a class (parent or child)
function createClassRow(cls, isChild, children = [], parentId = null) {
    const childCount = children.length;
    const hasChildren = childCount > 0;
    const parentDisplay = cls.PARENT_CLASS_NAME ? cls.PARENT_CLASS_NAME : (isChild ? '<em>Missing Parent</em>' : '');
    
    if (isChild) {
        // Child row
        return `
            <tr class="child-class-row hidden" data-parent-id="${parentId}" data-class-id="${cls.GFC_ID}">
                <td>
                    <input type="checkbox" class="class-checkbox" value="${cls.GFC_ID}" onchange="updateBulkDeleteButton()">
                </td>
                <td>
                    <div class="child-class-content">
                        <i class="fas fa-level-down-alt me-2 text-muted"></i>
                        ${cls.FIELD_CLASS_NAME}
                    </div>
                </td>
                <td>${cls.CLASS_TYPE}</td>
                <td>${parentDisplay}</td>
                <td></td>
                <td>${cls.DESCRIPTION || ''}</td>
                <td class="action-buttons">
                    <button class="btn btn-warning btn-sm" onclick="handleEditClass('${cls.GFC_ID}', '${cls.FIELD_CLASS_NAME.replace(/'/g, "\\'")}', '${cls.CLASS_TYPE}', '${(cls.DESCRIPTION || '').replace(/'/g, "\\'")}', '${cls.PARENT_GFC_ID || ''}')">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-danger btn-sm" onclick="handleDeleteClass('${cls.GFC_ID}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `;
    } else {
        // Parent row
        const expandIcon = hasChildren ? 'fa-chevron-right' : '';
        const expandClass = hasChildren ? 'expandable-row' : '';
        const clickHandler = hasChildren ? `onclick="toggleChildren(this, ${cls.GFC_ID})"` : '';
        
        return `
            <tr class="parent-class-row ${expandClass}" data-class-id="${cls.GFC_ID}" ${clickHandler}>
                <td>
                    <input type="checkbox" class="class-checkbox" value="${cls.GFC_ID}" onchange="updateBulkDeleteButton()">
                </td>
                <td>
                    <div class="parent-class-content">
                        ${hasChildren ? `<i class="fas ${expandIcon} me-2 expand-icon"></i>` : ''}
                        <strong>${cls.FIELD_CLASS_NAME}</strong>
                    </div>
                </td>
                <td>${cls.CLASS_TYPE}</td>
                <td>${parentDisplay}</td>
                <td>${hasChildren ? `<span class="badge bg-info">${childCount} child${childCount !== 1 ? 'ren' : ''}</span>` : ''}</td>
                <td>${cls.DESCRIPTION || ''}</td>
                <td class="action-buttons">
                    <button class="btn btn-warning btn-sm" onclick="handleEditClass('${cls.GFC_ID}', '${cls.FIELD_CLASS_NAME.replace(/'/g, "\\'")}', '${cls.CLASS_TYPE}', '${(cls.DESCRIPTION || '').replace(/'/g, "\\'")}', '${cls.PARENT_GFC_ID || ''}')">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-danger btn-sm" onclick="handleDeleteClass('${cls.GFC_ID}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `;
    }
}

// Toggle child rows visibility
function toggleChildren(element, parentId) {
    const icon = element.querySelector('.expand-icon');
    const childRows = document.querySelectorAll(`tr[data-parent-id="${parentId}"]`);
    
    if (icon.classList.contains('fa-chevron-right')) {
        // Expand - show children
        icon.classList.remove('fa-chevron-right');
        icon.classList.add('fa-chevron-down');
        childRows.forEach(row => row.classList.remove('hidden'));
    } else {
        // Collapse - hide children
        icon.classList.remove('fa-chevron-down');
        icon.classList.add('fa-chevron-right');
        childRows.forEach(row => row.classList.add('hidden'));
    }
}

// Show the modal for adding a new class
function showAddClassModal() {
    console.log('showAddClassModal called');
    document.getElementById('classModalTitle').textContent = 'Add New Field Class';
    document.getElementById('classForm').reset();
    document.getElementById('classId').value = '';
    
    // Load parent classes for selection
    loadParentClassOptions();
    
    if (classModal) {
        console.log('Showing modal');
        classModal.show();
    } else {
        console.error('classModal is not initialized');
    }
}

// Alias function for template compatibility
function openNewClassModal() {
    console.log('openNewClassModal called');
    showAddClassModal();
}

// Toggle all class checkboxes
function toggleAllClasses(masterCheckbox) {
    const checkboxes = document.querySelectorAll('.class-checkbox');
    checkboxes.forEach(checkbox => {
        checkbox.checked = masterCheckbox.checked;
    });
    updateBulkDeleteButton();
}

// Alias for Swagger import modal
function openSwaggerImportModal() {
    showSwaggerImportModal();
}

// Expand all parent classes
function expandAllParents() {
    const parentRows = document.querySelectorAll('.parent-class-row.expandable-row');
    parentRows.forEach(row => {
        const icon = row.querySelector('.expand-icon');
        const parentId = row.dataset.classId;
        if (icon && icon.classList.contains('fa-chevron-right')) {
            toggleChildren(row, parentId);
        }
    });
}

// Collapse all parent classes
function collapseAllParents() {
    const parentRows = document.querySelectorAll('.parent-class-row.expandable-row');
    parentRows.forEach(row => {
        const icon = row.querySelector('.expand-icon');
        const parentId = row.dataset.classId;
        if (icon && icon.classList.contains('fa-chevron-down')) {
            toggleChildren(row, parentId);
        }
    });
}

// Bulk delete classes
function bulkDeleteClasses() {
    showBulkDelete();
}

// Swagger import function aliases
function handleFileSelect() {
    console.log('handleFileSelect called');
    const fileInput = document.getElementById('swaggerFile');
    const nextBtn = document.getElementById('nextStepBtn');
    
    if (fileInput && fileInput.files.length > 0) {
        console.log('File selected:', fileInput.files[0].name);
        // Enable Next button when file is selected
        if (nextBtn) {
            nextBtn.disabled = false;
            console.log('Next button enabled');
        }
        // Clear existing file selection
        const existingFileSelect = document.getElementById('existingSwaggerFiles');
        if (existingFileSelect) {
            existingFileSelect.value = '';
        }
    } else {
        console.log('No file selected');
        if (nextBtn) {
            nextBtn.disabled = true;
        }
    }
}

function handleExistingFileSelect() {
    console.log('handleExistingFileSelect called');
    const existingFileSelect = document.getElementById('existingSwaggerFiles');
    const nextBtn = document.getElementById('nextStepBtn');
    
    if (existingFileSelect && existingFileSelect.value !== '') {
        console.log('Existing file selected:', existingFileSelect.value);
        // Enable Next button when existing file is selected
        if (nextBtn) {
            nextBtn.disabled = false;
            console.log('Next button enabled for existing file');
        }
        // Clear file input
        const fileInput = document.getElementById('swaggerFile');
        if (fileInput) {
            fileInput.value = '';
        }
    } else {
        console.log('No existing file selected');
        // Disable Next button if no selection
        if (nextBtn) {
            nextBtn.disabled = true;
        }
    }
}

function previousStep() {
    goBackStep();
}

function nextStep() {
    // Navigate to next step based on current step
    if (currentImportStep === 1) {
        parseSwaggerFile();
    } else if (currentImportStep === 2) {
        proceedToImport();
    }
}

function performImport() {
    executeImport();
}

// Wrapper functions to handle onclick events with proper escaping
function handleEditClass(id, name, type, description, parentId) {
    console.log('handleEditClass called with:', {id, name, type, description, parentId});
    editClass(id, name, type, description, parentId === '' ? null : parentId);
}

function handleDeleteClass(id) {
    console.log('handleDeleteClass called with id:', id);
    deleteClass(id);
}

// Show the modal for editing an existing class
function editClass(id, name, type, description, parentId) {
    document.getElementById('classModalTitle').textContent = 'Edit Field Class';
    document.getElementById('classId').value = id;
    document.getElementById('className').value = name;
    document.getElementById('classType').value = type;
    document.getElementById('classDescription').value = description;
    
    // Load parent classes for selection
    loadParentClassOptions(parentId);
    
    classModal.show();
}

// Save class (handles both add and edit)
function saveClass() {
    console.log('saveClass called');
    const classId = document.getElementById('classId').value;
    const className = document.getElementById('className').value.trim();
    const classType = document.getElementById('classType').value;
    const classDescription = document.getElementById('classDescription').value.trim();
    const parentClass = document.getElementById('parentClass').value;
    
    if (!className) {
        showToast('Error', 'Class name is required', 'error');
        return;
    }
    
    if (!classType) {
        showToast('Error', 'Class type is required', 'error');
        return;
    }
    
    const data = {
        className: className,
        type: classType,
        description: classDescription,
        parentGfcId: parentClass || null
    };
    
    const isEdit = classId && classId !== '';
    const url = isEdit ? '/classes/update_class' : '/classes/add_class';
    const method = isEdit ? 'PUT' : 'POST';
    
    if (isEdit) {
        data.gfcId = classId;
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
            showToast('Success', result.message);
            classModal.hide();
            loadClasses(); // Reload the table
        } else {
            showToast('Error', result.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error saving class:', error);
        showToast('Error', 'An error occurred while saving the class', 'error');
    });
}

// Load parent class options for dropdown
function loadParentClassOptions(selectedParentId = null) {
    fetch('/classes/get_classes')
        .then(response => response.json())
        .then(data => {
            const parentSelect = document.getElementById('parentClass');
            parentSelect.innerHTML = '<option value="">-- No Parent (Root Class) --</option>';
            
            // Only show classes that don't have parents themselves (to avoid deep nesting)
            const rootClasses = data.filter(cls => !cls.PARENT_GFC_ID);
            
            rootClasses.forEach(cls => {
                const option = document.createElement('option');
                option.value = cls.GFC_ID;
                option.textContent = cls.FIELD_CLASS_NAME;
                if (selectedParentId && cls.GFC_ID == selectedParentId) {
                    option.selected = true;
                }
                parentSelect.appendChild(option);
            });
        })
        .catch(error => {
            console.error('Error loading parent classes:', error);
        });
}

// Submit the class form
function submitClassForm() {
    const form = document.getElementById('classForm');
    const formData = new FormData(form);
    
    const classData = {
        className: formData.get('className'),
        type: formData.get('classType'),
        description: formData.get('classDescription'),
        parentGfcId: formData.get('parentGfcId') || null
    };
    
    const classId = document.getElementById('classId').value;
    const isEdit = classId !== '';
    
    if (isEdit) {
        classData.gfcId = parseInt(classId);
    }
    
    const url = isEdit ? '/classes/update_class' : '/classes/add_class';
    const method = isEdit ? 'PUT' : 'POST';
    
    fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(classData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Success', data.message, 'success');
            classModal.hide();
            loadClasses();
        } else {
            showToast('Error', data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Error', 'Failed to save class', 'error');
    });
}

// Delete a class with confirmation
function deleteClass(id) {
    currentDeleteId = id;
    
    // Show the modal with loading state
    showDeleteStates('loading');
    deleteModal.show();
    
    // Load deletion information
    loadDeletionInfo(id);
}

// Show different states in the delete modal
function showDeleteStates(state) {
    const loadingState = document.getElementById('deleteLoadingState');
    const informationState = document.getElementById('deleteInformation');
    const errorState = document.getElementById('deleteErrorState');
    const confirmBtn = document.getElementById('confirmDeleteBtn');
    
    // Hide all states
    loadingState.classList.add('d-none');
    informationState.classList.add('d-none');
    errorState.classList.add('d-none');
    
    // Show appropriate state
    switch(state) {
        case 'loading':
            loadingState.classList.remove('d-none');
            confirmBtn.disabled = true;
            break;
        case 'information':
            informationState.classList.remove('d-none');
            // Button will be enabled based on checkbox state
            break;
        case 'error':
            errorState.classList.remove('d-none');
            confirmBtn.disabled = true;
            break;
    }
}

// Load deletion information from the server
function loadDeletionInfo(classId) {
    fetch(`/classes/get_class_deletion_info/${classId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                populateDeletionInfo(data);
                showDeleteStates('information');
            } else {
                document.getElementById('deleteErrorMessage').textContent = data.message;
                showDeleteStates('error');
            }
        })
        .catch(error => {
            console.error('Error loading deletion info:', error);
            document.getElementById('deleteErrorMessage').textContent = 'Failed to load deletion information.';
            showDeleteStates('error');
        });
}

// Populate the deletion information in the modal
function populateDeletionInfo(data) {
    const fieldClass = data.field_class;
    const totals = data.totals;
    
    // Set class name
    document.getElementById('deleteClassName').textContent = fieldClass.FIELD_CLASS_NAME;
    
    // Update summary stats
    document.getElementById('totalFieldsCount').textContent = totals.total_fields_count;
    document.getElementById('childClassesCount').textContent = totals.child_classes_count;
    document.getElementById('childFieldsCount').textContent = totals.child_fields_count;
    document.getElementById('rulesUsingCount').textContent = totals.rules_using_count;
    
    // Update header counts
    document.getElementById('fieldsCountInHeader').textContent = totals.fields_count;
    document.getElementById('childClassesCountInHeader').textContent = totals.child_classes_count;
    document.getElementById('rulesCountInHeader').textContent = totals.rules_using_count;
    
    // Populate fields list
    populateFieldsList(data.fields);
    
    // Populate child classes list
    populateChildClassesList(data.child_classes);
    
    // Populate rules list
    populateRulesList(data.rules_using_class);
    
    // Show/hide sections based on content
    toggleSection('fieldsSection', totals.fields_count > 0);
    toggleSection('childClassesSection', totals.child_classes_count > 0);
    toggleSection('rulesSection', totals.rules_using_count > 0);
    
    // Reset checkbox and button state
    const checkbox = document.getElementById('confirmDeletionCheckbox');
    const confirmBtn = document.getElementById('confirmDeleteBtn');
    checkbox.checked = false;
    confirmBtn.disabled = true;
    
    // Add checkbox event listener
    checkbox.onchange = function() {
        confirmBtn.disabled = !this.checked;
    };
}

// Populate the fields list
function populateFieldsList(fields) {
    const container = document.getElementById('fieldsToDeleteList');
    container.innerHTML = '';
    
    if (fields.length === 0) {
        container.innerHTML = '<div class="list-group-item text-muted">No fields to delete</div>';
        return;
    }
    
    fields.forEach(field => {
        const item = document.createElement('div');
        item.className = 'list-group-item d-flex justify-content-between align-items-start';
        item.innerHTML = `
            <div class="ms-2 me-auto">
                <div class="fw-bold">${field.GF_NAME}</div>
                <small class="text-muted">${field.GF_TYPE} - ${field.GF_DESCRIPTION || 'No description'}</small>
            </div>
            <span class="badge bg-danger rounded-pill">${field.GF_TYPE}</span>
        `;
        container.appendChild(item);
    });
}

// Populate the child classes list
function populateChildClassesList(childClasses) {
    const container = document.getElementById('childClassesToDeleteList');
    container.innerHTML = '';
    
    if (childClasses.length === 0) {
        container.innerHTML = '<div class="list-group-item text-muted">No child classes to delete</div>';
        return;
    }
    
    childClasses.forEach(childClass => {
        const item = document.createElement('div');
        item.className = 'list-group-item d-flex justify-content-between align-items-start';
        item.innerHTML = `
            <div class="ms-2 me-auto">
                <div class="fw-bold">${childClass.FIELD_CLASS_NAME}</div>
                <small class="text-muted">${childClass.CLASS_TYPE}</small>
            </div>
            <span class="badge bg-warning rounded-pill">${childClass.FIELD_COUNT} fields</span>
        `;
        container.appendChild(item);
    });
}

// Populate the rules list
function populateRulesList(rules) {
    const container = document.getElementById('rulesToUnlinkList');
    container.innerHTML = '';
    
    if (rules.length === 0) {
        container.innerHTML = '<div class="list-group-item text-muted">No rules using this field class</div>';
        return;
    }
    
    rules.forEach(rule => {
        const item = document.createElement('div');
        item.className = 'list-group-item d-flex justify-content-between align-items-start';
        item.innerHTML = `
            <div class="ms-2 me-auto">
                <div class="fw-bold">${rule.RULE_NAME}</div>
                <small class="text-muted">ID: ${rule.RULE_ID}</small>
            </div>
            <span class="badge bg-secondary rounded-pill">${rule.RULE_TYPE}</span>
        `;
        container.appendChild(item);
    });
}

// Toggle section visibility
function toggleSection(sectionId, show) {
    const section = document.getElementById(sectionId);
    if (section) {
        section.style.display = show ? 'block' : 'none';
    }
}

// Confirm deletion with enhanced functionality
function confirmDelete() {
    if (!currentDeleteId) {
        showToast('Error', 'No class selected for deletion', 'error');
        return;
    }
    
    const confirmBtn = document.getElementById('confirmDeleteBtn');
    confirmBtn.disabled = true;
    confirmBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Deleting...';
    
    fetch(`/classes/delete_class_with_fields/${currentDeleteId}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Success', data.message, 'success');
            deleteModal.hide();
            loadClasses();
            
            // Log deletion details for debugging
            console.log('Deletion completed:', data.deleted_items);
        } else {
            showToast('Error', data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Error', 'Failed to delete field class', 'error');
    })
    .finally(() => {
        // Reset button state
        confirmBtn.disabled = false;
        confirmBtn.innerHTML = '<i class="fas fa-trash me-2"></i>Delete Field Class';
    });
}

// Update bulk delete button state
function updateBulkDeleteButton() {
    const checkedBoxes = document.querySelectorAll('.class-checkbox:checked');
    const bulkDeleteBtn = document.getElementById('bulkDeleteBtn');
    
    if (bulkDeleteBtn) {
        bulkDeleteBtn.disabled = checkedBoxes.length === 0;
    }
}

// Show bulk delete confirmation
function showBulkDelete() {
    const checkedBoxes = document.querySelectorAll('.class-checkbox:checked');
    const count = checkedBoxes.length;
    
    if (count === 0) {
        showToast('Warning', 'Please select at least one class to delete', 'warning');
        return;
    }
    
    document.getElementById('deleteMessage').textContent = 
        `Are you sure you want to delete ${count} selected field class${count > 1 ? 'es' : ''}? This action cannot be undone.`;
    deleteModal.show();
    
    // Override the confirm button to handle bulk delete
    document.getElementById('confirmDeleteBtn').onclick = confirmBulkDelete;
}

// Confirm bulk deletion
function confirmBulkDelete() {
    const checkedBoxes = document.querySelectorAll('.class-checkbox:checked');
    const classIds = Array.from(checkedBoxes).map(cb => parseInt(cb.value));
    
    fetch('/classes/bulk_delete_classes', {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ class_ids: classIds })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Success', data.message, 'success');
            deleteModal.hide();
            loadClasses();
            updateBulkDeleteButton();
        } else {
            showToast('Error', data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Error', 'Failed to delete classes', 'error');
    });
    
    // Reset the confirm button back to single delete
    document.getElementById('confirmDeleteBtn').onclick = confirmDelete;
}

// Show Swagger import modal
function showSwaggerImportModal() {
    console.log('showSwaggerImportModal called');
    
    if (!swaggerImportModal) {
        console.log('Swagger import modal not initialized, initializing now');
        const swaggerModalElement = document.getElementById('swaggerImportModal');
        if (swaggerModalElement && typeof bootstrap !== 'undefined') {
            swaggerImportModal = new bootstrap.Modal(swaggerModalElement);
        } else {
            console.error('Cannot initialize swagger modal - element or bootstrap not found');
            return;
        }
    }
    
    currentImportStep = 1;
    showImportStep(1);
    
    // Reset form state
    const fileInput = document.getElementById('swaggerFile');
    const existingFileSelect = document.getElementById('existingSwaggerFiles');
    const nextBtn = document.getElementById('nextStepBtn');
    
    if (fileInput) fileInput.value = '';
    if (existingFileSelect) existingFileSelect.value = '';
    if (nextBtn) nextBtn.disabled = true;
    
    console.log('Showing swagger modal');
    swaggerImportModal.show();
}

// Load existing Swagger files
function loadExistingSwaggerFiles() {
    fetch('/classes/get_swagger_files')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const fileSelect = document.getElementById('existingSwaggerFiles');
                if (fileSelect) {
                    // Clear existing options except the first one
                    fileSelect.innerHTML = '<option value="">Select existing file...</option>';
                    
                    if (data.files.length === 0) {
                        const option = document.createElement('option');
                        option.value = '';
                        option.textContent = 'No Swagger files found in temp directory';
                        option.disabled = true;
                        fileSelect.appendChild(option);
                    } else {
                        data.files.forEach(file => {
                            const option = document.createElement('option');
                            option.value = file.path;
                            option.textContent = file.name;
                            fileSelect.appendChild(option);
                        });
                    }
                }
            }
        })
        .catch(error => {
            console.error('Error loading existing files:', error);
        });
}

// Show specific import step
function showImportStep(step) {
    // Hide all steps using Bootstrap classes
    for (let i = 1; i <= 3; i++) {
        const stepDiv = document.getElementById(`step${i}`);
        if (stepDiv) {
            stepDiv.classList.add('d-none');
        }
    }
    
    // Show current step
    const currentStepDiv = document.getElementById(`step${step}`);
    if (currentStepDiv) {
        currentStepDiv.classList.remove('d-none');
    }
    
    // Update button visibility and state
    updateStepButtons(step);
    
    // Update progress indicators
    updateProgressIndicators(step);
    
    currentImportStep = step;
}

// Update step buttons based on current step
function updateStepButtons(step) {
    const prevBtn = document.getElementById('prevStepBtn');
    const nextBtn = document.getElementById('nextStepBtn');
    const importBtn = document.getElementById('importBtn');
    
    // Reset all buttons
    if (prevBtn) {
        prevBtn.style.display = step > 1 ? 'inline-block' : 'none';
    }
    
    if (nextBtn) {
        nextBtn.style.display = step < 3 ? 'inline-block' : 'none';
        nextBtn.disabled = step === 1; // Disabled on step 1 until file is selected
        nextBtn.innerHTML = step === 2 ? 'Review' : 'Next';
    }
    
    if (importBtn) {
        importBtn.style.display = step === 3 ? 'inline-block' : 'none';
    }
}

// Update progress indicators
function updateProgressIndicators(currentStep) {
    for (let i = 1; i <= 3; i++) {
        const indicator = document.querySelector(`.step-indicator[data-step="${i}"]`);
        if (indicator) {
            indicator.classList.remove('active', 'completed');
            if (i < currentStep) {
                indicator.classList.add('completed');
            } else if (i === currentStep) {
                indicator.classList.add('active');
            }
        }
    }
}

// Parse Swagger file
function parseSwaggerFile() {
    console.log('parseSwaggerFile called');
    const fileInput = document.getElementById('swaggerFile');
    const existingFileSelect = document.getElementById('existingSwaggerFiles');
    
    const formData = new FormData();
    
    if (fileInput && fileInput.files.length > 0) {
        console.log('Using uploaded file:', fileInput.files[0].name);
        formData.append('swagger_file', fileInput.files[0]);
    } else if (existingFileSelect && existingFileSelect.value !== '') {
        console.log('Using existing file:', existingFileSelect.value);
        formData.append('existing_file_path', existingFileSelect.value);
    } else {
        console.log('No file selected for parsing');
        showToast('Error', 'Please select a file to import', 'error');
        return;
    }
    
    // Show loading indicator on Next button
    const nextBtn = document.getElementById('nextStepBtn');
    if (nextBtn) {
        nextBtn.disabled = true;
        nextBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Parsing...';
    }
    
    fetch('/classes/parse_swagger', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        console.log('Parse response received:', data);
        
        if (nextBtn) {
            nextBtn.disabled = false;
            nextBtn.innerHTML = 'Next';
        }
        
        if (data.success) {
            console.log('Parse successful, populating preview');
            parsedSwaggerData = data;
            populateSwaggerPreview(data);
            showImportStep(2);
        } else {
            console.log('Parse failed:', data.message);
            showToast('Error', data.message, 'error');
        }
    })
    .catch(error => {
        if (nextBtn) {
            nextBtn.disabled = false;
            nextBtn.innerHTML = 'Next';
        }
        console.error('Error:', error);
        showToast('Error', 'Failed to parse Swagger file', 'error');
    });
}

// Populate the preview with parsed data
function populateSwaggerPreview(data) {
    console.log('populateSwaggerPreview called with data:', data);
    
    // Populate API info in the apiInfo div
    const apiInfoDiv = document.getElementById('apiInfo');
    if (apiInfoDiv) {
        console.log('Populating API info');
        apiInfoDiv.innerHTML = `
            <div><strong>Title:</strong> ${data.api_info.title}</div>
            <div><strong>Description:</strong> ${data.api_info.description}</div>
            <div><strong>Version:</strong> ${data.api_info.version}</div>
        `;
    } else {
        console.log('apiInfo div not found');
    }
    
    // Set suggested class name
    const classNameInput = document.getElementById('importClassName');
    if (classNameInput) {
        classNameInput.value = data.suggested_class_name;
    }
    
    // Populate field classes preview
    const classesPreview = document.getElementById('fieldClassesPreview');
    if (classesPreview) {
        classesPreview.innerHTML = '';
    
    data.field_classes.forEach(fc => {
        const classDiv = document.createElement('div');
        classDiv.className = 'mb-3 p-3 border rounded';
        classDiv.innerHTML = `
            <h6><strong>${fc.name}</strong> <span class="badge bg-secondary">${fc.type}</span></h6>
            <p class="text-muted mb-2">${fc.description}</p>
            <div class="field-list">
                <strong>Fields (${fc.fields.length}):</strong>
                <ul class="list-unstyled ms-3">
                    ${fc.fields.map(field => 
                        `<li><code>${field.name}</code> - ${field.type}${field.description ? ` (${field.description})` : ''}</li>`
                    ).join('')}
                </ul>
            </div>
        `;
        classesPreview.appendChild(classDiv);
    });
    }
    
    // Populate input/output field previews
    populateFieldPreview('inputFieldsPreview', data.input_fields);
    populateFieldPreview('outputFieldsPreview', data.output_fields);
}

// Populate field preview section
function populateFieldPreview(containerId, fields) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    container.innerHTML = '';
    
    if (fields.length === 0) {
        container.innerHTML = '<div class="text-muted">No fields found</div>';
        return;
    }
    
    const table = document.createElement('table');
    table.className = 'table table-sm';
    table.innerHTML = `
        <thead>
            <tr>
                <th>Field Name</th>
                <th>Type</th>
                <th>Class</th>
                <th>Description</th>
            </tr>
        </thead>
        <tbody>
            ${fields.map(field => `
                <tr>
                    <td><code>${field.name}</code></td>
                    <td>${field.type}</td>
                    <td><small class="text-muted">${field.class_name}</small></td>
                    <td>${field.description || ''}</td>
                </tr>
            `).join('')}
        </tbody>
    `;
    container.appendChild(table);
}

// Proceed to import configuration
function proceedToImport() {
    showImportStep(3);
}

// Execute the import
function executeImport() {
    const className = document.getElementById('importClassName').value.trim();
    const cleanupExisting = document.getElementById('cleanupExisting').checked;
    
    if (!className) {
        showToast('Error', 'Please enter a class name', 'error');
        return;
    }
    
    // Show loading
    const importBtn = document.getElementById('importBtn');
    if (importBtn) {
        importBtn.disabled = true;
        importBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Importing...';
    }
    
    const importData = {
        class_name: className,
        cleanup_existing: cleanupExisting,
        swagger_data: parsedSwaggerData
    };
    
    fetch('/classes/import_swagger', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(importData)
    })
    .then(response => response.json())
    .then(data => {
        if (importBtn) {
            importBtn.disabled = false;
            importBtn.innerHTML = '<i class="fas fa-check"></i> Complete Import';
        }
        
        if (data.success) {
            // Show success message with stats
            const statsMessage = `Import completed successfully! 
                Classes created: ${data.stats.classes_created}, 
                Fields created: ${data.stats.fields_created}
                ${data.stats.classes_updated > 0 ? `, Classes updated: ${data.stats.classes_updated}` : ''}
                ${data.stats.fields_deleted > 0 ? `, Fields deleted: ${data.stats.fields_deleted}` : ''}`;
            
            showToast('Success', statsMessage, 'success');
            swaggerImportModal.hide();
            loadClasses();
        } else {
            showToast('Error', data.message, 'error');
        }
    })
    .catch(error => {
        if (importBtn) {
            importBtn.disabled = false;
            importBtn.innerHTML = '<i class="fas fa-check"></i> Complete Import';
        }
        console.error('Error:', error);
        showToast('Error', 'Failed to import Swagger data', 'error');
    });
}

// Go back to previous step
function goBackStep() {
    if (currentImportStep > 1) {
        showImportStep(currentImportStep - 1);
    }
}

// Utility function to show toast notifications
function showToast(title, message, type = 'info') {
    const toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) return;
    
    const toastId = 'toast_' + Date.now();
    const bgClass = type === 'success' ? 'bg-success' : 
                   type === 'error' ? 'bg-danger' : 
                   type === 'warning' ? 'bg-warning' : 'bg-info';
    
    const toastHtml = `
        <div id="${toastId}" class="toast ${bgClass} text-white" role="alert">
            <div class="toast-header ${bgClass} text-white border-0">
                <strong class="me-auto">${title}</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement);
    toast.show();
    
    // Remove toast element after it's hidden
    toastElement.addEventListener('hidden.bs.toast', function() {
        toastElement.remove();
    });
}

// Pagination functions
function updatePaginationControls(pagination) {
    const paginationContainer = document.getElementById('classPagination');
    if (!paginationContainer) return;
    
    const { page, per_page, total, total_pages, has_prev, has_next } = pagination;
    
    // Update pagination info
    const paginationInfo = document.getElementById('classPaginationInfo');
    if (paginationInfo) {
        const start = (page - 1) * per_page + 1;
        const end = Math.min(page * per_page, total);
        paginationInfo.textContent = `Showing ${start}-${end} of ${total} classes`;
    }
    
    let paginationHtml = '<nav><ul class="pagination justify-content-center">';
    
    // Previous button
    paginationHtml += `
        <li class="page-item ${!has_prev ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="${has_prev ? `changePage(${page - 1})` : 'return false;'}">
                <i class="fas fa-chevron-left"></i> Previous
            </a>
        </li>
    `;
    
    // Page numbers
    const startPage = Math.max(1, page - 2);
    const endPage = Math.min(total_pages, page + 2);
    
    if (startPage > 1) {
        paginationHtml += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="changePage(1)">1</a>
            </li>
        `;
        if (startPage > 2) {
            paginationHtml += '<li class="page-item disabled"><span class="page-link">...</span></li>';
        }
    }
    
    for (let i = startPage; i <= endPage; i++) {
        paginationHtml += `
            <li class="page-item ${i === page ? 'active' : ''}">
                <a class="page-link" href="#" onclick="changePage(${i})">${i}</a>
            </li>
        `;
    }
    
    if (endPage < total_pages) {
        if (endPage < total_pages - 1) {
            paginationHtml += '<li class="page-item disabled"><span class="page-link">...</span></li>';
        }
        paginationHtml += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="changePage(${total_pages})">${total_pages}</a>
            </li>
        `;
    }
    
    // Next button
    paginationHtml += `
        <li class="page-item ${!has_next ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="${has_next ? `changePage(${page + 1})` : 'return false;'}">
                Next <i class="fas fa-chevron-right"></i>
            </a>
        </li>
    `;
    
    paginationHtml += '</ul></nav>';
    paginationContainer.innerHTML = paginationHtml;
}

function changePage(page) {
    loadClasses(page, currentSearch);
}

function performSearch() {
    const searchInput = document.getElementById('classSearch');
    const searchTerm = searchInput ? searchInput.value.trim() : '';
    loadClasses(1, searchTerm);
}

function clearSearch() {
    const searchInput = document.getElementById('classSearch');
    if (searchInput) {
        searchInput.value = '';
    }
    loadClasses(1, '');
}