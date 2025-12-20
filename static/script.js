function calculateGridLayout(pagesPerSide) {
    if (pagesPerSide === 1) return { cols: 1, rows: 1 };

    // Find best grid (cols * rows >= n)
    // Prioritize low waste, then Aspect Ratio (R >= C for Portrait)

    let best = { cols: 1, rows: pagesPerSide, waste: 0 };
    const candidates = [];

    // Check reasonable column counts
    const limit = Math.ceil(Math.sqrt(pagesPerSide)) + 2;

    for (let c = 1; c <= limit; c++) {
        const r = Math.ceil(pagesPerSide / c);
        const capacity = c * r;
        const waste = capacity - pagesPerSide;

        candidates.push({ cols: c, rows: r, waste: waste });
    }

    // Sort logic matching Python
    // 1. Waste asc
    // 2. Aspect ratio closeness to 1.414 (Portrait)
    candidates.sort((a, b) => {
        if (a.waste !== b.waste) return a.waste - b.waste;

        const ratioA = Math.abs((a.rows / a.cols) - 1.414);
        const ratioB = Math.abs((b.rows / b.cols) - 1.414);
        return ratioA - ratioB;
    });

    return candidates[0];
}

function calculateTotalPages(inputPages, pagesPerSheet) {
    if (inputPages === 0) return pagesPerSheet;
    if (inputPages % pagesPerSheet === 0) return inputPages;
    return (Math.floor(inputPages / pagesPerSheet) + 1) * pagesPerSheet;
}

function getPagePosition(pageNum, isFront, cols, rows, pagesPerSide) {
    const sidePosition = (pageNum - 1) % pagesPerSide;

    if (isFront) {
        const col = sidePosition % cols;
        const row = Math.floor(sidePosition / cols);
        return { col, row };
    } else {
        const baseCol = sidePosition % cols;
        const col = (cols - 1) - baseCol;
        const row = Math.floor(sidePosition / cols);
        return { col, row };
    }
}

function generatePageAssignments(inputPages, pagesPerSheet, pagesPerSide) {
    // SEQUENTIAL N-UP LOGIC
    // We fill the grid positions sequentially with page pairs.
    // Sheet 0 Grid 0: Pair 1 (P1/P2)
    // Sheet 0 Grid 1: Pair 2 (P3/P4)
    // ...

    const capacityPerSheet = pagesPerSide * 2;
    const numSheets = Math.ceil(inputPages / capacityPerSheet);
    const totalCapacity = numSheets * capacityPerSheet;

    const sheets = [];

    // Initialize sheets
    for (let i = 0; i < numSheets; i++) {
        sheets.push({ front: new Array(pagesPerSide), back: new Array(pagesPerSide) });
    }

    // Iterate through sheets and fill them
    for (let s = 0; s < numSheets; s++) {
        for (let gridIdx = 0; gridIdx < pagesPerSide; gridIdx++) {
            // Calculate Global Pair Index
            const globalPairIndex = (s * pagesPerSide) + gridIdx;

            // Front Page (Odd)
            const frontPageNum = (globalPairIndex * 2) + 1;
            // Back Page (Even)
            const backPageNum = (globalPairIndex * 2) + 2;

            sheets[s].front[gridIdx] = frontPageNum;
            sheets[s].back[gridIdx] = backPageNum;
        }
    }

    return { sheets, totalPages: totalCapacity, numSheets };
}

function createGrid(pages, inputPages, isFront, cols, rows, pagesPerSide) {
    const grid = document.createElement('div');
    grid.className = 'grid';
    grid.style.gridTemplateColumns = `repeat(${cols}, 1fr)`;
    grid.style.gridTemplateRows = `repeat(${rows}, 1fr)`;

    const cells = new Array(pagesPerSide);

    pages.forEach((pageNum, idx) => {
        // idx is the Stack Index (0 to N-1)
        // Calculate Logical Position (Row, Col) based on Stack Index
        const logicalRow = Math.floor(idx / cols);
        const logicalCol = idx % cols;

        // Determine Physical Position in Grid
        let targetRow = logicalRow;
        let targetCol = logicalCol;

        if (!isFront) {
            // Mirror columns for back side
            targetCol = cols - 1 - logicalCol;
        }

        const gridIndex = targetRow * cols + targetCol;

        const cell = document.createElement('div');
        const isBlank = pageNum > inputPages;
        const isOdd = pageNum % 2 === 1;

        cell.className = `cell ${isBlank ? 'blank' : (isOdd ? 'odd' : 'even')}`;

        // Position label (Now Page Number as requested)
        const posLabel = document.createElement('div');
        posLabel.className = 'position';
        posLabel.textContent = isBlank ? '' : `${pageNum}`;
        // FORCE STYLE
        posLabel.style.cssText = "position: absolute; top: 8px; left: 8px; background: white; border: 1px solid black; padding: 0px 2px; z-index: 100; font-weight: bold; color: black; display: block !important; opacity: 1 !important; visibility: visible !important; font-size: 7px !important;";
        cell.appendChild(posLabel);

        // Pair indicator
        const pairLabel = document.createElement('div');
        pairLabel.className = 'pair-indicator';
        // Pair logic: Ceiling(Page/2)
        const pairNum = !isBlank ? Math.ceil(pageNum / 2) : '-';
        pairLabel.textContent = `P${pairNum}`;
        cell.appendChild(pairLabel);

        // Page number
        const pageNumSpan = document.createElement('div');
        pageNumSpan.className = 'page-num';
        pageNumSpan.textContent = isBlank ? '' : pageNum; // Empty string if blank to reduce noise
        cell.appendChild(pageNumSpan);

        // Label
        const labelSpan = document.createElement('div');
        labelSpan.className = 'page-label';
        // Don't show text for blank
        labelSpan.textContent = isBlank ? '' : (isOdd ? 'ODD' : 'EVEN');
        cell.appendChild(labelSpan);

        // Tooltip
        if (!isBlank) {
            const pair = isOdd ? pageNum + 1 : pageNum - 1;
            cell.title = `Page ${pageNum} (Pair: ${pageNum}-${pair})\nStack: ${idx + 1}\nPosition: Row ${targetRow + 1}, Column ${targetCol + 1}`;
        } else {
            cell.title = `Blank padding page\nStack: ${idx + 1}\nPosition: Row ${targetRow + 1}, Column ${targetCol + 1}`;
        }

        cells[gridIndex] = cell;
    });

    cells.forEach(cell => grid.appendChild(cell));
    return grid;
}

