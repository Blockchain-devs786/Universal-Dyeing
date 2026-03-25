// Get form type and ID from URL
const pathParts = window.location.pathname.split('/');
const formType = pathParts[pathParts.length - 2];
const formId = parseInt(pathParts[pathParts.length - 1]);

async function loadFormDetail() {
    const loading = document.getElementById('loading');
    const container = document.getElementById('formContainer');
    const errorContainer = document.getElementById('errorContainer');
    
    try {
        const response = await fetch(`/api/module/audit/form/${formType}/${formId}`, {
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
            loading.style.display = 'none';
            container.innerHTML = renderFormDetail(data.form, data.form_type);
        } else {
            throw new Error(data.message || 'Failed to load form');
        }
    } catch (error) {
        loading.style.display = 'none';
        errorContainer.innerHTML = `<div class="error">Error loading form: ${error.message}</div>`;
    }
}

function renderFormDetail(form, formType) {
    const hasEditHistory = form.edit_log_history && form.edit_log_history.trim() !== '';
    
    if (hasEditHistory) {
        return renderComparisonView(form, formType);
    } else {
        return renderNormalView(form, formType);
    }
}

function renderNormalView(form, formType) {
    let html = `<div class="form-container">`;
    html += `<div class="form-section"><h3>Form Information</h3>`;
    html += renderFormFields(form, formType);
    html += `</div>`;
    
    if (form.items && form.items.length > 0) {
        html += `<div class="form-section"><h3>Items</h3>`;
        html += renderItemsTable(form.items, formType);
        html += `</div>`;
    }
    
    if (form.details && form.details.length > 0) {
        html += `<div class="form-section"><h3>Voucher Details</h3>`;
        html += renderVoucherDetailsTable(form.details, formType);
        html += `</div>`;
    }
    
    html += `</div>`;
    return html;
}

function renderComparisonView(form, formType) {
    // Parse edit log history
    const editLogs = parseEditLog(form.edit_log_history);
    
    let html = `<div class="comparison-container">`;
    
    // Left Panel - Edit Log History
    html += `<div class="comparison-panel">`;
    html += `<h3>Edit Log History</h3>`;
    html += `<div class="edit-log">`;
    editLogs.forEach((log, index) => {
        html += `<div class="edit-log-item">`;
        html += `<strong>Edit #${index + 1}</strong><br>`;
        html += escapeHtml(log);
        html += `</div>`;
    });
    html += `</div>`;
    html += `<div class="form-row"><span class="form-label">Edited By:</span><span class="form-value">${form.edited_by || 'N/A'}</span></div>`;
    html += `</div>`;
    
    // Right Panel - Final Form
    html += `<div class="comparison-panel">`;
    html += `<h3>Final Form (Latest)</h3>`;
    html += renderFormFields(form, formType, false);
    if (form.items && form.items.length > 0) {
        html += renderItemsTable(form.items, formType);
    }
    if (form.details && form.details.length > 0) {
        html += renderVoucherDetailsTable(form.details, formType);
    }
    html += `</div>`;
    
    html += `</div>`;
    return html;
}

function renderFormFields(form, formType, isOriginal = false) {
    let html = '';
    
    const fieldMap = {
        'inward': ['inward_number', 'gp_number', 'sr_number', 'ms_party_name', 'from_party', 'vehicle_number', 'driver_name', 'document_date', 'total_quantity', 'created_by'],
        'outward': ['outward_number', 'gp_number', 'sr_number', 'ms_party_name', 'from_party', 'outward_to', 'vehicle_number', 'driver_name', 'document_date', 'total_quantity', 'created_by'],
        'transfer': ['transfer_number', 'gp_number', 'sr_number', 'ms_party_name', 'from_party', 'transfer_to', 'transfer_to_ms_party_name', 'vehicle_number', 'driver_name', 'document_date', 'total_quantity', 'created_by'],
        'transfer_bn': ['transfer_number', 'gp_number', 'sr_number', 'ms_party_name', 'from_party', 'transfer_to', 'transfer_to_ms_party_name', 'vehicle_number', 'driver_name', 'document_date', 'total_quantity', 'created_by'],
        'invoice': ['invoice_number', 'ms_party_name', 'invoice_date', 'number_of_items', 'discount_amount', 'total_amount', 'created_by'],
        'voucher_cp': ['voucher_no', 'voucher_type', 'voucher_date', 'description', 'total_amount', 'created_by'],
        'voucher_cr': ['voucher_no', 'voucher_type', 'voucher_date', 'description', 'total_amount', 'created_by'],
        'voucher_jv': ['voucher_no', 'voucher_type', 'voucher_date', 'description', 'total_amount', 'created_by']
    };
    
    const fields = fieldMap[formType] || [];
    const labelMap = {
        'inward_number': 'Inward Number', 'outward_number': 'Outward Number', 'transfer_number': 'Transfer Number',
        'invoice_number': 'Invoice Number', 'voucher_no': 'Voucher Number',
        'gp_number': 'GP Number', 'sr_number': 'SR Number',
        'ms_party_name': 'MS Party', 'from_party': 'From Party', 'outward_to': 'Outward To',
        'transfer_to': 'Transfer To', 'transfer_to_ms_party_name': 'Transfer To MS Party',
        'vehicle_number': 'Vehicle Number', 'driver_name': 'Driver Name',
        'document_date': 'Date', 'invoice_date': 'Date', 'voucher_date': 'Date',
        'total_quantity': 'Total Quantity', 'total_amount': 'Total Amount',
        'number_of_items': 'Number of Items', 'discount_amount': 'Discount Amount',
        'voucher_type': 'Voucher Type', 'description': 'Description',
        'created_by': 'Created By', 'edited_by': 'Edited By'
    };
    
    fields.forEach(field => {
        let value = form[field];
        if (value !== undefined && value !== null && value !== '') {
            const label = labelMap[field] || field.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
            html += `<div class="form-row">`;
            html += `<span class="form-label">${label}:</span>`;
            const displayValue = String(formatValue(value));
            html += `<span class="form-value">${escapeHtml(displayValue)}</span>`;
            html += `</div>`;
        }
    });
    
    return html;
}

function renderItemsTable(items, formType) {
    let html = `<table class="items-table">`;
    html += `<thead><tr>`;
    html += `<th>Item Name</th>`;
    html += `<th>Measurement</th>`;
    html += `<th>Quantity</th>`;
    if (formType === 'invoice') {
        html += `<th>Rate</th>`;
        html += `<th>Amount</th>`;
        html += `<th>Outward/Transfer</th>`;
    }
    html += `</tr></thead><tbody>`;
    
    items.forEach(item => {
        html += `<tr>`;
        html += `<td>${escapeHtml(item.item_name)}</td>`;
        html += `<td>${escapeHtml(String(item.measurement))}</td>`;
        html += `<td>${escapeHtml(String(item.quantity))}</td>`;
        if (formType === 'invoice') {
            html += `<td>${escapeHtml(String(item.rate || 0))}</td>`;
            html += `<td>${escapeHtml(String(item.amount || 0))}</td>`;
            html += `<td>${escapeHtml(item.outward_number || item.transfer_number || '-')}</td>`;
        }
        html += `</tr>`;
    });
    
    html += `</tbody></table>`;
    return html;
}

function renderVoucherDetailsTable(details, formType) {
    let html = `<table class="voucher-details-table">`;
    html += `<thead><tr>`;
    html += `<th>Account</th>`;
    html += `<th class="text-right">Debit</th>`;
    html += `<th class="text-right">Credit</th>`;
    html += `</tr></thead><tbody>`;
    
    details.forEach(detail => {
        const accountName = detail.party_name || detail.asset_name || detail.expense_name || detail.vendor_name || 'N/A';
        html += `<tr>`;
        html += `<td>${escapeHtml(accountName)}</td>`;
        html += `<td class="text-right">${detail.debit_amount ? detail.debit_amount.toFixed(2) : '-'}</td>`;
        html += `<td class="text-right">${detail.credit_amount ? detail.credit_amount.toFixed(2) : '-'}</td>`;
        html += `</tr>`;
    });
    
    html += `</tbody></table>`;
    return html;
}

function parseEditLog(editLogHistory) {
    if (!editLogHistory) return [];
    return editLogHistory.split(';').map(log => log.trim()).filter(log => log.length > 0);
}

function formatValue(value) {
    if (typeof value === 'number') {
        return value.toFixed(2);
    }
    // Only split on 'T' if it looks like an ISO datetime (YYYY-MM-DDTHH:MM:SS format)
    if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}T/.test(value)) {
        return value.split('T')[0];
    }
    return value;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
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

// Load form detail on page load
window.addEventListener('DOMContentLoaded', loadFormDetail);
