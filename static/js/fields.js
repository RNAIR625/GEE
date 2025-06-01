// Global variables for field management
let currentDeleteId = null;
let fieldModal = null;
let deleteModal = null;
let currentFieldPage = 1;
let currentFieldSearch = '';
let currentFieldClassFilter = '';

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap modals
    const fieldModalElement = document.getElementById('fieldModal');
    if (fieldModalElement) {
        fieldModal = new bootstrap.Modal(fieldModalElement);
    }
    
    const deleteModalElement = document.getElementById('deleteModal');
    if (deleteModalElement) {
        deleteModal = new bootstrap.Modal(deleteModalElement);
    }
    
    // Load initial data
    loadFields();
    loadFieldClasses();
    loadFilterClasses();
});

// Load field classes for the form dropdown
function loadFieldClasses() {
    fetch('/fields/get_field_classes')
        .then(response => response.json())
        .then(data => {
            const select = document.getElementById('fieldClass');
            select.innerHTML = '<option value="">Select Class</option>';
            data.forEach(cls => {
                select.innerHTML += `<option value="${cls.GFC_ID}">${cls.FIELD_CLASS_NAME}</option>`;
            });
        })
        .catch(error => {
            console.error('Error loading field classes:', error);
            showToast('Error', 'Failed to load field classes', 'error');
        });
}

// Load field classes for the filter dropdown
function loadFilterClasses() {
    fetch('/fields/get_field_classes')
        .then(response => response.json())
        .then(data => {
            const select = document.getElementById('filterFieldClass');
            select.innerHTML = '<option value="">All Classes</option>';
            data.forEach(cls => {
                select.innerHTML += `<option value="${cls.GFC_ID}">${cls.FIELD_CLASS_NAME}</option>`;
            });
        })
        .catch(error => {
            console.error('Error loading filter classes:', error);
        });
}

// Load all fields
function loadFields(page = 1, search = '', classFilter = '') {
    currentFieldPage = page;
    currentFieldSearch = search;
    currentFieldClassFilter = classFilter;
    
    let url = `/fields/get_fields?page=${page}&per_page=10`;
    if (search) {
        url += `&search=${encodeURIComponent(search)}`;
    }
    if (classFilter) {
        url += `&class_filter=${encodeURIComponent(classFilter)}`;
    }
    
    fetch(url)
        .then(response => response.json())
        .then(response => {
            const data = response.data;
            const pagination = response.pagination;
            
            renderFields(data);
            updateFieldPaginationControls(pagination);
        })
        .catch(error => {
            console.error('Error loading fields:', error);
            showToast('Error', 'Failed to load fields', 'error');
        });
}

// Render fields to the table
function renderFields(fields) {
    const tableBody = document.getElementById('fieldTableBody');
    tableBody.innerHTML = '';
    
    fields.forEach(field => {
        const className = field.FIELD_CLASS_NAME || 'No Class';
        const row = `
            <tr>
                <td>
                    <input type="checkbox" class="field-checkbox" value="${field.GF_ID}" onchange="updateBulkDeleteFieldsButton()">
                </td>
                <td>${field.GF_NAME}</td>
                <td>
                    <span class="badge bg-secondary">${className}</span>
                </td>
                <td>${field.GF_TYPE}</td>
                <td>${field.GF_SIZE || ''}</td>
                <td>${field.GF_PRECISION_SIZE || ''}</td>
                <td>${field.GF_DEFAULT_VALUE || ''}</td>
                <td>${field.GF_DESCRIPTION || ''}</td>
                <td class="action-buttons">
                    <button class="btn btn-warning btn-sm" onclick="editField(${JSON.stringify(field).replace(/"/g, '&quot;')})">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-danger btn-sm" onclick="deleteField(${field.GF_ID})">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `;
        tableBody.innerHTML += row;
    });

    // Update field count
    document.getElementById('fieldCount').textContent = `${fields.length} fields`;
}

// Open modal for creating new field
function openNewFieldModal() {
    document.getElementById('modalTitle').textContent = 'Add New Field';
    document.getElementById('fieldForm').reset();
    document.getElementById('gfId').value = '';
    fieldModal.show();
}