function setConfig(pagesPerSheet, _dummyPageCount) {
    document.getElementById('pagesPerSheet').value = pagesPerSheet;
    // We strictly preserve the current input pages (either from upload or manual)
    // document.getElementById('pageInput').value = inputPages; 
    generateImposition();
}

function generateImposition() {
    const pagesPerSheetVal = parseInt(document.getElementById('pagesPerSheet').value);
    const layoutMode = document.getElementById('layoutMode').value;

    // Fix: inputPages was undefined. Read it from the hidden or visible input.
    // Even if hidden, the value is updated by file upload.
    let inputPages = parseInt(document.getElementById('pageInput').value);

    // Update display text
    const displayEl = document.getElementById('pageCountDisplay');
    if (displayEl) {
        if (inputPages > 0) {
            displayEl.textContent = `📄 Detected Pages in PDF: ${inputPages}`;
            displayEl.style.color = '#2563eb'; // Blue
        } else {
            displayEl.textContent = 'Upload a PDF to detect pages';
            displayEl.style.color = '#666';
        }
    }

    if (inputPages < 1 || inputPages > 500) {
        // If 0 (initial state), maybe default to something safely or return?
        // Let's allow 0 but maybe visualization shows empty?
        // Actually, if it's 0 (no file), we can default to 8 for demo purposes if user hasn't uploaded.
        if (inputPages === 0) inputPages = 8;
        else {
            alert('Please enter input pages between 1 and 500');
            return;
        }
    }

    if (pagesPerSheetVal < 1 || pagesPerSheetVal > 128) {
        alert('Please enter pages per sheet between 1 and 128');
        return;
    }

    // User Update: The input IS the pages per side (N-up)
    const pagesPerSide = pagesPerSheetVal;

    // Total pages per PHYSICAL sheet (Front + Back) is pagesPerSide * 2
    const totalCapacityPerSheet = pagesPerSide * 2;

    // SYNC HIDDEN INPUT FOR BACKEND
    const hiddenInput = document.getElementById('hidden_n_up');
    if (hiddenInput) {
        hiddenInput.value = pagesPerSide;
    }

    const layout = calculateGridLayout(pagesPerSide);

    // Use new Logic
    const result = generatePageAssignments(inputPages, totalCapacityPerSheet, pagesPerSide);
    const sheets = result.sheets;
    const totalPages = result.totalPages;
    const paddingPages = totalPages - inputPages;

    // Update stats
    const statsHTML = `
        <div class="stat-box">
            <div class="label">Input Pages</div>
            <div class="value">${inputPages}</div>
        </div>
        <div class="stat-box">
            <div class="label">Total Pages</div>
            <div class="value">${totalPages}</div>
        </div>
        <div class="stat-box">
            <div class="label">Sheets</div>
            <div class="value">${sheets.length}</div>
        </div>
        <div class="stat-box">
            <div class="label">Pairs/Stack</div>
            <div class="value">${result.numSheets}</div>
        </div>
        <div class="stat-box">
            <div class="label">Pages/Side (N-Up)</div>
            <div class="value">${pagesPerSide}</div>
        </div>
        <div class="stat-box">
            <div class="label">Grid Layout</div>
            <div class="value">${layout.cols}×${layout.rows}</div>
        </div>
        <div class="stat-box">
            <div class="label">Layout Mode</div>
            <div class="value" style="font-size: 16px;">${layoutMode === 'compact' ? 'Compact' : 'Print-Safe'}</div>
        </div>
    `;
    document.getElementById('stats').innerHTML = statsHTML;

    // Clear container
    const vizContainer = document.getElementById('visualization');
    vizContainer.innerHTML = '';

    // Show all sheets (removed 3-sheet limit)
    const displaySheets = sheets;

    displaySheets.forEach((sheet, idx) => {
        const sheetDiv = document.createElement('div');
        sheetDiv.className = 'sheet';

        const headerDiv = document.createElement('div');
        headerDiv.className = 'sheet-header';
        headerDiv.innerHTML = `
            <span>📄 Sheet ${idx + 1} of ${sheets.length}</span>
            <span>Pages ${sheet.front[0]}-${sheet.back[pagesPerSide - 1]}</span>
        `;
        sheetDiv.appendChild(headerDiv);

        // Wrapper for side-by-side layout
        const bodyDiv = document.createElement('div');
        bodyDiv.className = 'sheet-body';

        // Front side
        const frontDiv = document.createElement('div');
        frontDiv.className = 'sheet-side';
        const frontLabel = document.createElement('div');
        frontLabel.className = 'side-label';
        frontLabel.innerHTML = `
            <span>🔽 Front Side</span>
            <span class="badge">Odd Pages</span>
        `;
        frontDiv.appendChild(frontLabel);
        frontDiv.appendChild(createGrid(sheet.front, inputPages, true, layout.cols, layout.rows, pagesPerSide));
        bodyDiv.appendChild(frontDiv);

        // Back side
        const backDiv = document.createElement('div');
        backDiv.className = 'sheet-side';
        const backLabel = document.createElement('div');
        backLabel.className = 'side-label';
        backLabel.innerHTML = `
            <span>🔼 Back Side (Mirrored)</span>
            <span class="badge">Even Pages</span>
        `;
        backDiv.appendChild(backLabel);
        backDiv.appendChild(createGrid(sheet.back, inputPages, false, layout.cols, layout.rows, pagesPerSide));
        bodyDiv.appendChild(backDiv);

        sheetDiv.appendChild(bodyDiv);
        vizContainer.appendChild(sheetDiv);
    });

    // No limit message needed
}

