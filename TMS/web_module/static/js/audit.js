let allForms = [];
let filteredForms = [];
let currentPage = 1;
const itemsPerPage = 50;
let sortColumn = 'entry_num';
let sortDirection = 'asc';

// Load forms on page load
window.addEventListener('DOMContentLoaded', () => {
    loadForms();
    document.getElementById('searchInput').addEventListener('input', debounce(applyFilters, 300));
    document.getElementById('formTypeFilter').addEventListener('change', applyFilters);
});

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

async function loadForms() {
    const loading = document.getElementById('loading');
    const table = document.getElementById('formsTable');
    const errorContainer = document.getElementById('errorContainer');
    
    loading.style.display = 'block';
    table.style.display = 'none';
    errorContainer.innerHTML = '';
    
    try {
        const response = await fetch('/api/module/audit/forms', {
            credentials: 'include'
        });
        
        if (response.status === 401) {
            window.location.href = '/login';
            return;
        }
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            allForms = data.forms;
            applyFilters();
        } else {
            throw new Error(data.message || 'Failed to load forms');
        }
    } catch (error) {
        errorContainer.innerHTML = `<div class="error">Error loading forms: ${error.message}</div>`;
        loading.style.display = 'none';
    }
}

function applyFilters() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const formTypeFilter = document.getElementById('formTypeFilter').value;
    
    filteredForms = allForms.filter(form => {
        const matchesSearch = !searchTerm || 
            form.form_number.toLowerCase().includes(searchTerm) ||
            form.ms_party.toLowerCase().includes(searchTerm) ||
            form.created_by.toLowerCase().includes(searchTerm) ||
            form.edited_by.toLowerCase().includes(searchTerm);
        
        const matchesType = !formTypeFilter || form.form_type === formTypeFilter;
        
        return matchesSearch && matchesType;
    });
    
    currentPage = 1;
    renderTable();
}

function sortTable(column) {
    if (sortColumn === column) {
        sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
        sortColumn = column;
        sortDirection = 'asc';
    }
    
    filteredForms.sort((a, b) => {
        let aVal = a[column] || '';
        let bVal = b[column] || '';
        
        if (column === 'entry_num') {
            aVal = parseInt(aVal) || 0;
            bVal = parseInt(bVal) || 0;
        }
        
        if (typeof aVal === 'string') {
            aVal = aVal.toLowerCase();
            bVal = bVal.toLowerCase();
        }
        
        if (sortDirection === 'asc') {
            return aVal > bVal ? 1 : aVal < bVal ? -1 : 0;
        } else {
            return aVal < bVal ? 1 : aVal > bVal ? -1 : 0;
        }
    });
    
    renderTable();
}

function renderTable() {
    const tbody = document.getElementById('formsTableBody');
    const table = document.getElementById('formsTable');
    const loading = document.getElementById('loading');
    const pagination = document.getElementById('pagination');
    
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const pageForms = filteredForms.slice(startIndex, endIndex);
    
    tbody.innerHTML = '';
    
    pageForms.forEach(form => {
        const row = document.createElement('tr');
        row.onclick = () => viewFormDetail(form.form_type, form.form_id);
        
        const badgeClass = `badge-${form.form_type.replace('_', '-')}`;
        const formTypeLabel = form.form_type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
        
        row.innerHTML = `
            <td>${form.entry_num}</td>
            <td><span class="form-type-badge ${badgeClass}">${formTypeLabel}</span></td>
            <td>${form.form_number}</td>
            <td>${form.ms_party || '-'}</td>
            <td>${form.created_by || '-'}</td>
            <td>${form.edited_by || '-'}</td>
            <td>${form.document_date ? form.document_date.split('T')[0] : '-'}</td>
        `;
        tbody.appendChild(row);
    });
    
    loading.style.display = 'none';
    table.style.display = 'table';
    
    // Update pagination
    const totalPages = Math.ceil(filteredForms.length / itemsPerPage);
    if (totalPages > 1) {
        pagination.style.display = 'flex';
        document.getElementById('pageInfo').textContent = `Page ${currentPage} of ${totalPages} (${filteredForms.length} total)`;
        document.getElementById('prevBtn').disabled = currentPage === 1;
        document.getElementById('nextBtn').disabled = currentPage === totalPages;
    } else {
        pagination.style.display = 'none';
    }
    
    // Update sort indicators
    document.querySelectorAll('th').forEach(th => {
        th.classList.remove('sort-asc', 'sort-desc');
    });
    const headerCells = document.querySelectorAll('th');
    const columnIndex = ['entry_num', 'form_type', 'form_number', 'ms_party', 'created_by', 'edited_by', 'document_date'].indexOf(sortColumn);
    if (columnIndex >= 0 && headerCells[columnIndex]) {
        headerCells[columnIndex].classList.add(sortDirection === 'asc' ? 'sort-asc' : 'sort-desc');
    }
}

function changePage(direction) {
    const totalPages = Math.ceil(filteredForms.length / itemsPerPage);
    const newPage = currentPage + direction;
    if (newPage >= 1 && newPage <= totalPages) {
        currentPage = newPage;
        renderTable();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

function viewFormDetail(formType, formId) {
    window.location.href = `/audit/view/${formType}/${formId}`;
}

async function logout() {
    try {
        const response = await fetch('/api/module/logout', {
            method: 'POST',
            credentials: 'include'
        });
        if (response.ok) {
            window.location.href = '/login';
        }
    } catch (error) {
        console.error('Logout error:', error);
        window.location.href = '/login';
    }
}