// Open modal for editing existing field
function editField(field) {
    document.getElementById('modalTitle').textContent = 'Edit Field';
    document.getElementById('gfId').value = field.GF_ID;
    document.getElementById('fieldClass').value = field.GFC_ID || '';
    document.getElementById('fieldName').value = field.GF_NAME;
    document.getElementById('fieldType').value = field.GF_TYPE;
    document.getElementById('fieldSize').value = field.GF_SIZE || '';
    document.getElementById('fieldPrecision').value = field.GF_PRECISION_SIZE || '';
    document.getElementById('fieldDefault').value = field.GF_DEFAULT_VALUE || '';
    document.getElementById('fieldDescription').value = field.GF_DESCRIPTION || '';
    fieldModal.show();
}

// Save field (create or update)
function saveField() {
    const gfId = document.getElementById('gfId').value;
    const data = {
        gfcId: document.getElementById('fieldClass').value || null,
        fieldName: document.getElementById('fieldName').value,
        type: document.getElementById('fieldType').value,
        size: document.getElementById('fieldSize').value || null,
        precision: document.getElementById('fieldPrecision').value || null,
        defaultValue: document.getElementById('fieldDefault').value || null,
        description: document.getElementById('fieldDescription').value || null
    };

    if (!data.fieldName || !data.type) {
        showToast('Error', 'Field Name and Type are required!', 'error');
        return;
    }

    const method = gfId ? 'PUT' : 'POST';
    const url = gfId ? '/fields/update_field' : '/fields/add_field';
    if (gfId) data.gfId = gfId;

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
            fieldModal.hide();
            loadFields();
            showToast('Success', result.message);
        } else {
            showToast('Error', result.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error saving field:', error);
        showToast('Error', 'Failed to save field', 'error');
    });
}

// Filter fields based on search criteria
function filterFields() {
    const searchTerm = document.getElementById('searchFields').value.toLowerCase();
    const classFilter = document.getElementById('filterFieldClass').value;
    const typeFilter = document.getElementById('filterFieldType').value;
    
    let filteredFields = allFields;
    
    // Apply search filter
    if (searchTerm) {
        filteredFields = filteredFields.filter(field => 
            field.GF_NAME.toLowerCase().includes(searchTerm) || 
            (field.GF_DESCRIPTION && field.GF_DESCRIPTION.toLowerCase().includes(searchTerm)) ||
            (field.FIELD_CLASS_NAME && field.FIELD_CLASS_NAME.toLowerCase().includes(searchTerm))
        );
    }
    
    // Apply class filter
    if (classFilter) {
        filteredFields = filteredFields.filter(field => 
            field.GFC_ID && field.GFC_ID.toString() === classFilter
        );
    }
    
    // Apply type filter
    if (typeFilter) {
        filteredFields = filteredFields.filter(field => field.GF_TYPE === typeFilter);
    }
    
    renderFields(filteredFields);
    
    // Reset checkbox states after filtering
    document.getElementById('selectAllFields').checked = false;
    updateBulkDeleteFieldsButton();
}

// Delete field
function deleteField(gfId) {
    currentDeleteId = gfId;
    deleteModal.show();
}