// Initial generation
document.addEventListener('DOMContentLoaded', () => {
    // Generate initial with 0 or placeholder? Let's say 8 pages default for demo
    // But user wants accurate visualization. 
    // We'll leave the default 7 (or 0) in the hidden input but maybe show a message "Upload PDF to visualize"
    document.getElementById('pageInput').value = 8;
    generateImposition();

    // Auto-update on ANY change to inputs
    const inputs = ['pagesPerSheet', 'layoutMode'];
    inputs.forEach(id => {
        const elem = document.getElementById(id);
        if (elem) {
            elem.addEventListener('input', () => generateImposition());
            elem.addEventListener('change', () => generateImposition());
        }
    });

    // File Upload Handler
    const fileInput = document.getElementById('pdf_file');

    if (fileInput) {
        // Standard Change Event
        fileInput.addEventListener('change', function (e) {
            if (this.files && this.files[0]) {
                handleFiles(this.files[0]);
            }
        });

        async function handleFiles(file) {
            // No drop zone to update anymore

            const formData = new FormData();
            formData.append('pdf_file', file);

            // Show loading state?
            document.querySelector('.visualization').innerHTML = '<div style="text-align:center; padding:40px;">Analyzing PDF structure...</div>';

            try {
                const response = await fetch('/count-pages', {
                    method: 'POST',
                    body: formData
                });

                if (response.ok) {
                    const data = await response.json();
                    if (data.pages) {
                        // Update input pages
                        document.getElementById('pageInput').value = data.pages;
                        // Regenerate visualization
                        generateImposition();
                    }
                } else {
                    console.error("Failed to count pages");
                    // Fallback or error
                    document.querySelector('.visualization').innerHTML = '<div style="text-align:center; padding:40px; color:red;">Could not analyze PDF. Please check file.</div>';
                }
            } catch (err) {
                console.error("Error uploading file for count:", err);
            }
        }
    }

    // FORM SUBMISSION HANDLER
    const form = document.getElementById('uploadForm');
    if (form) {
        form.addEventListener('submit', function (e) {
            const fileInput = document.getElementById('pdf_file');
            if (!fileInput.files || fileInput.files.length === 0) {
                e.preventDefault();
                alert("⚠️ Please select a PDF file first!");
                return;
            }

            // Show loading state on button
            const btn = document.querySelector('.download-btn');
            const originalText = btn.textContent;
            btn.textContent = "⏳ Processing...";
            btn.style.opacity = "0.7";
            btn.style.pointerEvents = "none"; // Prevent double click

            // Re-enable after short delay in case download starts or fails silently (since it's a form post)
            // Ideally we'd use fetch/blob for download to know exactly when it finishes, 
            // but for a simple form post, a timeout reset is a common graceful fallback.
            setTimeout(() => {
                btn.textContent = originalText;
                btn.style.opacity = "1";
                btn.style.pointerEvents = "auto";
            }, 3000);
        });
    }
});
