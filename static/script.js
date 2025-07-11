document.addEventListener('DOMContentLoaded', () => {
    const table = document.getElementById('compliance-table');
    const loading = document.getElementById('loading');
    
    // Initialize all features
    initializeFileUpload();
    initializeTableFeatures();
    initializeSearchAndFilter();
    
    if (loading) {
        // Hide loading animation after page load if not processing
        if (!window.isProcessing) {
            loading.style.display = 'none';
        }
    }

    if (!table) return;

    const headers = table.querySelectorAll('th');
    let sortConfig = { key: null, direction: 'asc' };

    headers.forEach((header, index) => {
        header.addEventListener('click', () => {
            const key = ['parameter', 'actual_value', 'expected_value', 'is_compliant', 'explanation'][index];
            if (sortConfig.key !== key) {
                sortConfig = { key, direction: 'asc' };
            } else {
                sortConfig.direction = sortConfig.direction === 'asc' ? 'desc' : 'asc';
            }

            const rows = Array.from(table.querySelectorAll('tbody tr'));
            rows.sort((a, b) => {
                let aValue = a.cells[index].textContent.trim();
                let bValue = b.cells[index].textContent.trim();

                if (index === 3) { // Compliant column
                    const order = { 'Yes': 1, 'No': 2, '--': 3 };
                    aValue = order[aValue] || 4;
                    bValue = order[bValue] || 4;
                } else {
                    aValue = isNaN(aValue) ? aValue.toLowerCase() : parseFloat(aValue);
                    bValue = isNaN(bValue) ? bValue.toLowerCase() : parseFloat(bValue);
                }

                return sortConfig.direction === 'asc' ? aValue - bValue : bValue - aValue;
            });

            // Update header arrows
            headers.forEach(h => h.classList.remove('asc', 'desc'));
            header.classList.add(sortConfig.direction);

            const tbody = table.querySelector('tbody');
            rows.forEach(row => tbody.appendChild(row));
        });
    });

    // Add initial arrow styling
    headers.forEach(header => {
        header.classList.add('relative');
        header.innerHTML += '<span class="sort-arrow"></span>';
    });

    // Update arrow on sort
    document.querySelectorAll('th').forEach(th => {
        th.addEventListener('click', () => {
            const arrow = th.querySelector('.sort-arrow');
            if (th.classList.contains('asc')) {
                arrow.textContent = ' ↑';
            } else if (th.classList.contains('desc')) {
                arrow.textContent = ' ↓';
            } else {
                arrow.textContent = '';
            }
        });
    });
});

function initializeFileUpload() {
    const form = document.getElementById('upload-form');
    const fileInput = document.getElementById('file');
    const dropZone = document.getElementById('drop-zone');
    const submitBtn = document.getElementById('submit-btn');
    const progressContainer = document.getElementById('progress-container');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');

    if (!form || !fileInput || !dropZone) return;

    form.addEventListener('submit', (e) => {
        if(!fileInput.files.length) {
            e.preventDefault();
            alert('Please select a PDF file to upload.');
            return;
        }
        progressContainer.classList.remove('hidden');
        progressText.textContent = 'Uploading...';

        // Simulate progress (for demo purposes)
        let progress = 0;
        const interval = setInterval(() => {
            progress += 10;
            progressBar.style.width = progress + '%';
            if (progress >= 100) {
                clearInterval(interval);
                progressText.textContent = 'Processing...';
            }
        }, 300);
    });

    dropZone.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', handleFileSelect);

    dropZone.addEventListener('dragover', handleDragOver);
    dropZone.addEventListener('dragleave', handleDragLeave);
    dropZone.addEventListener('drop', handleFileDrop);

    function handleFileSelect(e) {
        const files = e.target.files || e.dataTransfer.files;
        if (files.length) {
            const file = files[0];
            displayFileInfo(file);
            submitBtn.disabled = false;
        }
    }

    function handleDragOver(e) {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.add('drag-over');
    }

    function handleDragLeave(e) {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.remove('drag-over');
    }

    function handleFileDrop(e) {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.remove('drag-over');
        const files = e.dataTransfer.files;
        if (files.length) {
            const file = files[0];
            fileInput.files = files;
            displayFileInfo(file);
            submitBtn.disabled = false;
        }
    }

    function displayFileInfo(file) {
        const fileInfo = document.getElementById('file-info');
        const fileName = document.getElementById('file-name');
        const fileSize = document.getElementById('file-size');

        fileInfo.classList.remove('hidden');
        fileName.textContent = file.name;
        fileSize.textContent = `${(file.size / 1024 / 1024).toFixed(2)} MB`;
        document.getElementById('upload-prompt').classList.add('hidden');
    }
}

function initializeTableFeatures() {
    // Table sorting and event listeners are implemented in main function
}

function initializeSearchAndFilter() {
    const searchInput = document.getElementById('search-input');
    const complianceFilter = document.getElementById('compliance-filter');
    const tableRows = document.querySelectorAll('#compliance-table tbody tr');

    if (!searchInput || !complianceFilter) return;

    searchInput.addEventListener('input', () => filterTable());
    complianceFilter.addEventListener('change', () => filterTable());

    function filterTable() {
        const query = searchInput.value.toLowerCase();
        const filter = complianceFilter.value;

        tableRows.forEach(row => {
            const cells = row.querySelectorAll('td');
            const matchesSearch = [...cells].some(cell => cell.textContent.toLowerCase().includes(query));
            const isCompliant = cells[3].textContent.trim() === 'Yes';

            if (
                (filter === 'all' || (filter === 'compliant' && isCompliant) || (filter === 'non-compliant' && !isCompliant)) &&
                matchesSearch
            ) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    }
}