// Confirm deletion
function confirmDelete() {
    if (!currentDeleteId) return;
    
    fetch(`/fields/delete_field/${currentDeleteId}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            deleteModal.hide();
            loadFields();
            showToast('Success', data.message);
        } else {
            showToast('Error', data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error deleting field:', error);
        showToast('Error', 'Failed to delete field', 'error');
    });
}

// ======================================
// BULK DELETE FUNCTIONALITY
// ======================================

// Toggle all field checkboxes
function toggleAllFields(selectAllCheckbox) {
    const checkboxes = document.querySelectorAll('.field-checkbox');
    checkboxes.forEach(checkbox => {
        checkbox.checked = selectAllCheckbox.checked;
    });
    updateBulkDeleteFieldsButton();
}

// Update bulk delete button based on selected checkboxes
function updateBulkDeleteFieldsButton() {
    const selectedCheckboxes = document.querySelectorAll('.field-checkbox:checked');
    const bulkDeleteBtn = document.getElementById('bulkDeleteFieldsBtn');
    const selectAllCheckbox = document.getElementById('selectAllFields');
    
    if (selectedCheckboxes.length > 0) {
        bulkDeleteBtn.style.display = 'inline-block';
        bulkDeleteBtn.innerHTML = `<i class="fas fa-trash me-2"></i>Delete Selected (${selectedCheckboxes.length})`;
    } else {
        bulkDeleteBtn.style.display = 'none';
    }

    // Update select all checkbox state
    const allCheckboxes = document.querySelectorAll('.field-checkbox');
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

// Bulk delete selected fields
function bulkDeleteFields() {
    const selectedCheckboxes = document.querySelectorAll('.field-checkbox:checked');
    if (selectedCheckboxes.length === 0) {
        showToast('Error', 'Please select fields to delete', 'error');
        return;
    }

    const selectedIds = Array.from(selectedCheckboxes).map(cb => cb.value);
    const confirmMessage = `Are you sure you want to delete ${selectedIds.length} selected field(s)? This action cannot be undone.`;
    
    if (confirm(confirmMessage)) {
        fetch('/fields/bulk_delete_fields', {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                field_ids: selectedIds
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                loadFields();
                document.getElementById('selectAllFields').checked = false;
                updateBulkDeleteFieldsButton();
                showToast('Success', `Successfully deleted ${data.deleted_count} field(s).`);
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

// ======================================
// PAGINATION FUNCTIONS
// ======================================

function updateFieldPaginationControls(pagination) {
    const paginationContainer = document.getElementById('fieldPagination');
    if (!paginationContainer) return;
    
    const { page, per_page, total, total_pages, has_prev, has_next } = pagination;
    
    // Update pagination info
    const paginationInfo = document.getElementById('fieldPaginationInfo');
    if (paginationInfo) {
        const start = (page - 1) * per_page + 1;
        const end = Math.min(page * per_page, total);
        paginationInfo.textContent = `Showing ${start}-${end} of ${total} fields`;
    }
    
    let paginationHtml = '<nav><ul class="pagination justify-content-center">';
    
    // Previous button
    paginationHtml += `
        <li class="page-item ${!has_prev ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="${has_prev ? `changeFieldPage(${page - 1})` : 'return false;'}">
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
                <a class="page-link" href="#" onclick="changeFieldPage(1)">1</a>
            </li>
        `;
        if (startPage > 2) {
            paginationHtml += '<li class="page-item disabled"><span class="page-link">...</span></li>';
        }
    }
    
    for (let i = startPage; i <= endPage; i++) {
        paginationHtml += `
            <li class="page-item ${i === page ? 'active' : ''}">
                <a class="page-link" href="#" onclick="changeFieldPage(${i})">${i}</a>
            </li>
        `;
    }
    
    if (endPage < total_pages) {
        if (endPage < total_pages - 1) {
            paginationHtml += '<li class="page-item disabled"><span class="page-link">...</span></li>';
        }
        paginationHtml += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="changeFieldPage(${total_pages})">${total_pages}</a>
            </li>
        `;
    }
    
    // Next button
    paginationHtml += `
        <li class="page-item ${!has_next ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="${has_next ? `changeFieldPage(${page + 1})` : 'return false;'}">
                Next <i class="fas fa-chevron-right"></i>
            </a>
        </li>
    `;
    
    paginationHtml += '</ul></nav>';
    paginationContainer.innerHTML = paginationHtml;
}

function changeFieldPage(page) {
    loadFields(page, currentFieldSearch, currentFieldClassFilter);
}

function performFieldSearch() {
    const searchInput = document.getElementById('fieldSearch');
    const classFilter = document.getElementById('filterFieldClass');
    const searchTerm = searchInput ? searchInput.value.trim() : '';
    const selectedClass = classFilter ? classFilter.value : '';
    loadFields(1, searchTerm, selectedClass);
}

function clearFieldSearch() {
    const searchInput = document.getElementById('fieldSearch');
    const classFilter = document.getElementById('filterFieldClass');
    if (searchInput) {
        searchInput.value = '';
    }
    if (classFilter) {
        classFilter.value = '';
    }
    loadFields(1, '', '');
}