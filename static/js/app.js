/**
 * Bilingual Exam PDF Splitter & 2-Up Stitcher
 * 100% Client-Side Web Application (GitHub Pages Compatible)
 * Powered by pdf.js (rendering & line detection) and pdf-lib (in-browser stitching)
 */

// Configure PDF.js worker
if (window.pdfjsLib) {
    pdfjsLib.GlobalWorkerOptions.workerSrc = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
}

document.addEventListener("DOMContentLoaded", () => {
    // --- Application State ---
    const state = {
        files: [],               // [{ id, name, sizeKb, arrayBuffer, pdfDoc, totalPages, dividerData: {} }]
        activeFileId: null,
        currentPageIdx: 0,
        totalPages: 0,
        currentDividerPct: 50.0,
        currentOffsetPt: 0.0,
        totalSheetsSaved: 0,
        results: [],
        theme: localStorage.getItem("app_theme") || "dark"
    };

    // --- DOM Elements ---
    const dropzone = document.getElementById("dropzone");
    const fileInput = document.getElementById("fileInput");
    const browseBtn = document.getElementById("browseBtn");
    const queueCard = document.getElementById("queueCard");
    const queueCount = document.getElementById("queueCount");
    const fileQueueList = document.getElementById("fileQueueList");
    const clearQueueBtn = document.getElementById("clearQueueBtn");

    const offsetSlider = document.getElementById("offsetSlider");
    const offsetValueDisplay = document.getElementById("offsetValueDisplay");
    const sideSelect = document.getElementById("sideSelect");
    const skipCoverCheckbox = document.getElementById("skipCoverCheckbox");
    const customSkipInput = document.getElementById("customSkipInput");
    const drawLineCheckbox = document.getElementById("drawLineCheckbox");
    const processBtn = document.getElementById("processBtn");

    const previewStage = document.getElementById("previewStage");
    const previewPlaceholder = document.getElementById("previewPlaceholder");
    const previewViewport = document.getElementById("previewViewport");
    const previewCanvas = document.getElementById("previewCanvas");
    const dividerOverlayLine = document.getElementById("dividerOverlayLine");
    const previewPageIndicator = document.getElementById("previewPageIndicator");
    const prevPageBtn = document.getElementById("prevPageBtn");
    const nextPageBtn = document.getElementById("nextPageBtn");
    const previewPageInput = document.getElementById("previewPageInput");
    const previewFooter = document.getElementById("previewFooter");
    const previewStats = document.getElementById("previewStats");

    const progressCard = document.getElementById("progressCard");
    const progressBarFill = document.getElementById("progressBarFill");
    const progressStatusText = document.getElementById("progressStatusText");

    const resultsCard = document.getElementById("resultsCard");
    const resultsList = document.getElementById("resultsList");
    const batchZipBtn = document.getElementById("batchZipBtn");

    const pdfViewerContainer = document.getElementById("pdfViewerContainer");
    const viewerTitle = document.getElementById("viewerTitle");
    const pdfViewerFrame = document.getElementById("pdfViewerFrame");
    const closeViewerBtn = document.getElementById("closeViewerBtn");

    const historyCount = document.getElementById("historyCount");
    const historyList = document.getElementById("historyList");
    const totalSavedText = document.getElementById("totalSavedText");
    const themeToggleBtn = document.getElementById("themeToggleBtn");
    const themeIcon = document.getElementById("themeIcon");

    // --- Theme Control ---
    function applyTheme(theme) {
        state.theme = theme;
        document.body.className = theme === "light" ? "theme-light" : "theme-dark";
        themeIcon.textContent = theme === "light" ? "🌙" : "☀️";
        localStorage.setItem("app_theme", theme);
    }
    applyTheme(state.theme);

    themeToggleBtn.addEventListener("click", () => {
        applyTheme(state.theme === "dark" ? "light" : "dark");
    });

    // --- Drag and Drop ---
    browseBtn.addEventListener("click", () => fileInput.click());
    dropzone.addEventListener("click", (e) => {
        if (e.target !== browseBtn) fileInput.click();
    });

    ["dragenter", "dragover"].forEach(evtName => {
        dropzone.addEventListener(evtName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.add("dragover");
        });
    });

    ["dragleave", "drop"].forEach(evtName => {
        dropzone.addEventListener(evtName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.remove("dragover");
        });
    });

    dropzone.addEventListener("drop", (e) => {
        const files = e.dataTransfer.files;
        if (files && files.length > 0) handleFiles(files);
    });

    fileInput.addEventListener("change", (e) => {
        if (e.target.files && e.target.files.length > 0) handleFiles(e.target.files);
    });

    // --- Client-Side File Handler ---
    async function handleFiles(fileList) {
        for (let i = 0; i < fileList.length; i++) {
            const file = fileList[i];
            if (!file.name.toLowerCase().endsWith(".pdf")) continue;

            try {
                const arrayBuffer = await file.arrayBuffer();
                // Load with pdfjs
                const loadingTask = pdfjsLib.getDocument({ data: arrayBuffer });
                const pdfDoc = await loadingTask.promise;

                const fileObj = {
                    id: Math.random().toString(36).substring(2, 10),
                    name: file.name,
                    sizeKb: Math.round(file.size / 1024),
                    arrayBuffer: arrayBuffer,
                    pdfDoc: pdfDoc,
                    totalPages: pdfDoc.numPages,
                    dividerCache: {}
                };

                state.files.push(fileObj);

                if (!state.activeFileId) {
                    state.activeFileId = fileObj.id;
                    state.currentPageIdx = 0;
                }
            } catch (err) {
                console.error("Failed to load PDF:", err);
                alert(`Could not load ${file.name}: ` + err.message);
            }
        }

        renderQueue();
        loadPreview();
        updateControlsState();
        fileInput.value = "";
    }

    function renderQueue() {
        if (state.files.length === 0) {
            queueCard.style.display = "none";
            return;
        }

        queueCard.style.display = "flex";
        queueCount.textContent = state.files.length;
        fileQueueList.innerHTML = "";

        state.files.forEach(f => {
            const item = document.createElement("div");
            item.className = `queue-item ${f.id === state.activeFileId ? "active" : ""}`;
            item.innerHTML = `
                <div class="queue-item-info">
                    <span class="queue-item-name" title="${f.name}">${f.name}</span>
                    <span class="queue-item-meta">${f.totalPages} pages • ${f.sizeKb} KB</span>
                </div>
                <button type="button" class="btn btn-xs btn-outline text-danger" data-id="${f.id}">✕</button>
            `;

            item.addEventListener("click", (e) => {
                if (e.target.tagName === "BUTTON") {
                    e.stopPropagation();
                    removeFile(f.id);
                } else {
                    state.activeFileId = f.id;
                    state.currentPageIdx = 0;
                    renderQueue();
                    loadPreview();
                }
            });

            fileQueueList.appendChild(item);
        });
    }

    function removeFile(fileId) {
        state.files = state.files.filter(f => f.id !== fileId);
        if (state.activeFileId === fileId) {
            state.activeFileId = state.files.length > 0 ? state.files[0].id : null;
            state.currentPageIdx = 0;
        }
        renderQueue();
        loadPreview();
        updateControlsState();
    }

    clearQueueBtn.addEventListener("click", () => {
        state.files = [];
        state.activeFileId = null;
        state.currentPageIdx = 0;
        renderQueue();
        loadPreview();
        updateControlsState();
    });

    function updateControlsState() {
        const hasFiles = state.files.length > 0;
        processBtn.disabled = !hasFiles;
        prevPageBtn.disabled = !hasFiles;
        nextPageBtn.disabled = !hasFiles;
        previewPageInput.disabled = !hasFiles;
    }

    // --- 10-Slice Physical Divider Line Detection on Canvas ---
    function detectDividerLineOnCanvas(canvas) {
        const ctx = canvas.getContext("2d");
        const w = canvas.width;
        const h = canvas.height;

        const contentTop = Math.floor(h * 0.08);
        const contentBottom = Math.floor(h * 0.92);
        const contentHeight = contentBottom - contentTop;

        const minX = Math.floor(w * 0.44);
        const maxX = Math.floor(w * 0.56);

        const nSlices = 10;
        const sliceH = Math.floor(contentHeight / nSlices);
        const slicePeaks = [];

        const imgData = ctx.getImageData(0, 0, w, h).data;

        for (let s = 0; s < nSlices; s++) {
            const sliceYStart = contentTop + s * sliceH;
            const sliceYEnd = sliceYStart + sliceH;
            const span = maxX - minX;
            const darkProfile = new Float32Array(span);

            for (let x = minX; x < maxX; x++) {
                let darkCount = 0;
                for (let y = sliceYStart; y < sliceYEnd; y++) {
                    const idx = (y * w + x) * 4;
                    const brightness = 0.299 * imgData[idx] + 0.587 * imgData[idx + 1] + 0.114 * imgData[idx + 2];
                    if (brightness < 130) darkCount++;
                }
                darkProfile[x - minX] = darkCount / sliceH;
            }

            // 3-point smoothing
            let bestIdx = 0;
            let bestVal = 0;
            for (let i = 1; i < span - 1; i++) {
                const smooth = 0.25 * darkProfile[i - 1] + 0.5 * darkProfile[i] + 0.25 * darkProfile[i + 1];
                if (smooth > bestVal) {
                    bestVal = smooth;
                    bestIdx = i;
                }
            }

            if (bestVal > 0.12) {
                slicePeaks.push(minX + bestIdx);
            }
        }

        if (slicePeaks.length >= 3) {
            slicePeaks.sort((a, b) => a - b);
            return slicePeaks[Math.floor(slicePeaks.length / 2)];
        }
        return Math.floor(w / 2);
    }

    // --- Page Preview Rendering ---
    async function loadPreview() {
        if (!state.activeFileId) {
            previewPlaceholder.style.display = "flex";
            previewViewport.style.display = "none";
            previewFooter.style.display = "none";
            previewPageIndicator.textContent = "No PDF selected";
            previewPageInput.value = 1;
            return;
        }

        const activeFile = state.files.find(f => f.id === state.activeFileId);
        if (!activeFile) return;

        state.totalPages = activeFile.totalPages;
        previewPageIndicator.textContent = `${activeFile.name}`;
        previewPageInput.value = state.currentPageIdx + 1;
        previewPageInput.max = state.totalPages;

        try {
            const page = await activeFile.pdfDoc.getPage(state.currentPageIdx + 1);
            const viewport = page.getViewport({ scale: 1.2 });

            previewCanvas.width = viewport.width;
            previewCanvas.height = viewport.height;

            const ctx = previewCanvas.getContext("2d");
            await page.render({ canvasContext: ctx, viewport: viewport }).promise;

            // Detect divider line on the rendered canvas
            const linePixelX = detectDividerLineOnCanvas(previewCanvas);
            const ptScale = page.view[2] / viewport.width;
            const dividerPt = linePixelX * ptScale;
            const dividerPct = (linePixelX / viewport.width) * 100.0;

            state.currentDividerPct = dividerPct;

            previewPlaceholder.style.display = "none";
            previewViewport.style.display = "inline-block";
            previewFooter.style.display = "flex";

            updateDividerOverlay();
            previewStats.textContent = `Page ${state.currentPageIdx + 1}/${state.totalPages} • Divider: ${dividerPt.toFixed(1)} pt (${dividerPct.toFixed(1)}%)`;

        } catch (err) {
            console.error("Preview load error:", err);
        }
    }

    function updateDividerOverlay() {
        const offsetPct = (state.currentOffsetPt / 595.0) * 100.0;
        const totalPct = Math.max(10, Math.min(90, state.currentDividerPct + offsetPct));
        dividerOverlayLine.style.left = `${totalPct}%`;
    }

    // --- Offset Slider ---
    offsetSlider.addEventListener("input", (e) => {
        const val = parseFloat(e.target.value);
        state.currentOffsetPt = val;
        offsetValueDisplay.textContent = `${val > 0 ? "+" : ""}${val} pt`;
        updateDividerOverlay();
    });

    // --- Page Navigation ---
    prevPageBtn.addEventListener("click", () => {
        if (state.currentPageIdx > 0) {
            state.currentPageIdx--;
            loadPreview();
        }
    });

    nextPageBtn.addEventListener("click", () => {
        if (state.currentPageIdx < state.totalPages - 1) {
            state.currentPageIdx++;
            loadPreview();
        }
    });

    previewPageInput.addEventListener("change", (e) => {
        let val = parseInt(e.target.value) - 1;
        if (isNaN(val) || val < 0) val = 0;
        if (val >= state.totalPages) val = state.totalPages - 1;
        state.currentPageIdx = val;
        loadPreview();
    });

    // --- 100% Client-Side In-Browser Stitching Engine (pdf-lib) ---
    processBtn.addEventListener("click", async () => {
        if (state.files.length === 0) return;

        const layoutMode = document.querySelector('input[name="layoutMode"]:checked').value;
        const merge2up = (layoutMode === "2up");
        const side = sideSelect.value; // left, right, both
        const drawLine = drawLineCheckbox.checked;

        const skipSet = new Set();
        if (skipCoverCheckbox.checked) skipSet.add(0);
        const customSkip = customSkipInput.value.trim();
        if (customSkip) {
            customSkip.split(",").forEach(p => {
                const num = parseInt(p.trim());
                if (!isNaN(num)) skipSet.add(num);
            });
        }

        progressCard.style.display = "flex";
        progressBarFill.style.width = "5%";
        progressStatusText.textContent = `Starting client-side in-browser stitching...`;
        processBtn.disabled = true;

        const results = [];
        let totalFiles = state.files.length;

        try {
            for (let fIdx = 0; fIdx < totalFiles; fIdx++) {
                const f = state.files[fIdx];
                const sidesToRun = (side === "both") ? ["left", "right"] : [side];

                for (const s of sidesToRun) {
                    const result = await processSinglePdfClientSide(
                        f, s, merge2up, skipSet, state.currentOffsetPt, drawLine,
                        (step, total) => {
                            const pct = Math.round(((fIdx + (step / total)) / totalFiles) * 100);
                            progressBarFill.style.width = `${pct}%`;
                            progressStatusText.textContent = `Processing ${f.name} (${step}/${total})...`;
                        }
                    );
                    results.push(result);
                }
            }

            progressBarFill.style.width = "100%";
            setTimeout(() => {
                progressCard.style.display = "none";
                processBtn.disabled = false;
                renderResults(results);
            }, 300);

        } catch (err) {
            console.error("Client-side process error:", err);
            alert("Processing error: " + err.message);
            progressCard.style.display = "none";
            processBtn.disabled = false;
        }
    });

    async function processSinglePdfClientSide(fileObj, side, merge2up, skipSet, offsetPt, drawLine, progressCb) {
        const { PDFDocument, rgb } = PDFLib;
        const srcDoc = await PDFDocument.load(fileObj.arrayBuffer);
        const outDoc = await PDFDocument.create();

        const srcPages = srcDoc.getPages();
        const validIndices = [];
        for (let i = 0; i < srcPages.length; i++) {
            if (!skipSet.has(i)) validIndices.push(i);
        }

        const totalValid = validIndices.length;

        // Hidden canvas for divider line detection on each page
        const offscreenCanvas = document.createElement("canvas");

        if (merge2up) {
            const pairCount = Math.ceil(totalValid / 2);
            for (let pairIdx = 0; pairIdx < pairCount; pairIdx++) {
                const idx1 = validIndices[pairIdx * 2];
                const idx2 = (pairIdx * 2 + 1 < totalValid) ? validIndices[pairIdx * 2 + 1] : null;

                const p1 = srcPages[idx1];
                const { width: targetW, height: targetH } = p1.getSize();
                const midX = targetW / 2;

                const newPage = outDoc.addPage([targetW, targetH]);

                // Detect divider line for p1
                const divider1 = await detectDividerForPage(fileObj.pdfDoc, idx1, offscreenCanvas) + offsetPt;

                const clip1Box = (side === "left")
                    ? { left: 0, bottom: 0, right: Math.min(targetW, divider1 + 1.0), top: targetH }
                    : { left: Math.max(0, divider1 - 1.0), bottom: 0, right: targetW, top: targetH };

                const [clip1] = await outDoc.embedPages([p1], [clip1Box]);
                newPage.drawPage(clip1, { x: 0, y: 0, width: midX, height: targetH });

                // Page 2 in pair
                if (idx2 !== null) {
                    const p2 = srcPages[idx2];
                    const divider2 = await detectDividerForPage(fileObj.pdfDoc, idx2, offscreenCanvas) + offsetPt;

                    const clip2Box = (side === "left")
                        ? { left: 0, bottom: 0, right: Math.min(targetW, divider2 + 1.0), top: targetH }
                        : { left: Math.max(0, divider2 - 1.0), bottom: 0, right: targetW, top: targetH };

                    const [clip2] = await outDoc.embedPages([p2], [clip2Box]);
                    newPage.drawPage(clip2, { x: midX, y: 0, width: midX, height: targetH });
                }

                if (drawLine) {
                    newPage.drawLine({
                        start: { x: midX, y: 35 },
                        end: { x: midX, y: targetH - 35 },
                        thickness: 0.7,
                        color: rgb(0.25, 0.25, 0.25)
                    });
                }

                if (progressCb) progressCb(pairIdx + 1, pairCount);
            }
        } else {
            // Single-column mode
            for (let step = 0; step < totalValid; step++) {
                const pageIdx = validIndices[step];
                const page = srcPages[pageIdx];
                const { width: origW, height: origH } = page.getSize();

                const divider = await detectDividerForPage(fileObj.pdfDoc, pageIdx, offscreenCanvas) + offsetPt;

                const clipBox = (side === "left")
                    ? { left: 0, bottom: 0, right: Math.min(origW, divider + 1.0), top: origH }
                    : { left: Math.max(0, divider - 1.0), bottom: 0, right: origW, top: origH };

                const cropW = (side === "left") ? clipBox.right : (origW - clipBox.left);
                const [clip] = await outDoc.embedPages([page], [clipBox]);

                const newPage = outDoc.addPage([cropW, origH]);
                newPage.drawPage(clip, { x: 0, y: 0, width: cropW, height: origH });

                if (progressCb) progressCb(step + 1, totalValid);
            }
        }

        const outBytes = await outDoc.save();
        const baseName = fileObj.name.replace(/\.[^/.]+$/, "");
        const suffix = (side === "left") ? "_hindi" : "_english";
        const modeTag = merge2up ? "_2up" : "_single";
        const outFileName = `${baseName}${suffix}${modeTag}.pdf`;

        const blob = new Blob([outBytes], { type: "application/pdf" });
        const blobUrl = URL.createObjectURL(blob);

        const outPages = outDoc.getPageCount();
        const origPages = fileObj.totalPages - skipSet.size;
        const savedSheets = merge2up ? Math.max(0, origPages - outPages) : 0;
        const savingsPct = (merge2up && origPages > 0) ? Math.round((savedSheets / origPages) * 100) : 0;

        return {
            id: Math.random().toString(36).substring(2, 10),
            name: outFileName,
            blobUrl: blobUrl,
            blob: blob,
            outPages: outPages,
            origPages: origPages,
            savedSheets: savedSheets,
            savingsPct: savingsPct,
            mode: merge2up ? "2-Up Booklet" : "Single-Column",
            sizeKb: Math.round(outBytes.length / 1024),
            time: new Date().toLocaleTimeString()
        };
    }

    async function detectDividerForPage(pdfDoc, pageIdx, offscreenCanvas) {
        const page = await pdfDoc.getPage(pageIdx + 1);
        const viewport = page.getViewport({ scale: 1.0 });

        offscreenCanvas.width = viewport.width;
        offscreenCanvas.height = viewport.height;
        const ctx = offscreenCanvas.getContext("2d");

        await page.render({ canvasContext: ctx, viewport: viewport }).promise;
        const px = detectDividerLineOnCanvas(offscreenCanvas);
        const scale = page.view[2] / viewport.width;
        return px * scale;
    }

    // --- Render Results & PDF Viewer ---
    function renderResults(results) {
        state.results = results;
        resultsCard.style.display = "flex";
        resultsList.innerHTML = "";

        let newSheetsSaved = 0;

        results.forEach(res => {
            newSheetsSaved += res.savedSheets;

            const item = document.createElement("div");
            item.className = "result-item";
            item.innerHTML = `
                <div class="result-meta">
                    <h5>${res.name}</h5>
                    <div class="result-stats">
                        <span class="badge badge-accent">${res.mode}</span>
                        <span>📄 ${res.origPages} pages ➔ <strong>${res.outPages} pages</strong></span>
                        ${res.savedSheets > 0 ? `<span class="badge badge-success">Saved ${res.savedSheets} sheets (${res.savingsPct}%)</span>` : ""}
                    </div>
                </div>
                <div class="result-actions">
                    <button type="button" class="btn btn-sm btn-outline preview-pdf-btn" data-url="${res.blobUrl}" data-name="${res.name}">👁️ View</button>
                    <a href="${res.blobUrl}" download="${res.name}" class="btn btn-sm btn-primary">⬇️ Download</a>
                </div>
            `;
            resultsList.appendChild(item);
        });

        state.totalSheetsSaved += newSheetsSaved;
        totalSavedText.textContent = `${state.totalSheetsSaved} Sheets Saved`;

        document.querySelectorAll(".preview-pdf-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                const url = btn.getAttribute("data-url");
                const name = btn.getAttribute("data-name");
                viewerTitle.textContent = `Viewing: ${name}`;
                pdfViewerFrame.src = url;
                pdfViewerContainer.style.display = "flex";
                pdfViewerContainer.scrollIntoView({ behavior: "smooth" });
            });
        });

        updateHistoryList(results);
    }

    closeViewerBtn.addEventListener("click", () => {
        pdfViewerContainer.style.display = "none";
        pdfViewerFrame.src = "";
    });

    // --- Batch Download ---
    batchZipBtn.addEventListener("click", () => {
        if (!state.results || state.results.length === 0) return;
        state.results.forEach((res, i) => {
            setTimeout(() => {
                const a = document.createElement("a");
                a.href = res.blobUrl;
                a.download = res.name;
                document.body.appendChild(a);
                a.click();
                a.remove();
            }, i * 300);
        });
    });

    function updateHistoryList(newResults) {
        if (!newResults || newResults.length === 0) return;
        historyCount.textContent = `${newResults.length} Completed`;
        historyList.innerHTML = "";
        newResults.forEach(item => {
            const row = document.createElement("div");
            row.className = "queue-item";
            row.innerHTML = `
                <div class="queue-item-info">
                    <span class="queue-item-name">${item.name}</span>
                    <span class="queue-item-meta">${item.time} • ${item.outPages} pages • ${item.sizeKb} KB</span>
                </div>
                <a href="${item.blobUrl}" download="${item.name}" class="btn btn-xs btn-outline">⬇️</a>
            `;
            historyList.appendChild(row);
        });
    }
});
