/* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
   ResumeAI â€” Frontend Application Logic
   â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */

(function () {
    "use strict";

    // â”€â”€ DOM Elements â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    const uploadZone = document.getElementById("upload-zone");
    const fileInput = document.getElementById("file-input");
    const uploadBrowse = document.getElementById("upload-browse");
    const filePreview = document.getElementById("file-preview");
    const fileName = document.getElementById("file-name");
    const fileSize = document.getElementById("file-size");
    const fileRemove = document.getElementById("file-remove");
    const analyzeBtn = document.getElementById("analyze-btn");
    const uploadSection = document.getElementById("view-landing");
    const loadingSection = document.getElementById("loading-section");
    const loadingText = document.getElementById("loading-text");
    const resultsSection = document.getElementById("app-shell");
    const errorToast = document.getElementById("error-toast");
    const errorMessage = document.getElementById("error-message");
    const errorClose = document.getElementById("error-close");
    const tryAgainBtn = document.getElementById("try-again-btn");
    const musicToggle = document.getElementById("music-toggle");
    const ambientMusic = document.getElementById("ambient-music");

    // â”€â”€ Auth DOM Elements â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    const navLoginBtn = document.getElementById("nav-login-btn");
    const userMenu = document.getElementById("user-menu");
    const navMyAppsBtn = document.getElementById("nav-my-apps");
    const userAvatar = document.getElementById("user-avatar");
    const userNameNav = document.getElementById("user-name-nav");
    const userAvatarBtn = document.getElementById("user-avatar-btn");
    const userDropdown = document.getElementById("user-dropdown");
    const userDropdownName = document.getElementById("user-dropdown-name");
    const userDropdownEmail = document.getElementById("user-dropdown-email");
    const logoutBtn = document.getElementById("logout-btn");
    
    const authOverlay = document.getElementById("auth-overlay");
    const authClose = document.getElementById("auth-close");
    const authTabs = document.querySelectorAll(".auth-tab");
    const loginForm = document.getElementById("login-form");
    const signupForm = document.getElementById("signup-form");
    const loginError = document.getElementById("login-error");
    const signupError = document.getElementById("signup-error");

    const successToast = document.getElementById("success-toast");
    const successMessage = document.getElementById("success-message");

    const appsModal = document.getElementById("apps-modal");
    const appsClose = document.getElementById("apps-close");
    const appsListContainer = document.getElementById("apps-list-container");
    const navAppsBtn = document.getElementById("nav-apps-btn");
    const categoryStatusBanner = document.getElementById("category-state-banner");
    const categoryStatusText = document.getElementById("category-state-text");
    const categoryConfirmPanel = document.getElementById("category-confirm-panel");
    const categoryConfirmOptions = document.getElementById("category-confirm-options");
    const categoryRememberCheckbox = document.getElementById("remember-category");
    const rankingMeta = document.getElementById("ranking-meta");
    const sidebarLinks = document.querySelectorAll(".sidebar-link");
    const dashboardViews = document.querySelectorAll(".dashboard-view");
    const dashboardContent = document.querySelector(".dashboard-content");

    let currentUser = null;
    let currentQualityReport = null;

    let selectedFile = null;
    let analysisInFlight = false;
    const MAX_UPLOAD_BYTES = 8 * 1024 * 1024;
    const MAX_UPLOAD_LABEL = "8 MB";

    function sleep(ms) {
        return new Promise((resolve) => setTimeout(resolve, ms));
    }

    function parseJsonSafe(text) {
        if (!text) return {};
        try {
            return JSON.parse(text);
        } catch {
            return {};
        }
    }

    async function postAnalyzeWithRetry(formData, retries = 1) {
        let lastError = null;
        for (let attempt = 0; attempt <= retries; attempt++) {
            try {
                return await fetch("/api/analyze", {
                    method: "POST",
                    body: formData,
                    credentials: "same-origin",
                    cache: "no-store",
                });
            } catch (err) {
                lastError = err;
                if (attempt === retries) break;
                await sleep(1200);
            }
        }
        throw lastError || new Error("Analysis request failed.");
    }

    // â”€â”€ Theme Toggle â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    const themeToggle = document.getElementById("theme-toggle");

    function getStoredTheme() {
        return localStorage.getItem("theme") || "dark";
    }

    function applyTheme(theme) {
        if (theme === "light") {
            document.documentElement.setAttribute("data-theme", "light");
        } else {
            document.documentElement.removeAttribute("data-theme");
        }
        localStorage.setItem("theme", theme);
    }

    // Apply saved theme on load
    applyTheme(getStoredTheme());

    themeToggle.addEventListener("click", () => {
        const current = getStoredTheme();
        const next = current === "dark" ? "light" : "dark";
        applyTheme(next);
    });

    // ── Ambient Music Toggle ──────────────────────────────────────────
    if (musicToggle && ambientMusic) {
        const musicIconOff = musicToggle.querySelector(".music-icon-off");
        const musicIconOn = musicToggle.querySelector(".music-icon-on");

        // Pleasant low background volume
        ambientMusic.volume = 0.25;

        // Load stored music state
        const storedMusicState = localStorage.getItem("ambientMusic") === "playing";

        function setMusicState(isPlaying) {
            if (isPlaying) {
                ambientMusic.play().then(() => {
                    if (musicIconOff) musicIconOff.style.display = "none";
                    if (musicIconOn) musicIconOn.style.display = "block";
                    localStorage.setItem("ambientMusic", "playing");
                }).catch(err => {
                    console.log("Autoplay or audio play blocked: ", err);
                    // Reset to paused if play fails
                    if (musicIconOff) musicIconOff.style.display = "block";
                    if (musicIconOn) musicIconOn.style.display = "none";
                    localStorage.setItem("ambientMusic", "paused");
                });
            } else {
                ambientMusic.pause();
                if (musicIconOff) musicIconOff.style.display = "block";
                if (musicIconOn) musicIconOn.style.display = "none";
                localStorage.setItem("ambientMusic", "paused");
            }
        }

        // Apply saved state or default to paused
        if (storedMusicState) {
            // Note: browser might block autoplay on initial load, but this is handled gracefully by play().catch()
            setMusicState(true);
        }

        musicToggle.addEventListener("click", () => {
            const isPaused = ambientMusic.paused;
            setMusicState(isPaused);
        });
    }


    // Hero stats (live, not dummy)
    loadHeroStats();

    async function loadHeroStats() {
        const jobsEl = document.getElementById("stat-jobs");
        const catEl = document.getElementById("stat-categories");
        const skillsEl = document.getElementById("stat-skills");

        // Skill extraction is always on, keep it simple/credible
        if (skillsEl) skillsEl.textContent = "Ready";

        // Categories from backend
        try {
            const res = await fetch("/api/categories");
            const data = await res.json();
            const count = Array.isArray(data.categories) ? data.categories.length : 0;
            if (catEl) catEl.textContent = count ? `${count}` : "\u2014";
        } catch {
            if (catEl) catEl.textContent = "\u2014";
        }

        // Live jobs sample
        try {
            const res = await fetch("/api/jobs/live?q=software%20developer");
            const data = await res.json();
            const count = typeof data.count === "number" ? data.count : (data.jobs || []).length;
            if (jobsEl) jobsEl.textContent = count ? `${count} now` : "Live";
        } catch {
            if (jobsEl) jobsEl.textContent = "Live";
        }
    }

    // â”€â”€ File Upload â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    // Drag & drop
    uploadZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        uploadZone.classList.add("drag-over");
    });

    uploadZone.addEventListener("dragleave", () => {
        uploadZone.classList.remove("drag-over");
    });

    uploadZone.addEventListener("drop", (e) => {
        e.preventDefault();
        uploadZone.classList.remove("drag-over");
        const files = e.dataTransfer.files;
        if (files.length > 0) handleFileSelect(files[0]);
    });

    // Click to upload (handled natively by the transparent absolute overlay of fileInput)

    fileInput.addEventListener("change", () => {
        if (fileInput.files.length > 0) handleFileSelect(fileInput.files[0]);
    });

    function handleFileSelect(file) {
        const ext = file.name.split(".").pop().toLowerCase();
        const allowed = ["pdf", "docx", "doc", "txt"];
        if (!allowed.includes(ext)) {
            showError("Unsupported file type. Please upload a PDF, DOCX, or TXT file.");
            return;
        }
        if (file.size > MAX_UPLOAD_BYTES) {
            showError(`File is too large. Maximum size is ${MAX_UPLOAD_LABEL}.`);
            return;
        }

        selectedFile = file;
        fileName.textContent = file.name;
        fileSize.textContent = formatFileSize(file.size);
        uploadZone.style.display = "none";
        filePreview.style.display = "block";
    }

    fileRemove.addEventListener("click", resetUpload);

    function resetUpload() {
        selectedFile = null;
        fileInput.value = "";
        uploadZone.style.display = "block";
        filePreview.style.display = "none";
    }

    function formatFileSize(bytes) {
        if (bytes < 1024) return bytes + " B";
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
        return (bytes / (1024 * 1024)).toFixed(1) + " MB";
    }

    // â”€â”€ Analyze â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    analyzeBtn.addEventListener("click", async () => {
        await runAnalysis();
    });

    async function runAnalysis(options = {}) {
        if (analysisInFlight) return;

        if (!selectedFile) {
            showError("Please select a resume file first.");
            return;
        }

        const confirmedCategory = options.confirmedCategory || "";
        const rememberCategory = Boolean(options.rememberCategory);
        analysisInFlight = true;

        uploadSection.style.display = "none";
        resultsSection.style.display = "none";
        loadingSection.style.display = "";
        document.body.classList.remove("results-mode");
        loadingSection.scrollIntoView({ behavior: "smooth", block: "center" });

        const loadingMessages = [
            "Extracting text from your resume...",
            "Running NLP pipeline...",
            "Detecting skills and competencies...",
            "Predicting career category...",
            "Matching with job database...",
            "Generating recommendations...",
        ];
        let msgIndex = 0;
        const msgInterval = setInterval(() => {
            msgIndex = (msgIndex + 1) % loadingMessages.length;
            loadingText.textContent = loadingMessages[msgIndex];
        }, 2000);

        try {
            try {
                await fetch("/api/health", { cache: "no-store" });
            } catch (_) {
                // Best effort warm-up ping for free-tier cold starts.
            }

            const formData = new FormData();
            formData.append("resume", selectedFile);
            if (confirmedCategory) {
                formData.append("confirmed_category", confirmedCategory);
                formData.append("remember_category", String(rememberCategory));
            }

            const response = await postAnalyzeWithRetry(formData, 1);

            clearInterval(msgInterval);
            const rawResponse = await response.text();
            const data = parseJsonSafe(rawResponse);

            if (!response.ok) {
                if (response.status === 401 || data.auth_required) {
                    window.location.href = "/login";
                    return;
                }
                if (response.status === 413) {
                    throw new Error(`File is too large. Please upload a resume under ${MAX_UPLOAD_LABEL}.`);
                }
                throw new Error(
                    data.error || `Analysis failed (HTTP ${response.status}). Please try again.`
                );
            }

            if (!data || !data.success) {
                throw new Error(data.error || "Unknown error occurred.");
            }

            loadingSection.style.display = "none";
            renderResults(data);
            resultsSection.style.display = "";
            if (dashboardContent) {
                dashboardContent.scrollTop = 0;
            }
            document.body.classList.add("results-mode");
            resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
        } catch (err) {
            clearInterval(msgInterval);
            loadingSection.style.display = "none";
            uploadSection.style.display = "";
            document.body.classList.remove("results-mode");
            const msg = (err && err.message) ? err.message : "Analysis failed. Please try again.";
            if (msg === "Failed to fetch" || msg === "Load failed") {
                showError(
                    `Network issue while uploading. On mobile, open in Chrome/Safari (not in-app browser), use stable internet, and keep file under ${MAX_UPLOAD_LABEL}.`
                );
            } else {
                showError(msg);
            }
        } finally {
            analysisInFlight = false;
        }
    }

    // â”€â”€ Render Results â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    function renderResults(data) {
        const stats = data.resume_stats;
        const skills = data.skills;
        const categories = data.predicted_categories;
        const jobs = data.job_recommendations;

        // Overview cards
        currentQualityReport = stats.quality_report;
        animateNumber("quality-score", stats.quality_score);
        animateNumber("skill-count", stats.skill_count);
        animateNumber("word-count", stats.word_count);
        animateNumber("jobs-count", jobs.length);

        // Animate quality ring
        setTimeout(() => {
            const ring = document.getElementById("quality-ring");
            if (ring) {
                const circumference = 2 * Math.PI * 52; // r=52
                const offset = circumference * (1 - stats.quality_score / 100);
                ring.style.strokeDasharray = circumference;
                ring.style.strokeDashoffset = offset;

                // Dynamic color based on score
                const color = stats.quality_score >= 70
                    ? "var(--accent-green)"
                    : stats.quality_score >= 40
                        ? "var(--accent-orange)"
                        : "var(--accent-red)";
                ring.style.stroke = color;
            }
        }, 200);

        // Category prediction
        renderCategories(categories);
        renderClassificationState(data);

        // Skills breakdown
        renderSkills(skills);

        // Skills Gap Roadmap
        renderSkillsGap(data.skills_gap);

        // Job recommendations
        renderJobs(jobs);
        renderRankingMeta(data);

        // Always return to overview after fresh analysis to avoid stale hidden states
        if (typeof window.switchDashboardView === "function") {
            window.switchDashboardView("view-overview", false);
        }
    }

    function renderClassificationState(data) {
        if (!categoryStatusBanner || !categoryStatusText || !categoryConfirmPanel || !categoryConfirmOptions) {
            return;
        }

        const state = data.classification_state || "high_confidence";
        const topConfidence = Math.round((data.top_confidence || 0) * 100);
        const choices = Array.isArray(data.confirmation_choices) ? data.confirmation_choices : [];
        const analysisCategory = data.analysis_category || "";

        categoryStatusBanner.style.display = "block";
        categoryStatusBanner.classList.remove("low-confidence", "high-confidence");
        categoryConfirmPanel.style.display = "none";
        categoryConfirmOptions.innerHTML = "";

        if (state === "low_confidence") {
            categoryStatusBanner.classList.add("low-confidence");
            categoryStatusText.textContent = `Low confidence (${topConfidence}%). Confirm your category to improve matching quality.`;
            categoryConfirmPanel.style.display = "block";

            choices.forEach((choice) => {
                const btn = document.createElement("button");
                btn.type = "button";
                btn.className = "confirm-choice-btn";
                btn.textContent = choice;
                if (choice === analysisCategory) {
                    btn.classList.add("active");
                }
                btn.addEventListener("click", async () => {
                    const remember = categoryRememberCheckbox ? categoryRememberCheckbox.checked : false;
                    await runAnalysis({
                        confirmedCategory: choice,
                        rememberCategory: remember,
                    });
                });
                categoryConfirmOptions.appendChild(btn);
            });
        } else {
            categoryStatusBanner.classList.add("high-confidence");
            categoryStatusText.textContent = `High confidence (${topConfidence}%). Category used: ${analysisCategory}.`;
        }
    }

    function renderRankingMeta(data) {
        if (!rankingMeta) return;

        const source = data.ranking_source || "";
        const budgetExceeded = Boolean(data.ranking_budget_exceeded);
        let message = "";

        if (budgetExceeded) {
            message = "Ranking budget exceeded, showing current live order for faster response.";
        } else if (source === "live_hybrid") {
            message = "Hybrid ranking active: TF-IDF + skill overlap + category boost.";
        } else if (source === "live_api_raw") {
            message = "Live jobs shown in API order.";
        } else if (source === "local_fallback") {
            message = "Live API unavailable, using local ranked fallback jobs.";
        }

        if (!message) {
            rankingMeta.style.display = "none";
            rankingMeta.textContent = "";
            return;
        }

        rankingMeta.textContent = message;
        rankingMeta.classList.toggle("warning", budgetExceeded);
        rankingMeta.style.display = "block";
    }

    function animateNumber(elementId, target) {
        const el = document.getElementById(elementId);
        if (!el) return;
        const duration = 1000;
        const start = performance.now();

        function update(now) {
            const elapsed = now - start;
            const progress = Math.min(elapsed / duration, 1);
            // Ease out cubic
            const eased = 1 - Math.pow(1 - progress, 3);
            const current = Math.round(eased * target);
            el.textContent = current;
            if (progress < 1) requestAnimationFrame(update);
        }
        requestAnimationFrame(update);
    }

    function renderCategories(categories) {
        const container = document.getElementById("category-bars");
        container.innerHTML = "";

        categories.forEach((cat, idx) => {
            const confidence = Math.round(cat.confidence * 100);
            const item = document.createElement("div");
            item.className = "category-bar-item";
            item.innerHTML = `
                <span class="category-name">${escapeHtml(cat.category)}</span>
                <div class="category-bar-bg">
                    <div class="category-bar-fill top-${idx + 1}" style="width: 0%">
                        <span class="category-bar-value">${confidence}%</span>
                    </div>
                </div>
            `;
            container.appendChild(item);

            // Animate bar
            setTimeout(() => {
                const fill = item.querySelector(".category-bar-fill");
                fill.style.width = Math.max(confidence, 8) + "%";
            }, 300 + idx * 150);
        });
    }

    function renderSkills(skills) {
        const container = document.getElementById("skills-groups");
        container.innerHTML = "";

        const grouped = skills.grouped;
        if (!grouped || Object.keys(grouped).length === 0) {
            container.innerHTML = `
                <div style="text-align: center; color: var(--text-muted); padding: 2rem;">
                    No specific skills detected. Consider adding more technical skills to your resume.
                </div>
            `;
            return;
        }

        Object.entries(grouped).forEach(([domain, skillList], idx) => {
            const group = document.createElement("div");
            group.className = "skill-group";
            group.setAttribute("data-domain", domain);
            group.style.animationDelay = (idx * 0.1) + "s";

            const badges = skillList
                .map((s) => `<span class="skill-badge">${escapeHtml(s)}</span>`)
                .join("");

            group.innerHTML = `
                <div class="skill-group-title">${escapeHtml(domain)}</div>
                <div class="skill-badges">${badges}</div>
            `;
            container.appendChild(group);
        });
    }

    function renderSkillsGap(gap) {
        const block = document.getElementById("skills-gap-block");
        if (!gap) {
            block.style.display = "none";
            return;
        }

        block.style.display = "block";
        document.getElementById("gap-target-category").textContent = gap.target_category;
        
        // Render Matched
        const matchedList = document.getElementById("gap-matched-list");
        matchedList.innerHTML = gap.matched_skills.map(s => `
            <div class="gap-skill-item">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--accent-green)" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
                ${escapeHtml(s)}
            </div>
        `).join("") || '<p style="font-size:0.8rem; color:var(--text-muted);">No core skills matched yet.</p>';

        // Render Missing
        const missingList = document.getElementById("gap-missing-list");
        missingList.innerHTML = gap.missing_skills.map(s => `
            <div class="gap-skill-item">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--accent-red)" stroke-width="3"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                ${escapeHtml(s)}
                <button class="learn-btn" onclick="window.open('https://www.youtube.com/results?search_query=learn+${encodeURIComponent(s)}+for+${encodeURIComponent(gap.target_category)}', '_blank')">Learn</button>
            </div>
        `).join("") || '<p style="font-size:0.8rem; color:var(--accent-green);">You have mastered all core skills! ðŸ†</p>';

        // Animate Circle
        const score = gap.readiness_score;
        const path = document.getElementById("readiness-path");
        const text = document.getElementById("readiness-percentage");
        
        // Reset
        path.style.strokeDasharray = "0, 100";
        text.textContent = "0%";

        setTimeout(() => {
            path.style.strokeDasharray = `${score}, 100`;
            
            // Animate text
            let current = 0;
            const step = score / 50;
            const interval = setInterval(() => {
                current += step;
                if (current >= score) {
                    text.textContent = Math.round(score) + "%";
                    clearInterval(interval);
                } else {
                    text.textContent = Math.round(current) + "%";
                }
            }, 20);
        }, 500);
    }

    function renderJobs(jobs) {
        const container = document.getElementById("jobs-grid");
        container.innerHTML = "";

        if (!jobs || jobs.length === 0) {
            container.innerHTML = `
                <div style="text-align: center; color: var(--text-muted); padding: 2rem; grid-column: 1 / -1;">
                    No matching jobs found. Try uploading a more detailed resume.
                </div>
            `;
            return;
        }

        jobs.forEach((job, idx) => {
            const card = createJobCard(job, idx);
            container.appendChild(card);
        });

        // Set up filters
        setupJobFilters(jobs);
    }

    function createJobCard(job, idx) {
        const card = document.createElement("div");
        card.className = "job-card";
        card.setAttribute("data-type", job.type);
        card.style.animationDelay = (idx * 0.08) + "s";

        // Match level
        const score = job.combined_score;
        let matchClass, matchLabel;
        if (score >= 40) { matchClass = "match-high"; matchLabel = `${score.toFixed(0)}% Match`; }
        else if (score >= 25) { matchClass = "match-medium"; matchLabel = `${score.toFixed(0)}% Match`; }
        else { matchClass = "match-low"; matchLabel = `${score.toFixed(0)}% Match`; }

        // Job type styling
        const typeClass = job.type === "internship" ? "job-type-internship" : "job-type-fulltime";
        const typeLabel = job.type === "internship" ? "Internship" : "Full-time";

        // Skills
        const matchedSkills = (job.matched_skills || [])
            .slice(0, 5)
            .map((s) => `<span class="job-skill-matched">\u2713 ${escapeHtml(s)}</span>`)
            .join("");
        const missingSkills = (job.missing_skills || [])
            .slice(0, 3)
            .map((s) => `<span class="job-skill-missing">\u2717 ${escapeHtml(s)}</span>`)
            .join("");

        card.innerHTML = `
            <div class="job-card-header">
                <div class="job-title">${escapeHtml(job.title)}</div>
                <span class="job-card-match ${matchClass}">${matchLabel}</span>
            </div>
            <div class="job-company">${escapeHtml(job.company)}</div>
            <div class="job-meta">
                <span class="job-meta-tag job-type-tag ${typeClass}">${typeLabel}</span>
                <span class="job-meta-tag">${escapeHtml(job.location)}</span>
                <span class="job-meta-tag">${escapeHtml(job.experience_level)}</span>
            </div>
            <div class="job-description">${escapeHtml(job.description)}</div>
            ${matchedSkills || missingSkills ? `
            <div class="job-skills-section">
                ${matchedSkills ? `
                    <div class="job-skills-label">Matched Skills</div>
                    <div class="job-skills-list">${matchedSkills}</div>
                ` : ""}
                ${missingSkills ? `
                    <div class="job-skills-label" style="margin-top: 8px;">Skills to Develop</div>
                    <div class="job-skills-list">${missingSkills}</div>
                ` : ""}
            </div>
            ` : ""}
            <div class="job-footer">
                <span class="job-salary">${escapeHtml(job.salary_range)}</span>
                ${job.has_applied ? 
                    `<button class="job-apply-btn disabled" style="background:var(--bg-card-alt);color:var(--text-muted);cursor:not-allowed;" disabled>Applied \u2713</button>` :
                    `<button class="job-apply-btn">Apply \u2192</button>`
                }
            </div>
        `;

        // Attach click handler via JS (not inline onclick) to avoid quote-escaping issues
        if (!job.has_applied) {
            const applyBtn = card.querySelector(".job-apply-btn");
            applyBtn.addEventListener("click", function () {
                applyForJob(this, job.title, job.company, job.source, job.apply_url);
            });
        }

        return card;
    }

    // Apply for job: record in-app + redirect to the real application page
    window.applyForJob = function(btn, title, company, source, url) {
        if (!currentUser) {
            // Save intent to automatically apply/redirect after login!
            localStorage.setItem("pending_apply", JSON.stringify({ title, company, source, url }));
            window.location.href = '/login';
            return;
        }
        
        // Resolve a highly direct application URL or fallback to a premium, real-time professional job portal (LinkedIn)
        let applyUrl;
        if (url && url !== "#" && url !== "" && url !== "undefined" && url !== "null") {
            applyUrl = url;
        } else {
            // Clean job title (e.g. remove brackets or details)
            const cleanTitle = title.replace(/\(.*?\)/g, "").replace(/\[.*?\]/g, "").trim();
            const isInternship = source === "internship" || cleanTitle.toLowerCase().includes("intern") || cleanTitle.toLowerCase().includes("internship");
            const filterParam = isInternship ? "&f_E=1" : "&f_WT=2"; // f_E=1 for Internship experience level, f_WT=2 for remote filter
            applyUrl = `https://www.linkedin.com/jobs/search/?keywords=${encodeURIComponent(cleanTitle)}${filterParam}`;
        }

        // Open direct job listing / search tab
        try {
            const win = window.open(applyUrl, '_blank');
            if (!win) {
                // Fallback using dynamic link element if window.open is blocked
                const link = document.createElement("a");
                link.href = applyUrl;
                link.target = "_blank";
                link.rel = "noopener noreferrer";
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            }
        } catch (e) {
            console.error("Popup block fallback trigger: ", e);
            // Absolute fallback
            const link = document.createElement("a");
            link.href = applyUrl;
            link.target = "_blank";
            link.rel = "noopener noreferrer";
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }

        // Run the API call asynchronously
        (async () => {
            try {
                const response = await fetch("/api/apply", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        job_title: title,
                        company: company,
                        job_source: source,
                        job_url: url || ""
                    })
                });
                const data = await response.json();
                
                if (!response.ok) {
                    if (data.auth_required) {
                        window.location.href = '/login';
                        return;
                    }
                    throw new Error(data.error || "Failed to apply.");
                }
                
                // Update button state
                if (btn) {
                    btn.textContent = "Applied \u2713";
                    btn.disabled = true;
                    btn.classList.add("disabled");
                    btn.style.background = "var(--bg-card-alt)";
                    btn.style.color = "var(--text-muted)";
                    btn.style.cursor = "not-allowed";
                    const clone = btn.cloneNode(true);
                    btn.parentNode.replaceChild(clone, btn);
                }

                showSuccess(data.message || `Application recorded for ${company}!`);
                
            } catch (err) {
                showError(err.message);
            }
        })();
    };

    // â”€â”€ Quality Modal Logic â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    const qualityModal = document.getElementById("quality-modal");
    const qualityClose = document.getElementById("quality-close");
    const qualityList = document.getElementById("quality-breakdown-list");

    window.openQualityModal = function() {
        if (!currentQualityReport) return;
        
        qualityModal.style.display = "flex";
        renderQualityBreakdown();
    };

    if (qualityClose) {
        qualityClose.addEventListener("click", () => {
            qualityModal.style.display = "none";
        });
    }

    function renderQualityBreakdown() {
        const report = currentQualityReport;
        const breakdown = report.breakdown;
        
        qualityList.innerHTML = "";
        
        Object.entries(breakdown).forEach(([key, data]) => {
            const item = document.createElement("div");
            item.className = "q-item";
            item.innerHTML = `
                <div class="q-row">
                    <span class="q-text">${escapeHtml(data.label)}</span>
                    <span class="q-val">${data.score}%</span>
                </div>
                <div class="q-bar-bg">
                    <div class="q-bar-fill" style="width: 0%"></div>
                </div>
                <div class="q-feedback">${escapeHtml(data.feedback)}</div>
            `;
            qualityList.appendChild(item);
            
            // Animate bar
            setTimeout(() => {
                item.querySelector(".q-bar-fill").style.width = data.score + "%";
            }, 100);
        });

        document.getElementById("quality-modal-summary").textContent = report.summary;
    }

    // â”€â”€ Filter Jobs â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    function setupJobFilters(jobs) {
        const filterBtns = document.querySelectorAll(".filter-btn");
        filterBtns.forEach((btn) => {
            btn.addEventListener("click", () => {
                filterBtns.forEach((b) => b.classList.remove("active"));
                btn.classList.add("active");

                const filter = btn.getAttribute("data-filter");
                const cards = document.querySelectorAll(".job-card");
                cards.forEach((card) => {
                    const type = card.getAttribute("data-type");
                    if (filter === "all" || type === filter) {
                        card.style.display = "";
                    } else {
                        card.style.display = "none";
                    }
                });
            });
        });
    }

    // â”€â”€ Error Handling â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    function showError(message) {
        errorMessage.textContent = message;
        errorToast.style.display = "block";
        setTimeout(() => {
            errorToast.style.display = "none";
        }, 8000);
    }

    errorClose.addEventListener("click", () => {
        errorToast.style.display = "none";
    });

    // â”€â”€ Try Again â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    tryAgainBtn.addEventListener("click", () => {
        resultsSection.style.display = "none";
        uploadSection.style.display = "";
        document.body.classList.remove("results-mode");
        resetUpload();
        uploadSection.scrollIntoView({ behavior: "smooth", block: "center" });
    });

    // â”€â”€ Smooth Scroll for Nav Links â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    document.querySelectorAll('a[href^="#"]').forEach((link) => {
        link.addEventListener("click", (e) => {
            const target = document.querySelector(link.getAttribute("href"));
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: "smooth", block: "start" });
            }
        });
    });

    // â”€â”€ Navbar scroll effect â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    let lastScroll = 0;
    window.addEventListener("scroll", () => {
        const navbar = document.getElementById("navbar");
        const scroll = window.scrollY;
        const isLight = document.documentElement.getAttribute("data-theme") === "light";
        if (scroll > 50) {
            navbar.style.background = isLight ? "rgba(245, 247, 251, 0.95)" : "rgba(10, 10, 15, 0.95)";
        } else {
            navbar.style.background = isLight ? "rgba(245, 247, 251, 0.8)" : "rgba(10, 10, 15, 0.7)";
        }
        lastScroll = scroll;
    });

    // â”€â”€ Utility â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    function escapeHtml(text) {
        if (!text) return "";
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }

    // â”€â”€ Auth Handling â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    
    // Check auth on load
    async function checkAuth() {
        try {
            const res = await fetch("/auth/me");
            const data = await res.json();
            if (data.authenticated) {
                currentUser = data.user;
                updateAuthUI();

                // Handle pending application from before login
                const pending = localStorage.getItem("pending_apply");
                if (pending) {
                    localStorage.removeItem("pending_apply");
                    try {
                        const { title, company, source, url } = JSON.parse(pending);
                        applyForJob(null, title, company, source, url);
                    } catch (e) {
                        console.error("Failed to parse pending application", e);
                    }
                }
            }
        } catch (e) {
            console.error("Auth check failed", e);
        }
    }

    function updateAuthUI() {
        if (currentUser) {
            navLoginBtn.style.display = "none";
            userMenu.style.display = "block";
            navMyAppsBtn.style.display = "block";
            
            userAvatar.textContent = currentUser.name.charAt(0).toUpperCase();
            userNameNav.textContent = currentUser.name.split(" ")[0];
            userDropdownName.textContent = currentUser.name;
            userDropdownEmail.textContent = currentUser.email;
        } else {
            navLoginBtn.style.display = "flex";
            userMenu.style.display = "none";
            navMyAppsBtn.style.display = "none";
        }
    }

    // Toggle Dropdown
    if (userAvatarBtn) {
        userAvatarBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            userDropdown.classList.toggle("show");
        });
    }

    document.addEventListener("click", (e) => {
        if (userDropdown && userDropdown.classList.contains("show") && !userMenu.contains(e.target)) {
            userDropdown.classList.remove("show");
        }
    });

    // Auth Modal
    window.openAuthModal = function(tab = 'login') {
        if (!authOverlay) {
            window.location.href = "/login";
            return;
        }
        authOverlay.style.display = "flex";
        switchAuthTab(tab);
    };

    if (authClose) {
        authClose.addEventListener("click", () => {
            authOverlay.style.display = "none";
        });
    }

    authTabs.forEach(tab => {
        tab.addEventListener("click", () => {
            switchAuthTab(tab.getAttribute("data-tab"));
        });
    });

    function switchAuthTab(tabName) {
        if (!loginForm || !signupForm) return;
        authTabs.forEach(t => t.classList.remove("active"));
        const activeTab = document.querySelector(`.auth-tab[data-tab="${tabName}"]`);
        if (activeTab) activeTab.classList.add("active");
        
        if (tabName === 'login') {
            loginForm.style.display = "flex";
            signupForm.style.display = "none";
        } else {
            loginForm.style.display = "none";
            signupForm.style.display = "flex";
        }
        loginError.textContent = "";
        signupError.textContent = "";
    }

    // Submit Forms
    if (loginForm) {
        loginForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const email = document.getElementById("login-email").value;
            const password = document.getElementById("login-password").value;
            
            try {
                const res = await fetch("/auth/login", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ email, password })
                });
                const data = await res.json();
                
                if (!res.ok) throw new Error(data.error);
                
                currentUser = data.user;
                updateAuthUI();
                authOverlay.style.display = "none";
                showSuccess(data.message);
                loginForm.reset();
            } catch (err) {
                loginError.textContent = err.message;
            }
        });
    }

    if (signupForm) {
        signupForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const name = document.getElementById("signup-name").value;
            const email = document.getElementById("signup-email").value;
            const password = document.getElementById("signup-password").value;
            
            try {
                const res = await fetch("/auth/signup", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ name, email, password })
                });
                const data = await res.json();
                
                if (!res.ok) throw new Error(data.error);
                
                currentUser = data.user;
                updateAuthUI();
                authOverlay.style.display = "none";
                showSuccess(data.message);
                signupForm.reset();
            } catch (err) {
                signupError.textContent = err.message;
            }
        });
    }

    if (logoutBtn) {
        logoutBtn.addEventListener("click", async () => {
            try {
                await fetch("/auth/logout");
                currentUser = null;
                updateAuthUI();
                userDropdown.classList.remove("show");
                showSuccess("Successfully logged out");
                
                // If on results, maybe hide it
                if (document.body.classList.contains("results-mode")) {
                    resultsSection.style.display = "none";
                    uploadSection.style.display = "";
                    document.body.classList.remove("results-mode");
                    resetUpload();
                }
            } catch (e) {
                console.error("Logout failed", e);
            }
        });
    }

    function showSuccess(message) {
        if (!successToast) return;
        successMessage.textContent = message;
        successToast.style.display = "block";
        setTimeout(() => {
            successToast.style.display = "none";
        }, 5000);
    }

    // â”€â”€ My Applications Modal â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    
    if (navMyAppsBtn) {
        navMyAppsBtn.addEventListener("click", (e) => {
            e.preventDefault();
            openAppsModal();
        });
    }

    if (navAppsBtn) {
        navAppsBtn.addEventListener("click", (e) => {
            e.preventDefault();
            openAppsModal();
        });
    }

    if (appsClose) {
        appsClose.addEventListener("click", () => {
            appsModal.style.display = "none";
        });
    }
    
    // Close modal on escape
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && appsModal && appsModal.style.display === "flex") {
            appsModal.style.display = "none";
        }
    });

    function openAppsModal() {
        if (!currentUser) {
            window.location.href = "/login";
            return;
        }
        appsModal.style.display = "flex";
        loadApplications();
    }

    async function loadApplications() {
        appsListContainer.innerHTML = `
            <div class="loading-apps" style="text-align: center; padding: 3rem;">
                <div class="spinner-ring" style="position: static; display: inline-block; width: 40px; height: 40px; border-width: 2px;"></div>
                <p style="margin-top: 1rem; color: var(--text-muted);">Loading your applications...</p>
            </div>
        `;

        try {
            const res = await fetch("/api/applications");
            const data = await res.json();

            if (!res.ok) throw new Error(data.error || "Failed to load applications");

            renderApplicationsList(data.applications);
        } catch (e) {
            appsListContainer.innerHTML = `
                <div class="error-state" style="text-align: center; padding: 3rem; color: var(--accent-red);">
                    <p>${escapeHtml(e.message)}</p>
                    <button class="btn btn-ghost" onclick="loadApplications()" style="margin-top: 1rem;">Retry</button>
                </div>
            `;
        }
    }

    function renderApplicationsList(apps) {
        if (!apps || apps.length === 0) {
            appsListContainer.innerHTML = `
                <div class="empty-apps-state">
                    <div class="empty-apps-icon">
                        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>
                    </div>
                    <h3>No Applications Yet</h3>
                    <p>Start applying to jobs to see them tracked here!</p>
                </div>
            `;
            return;
        }

        appsListContainer.innerHTML = "";
        apps.forEach(app => {
            const date = new Date(app.applied_at).toLocaleDateString(undefined, { 
                month: 'short', 
                day: 'numeric', 
                year: 'numeric' 
            });
            const item = document.createElement("div");
            item.className = "app-item";
            item.innerHTML = `
                <div class="app-info">
                    <h4>${escapeHtml(app.job_title)}</h4>
                    <p>${escapeHtml(app.company)} \u2022 ${escapeHtml(app.job_source)}</p>
                </div>
                <div class="app-status">
                    <span class="status-badge status-applied">Applied</span>
                    <span class="app-date">${date}</span>
                </div>
            `;
            
            // Make clickable if there's a URL
            if (app.job_url && app.job_url !== "#") {
                item.style.cursor = "pointer";
                item.addEventListener("click", () => window.open(app.job_url, "_blank"));
            }
            
            appsListContainer.appendChild(item);
        });
    }

    // Expose globally for retry buttons
    window.loadApplications = loadApplications;

    // â”€â”€ AI Optimization Lab â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    const aiRefineBtn = document.getElementById("ai-refine-btn");
    const aiRefineInput = document.getElementById("ai-refine-input");
    const aiOutputGroup = document.getElementById("ai-refine-output-group");
    const aiOutputText = document.getElementById("ai-refine-output");
    const aiCopyBtn = document.getElementById("ai-copy-btn");

    if (aiRefineBtn) {
        aiRefineBtn.addEventListener("click", async () => {
            const text = aiRefineInput.value.trim();
            if (!text) {
                showError("Please enter some text to refine.");
                return;
            }

            // Show loading state on button
            const btnText = aiRefineBtn.querySelector(".btn-text");
            const btnLoader = aiRefineBtn.querySelector(".btn-loader");
            
            aiRefineBtn.disabled = true;
            if (btnText) btnText.style.opacity = "0.5";
            if (btnLoader) btnLoader.style.display = "block";

            try {
                const res = await fetch("/api/optimize/stream", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ text })
                });

                if (!res.ok) {
                    let data;
                    try {
                        data = await res.json();
                    } catch (e) {
                        throw new Error(`Server returned an invalid response (${res.status}). The AI service might be down.`);
                    }
                    if (res.status === 401 || data.auth_required) {
                        showError("Please sign in to access personalized AI refinements.");
                        window.location.href = '/login';
                        return;
                    }
                    throw new Error(data.error || `Optimization failed with status ${res.status}`);
                }

                if (!res.body) {
                    // Fallback to non-stream if body stream is not available
                    const fallbackRes = await fetch("/api/optimize", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ text })
                    });
                    const fallbackData = await fallbackRes.json();
                    if (!fallbackRes.ok) throw new Error(fallbackData.error || "Optimization failed");
                    aiOutputText.textContent = fallbackData.optimized;
                    aiOutputGroup.style.display = "block";
                    aiOutputGroup.scrollIntoView({ behavior: "smooth", block: "nearest" });
                    showSuccess("AI Optimization complete!");
                    return;
                }

                // Stream response handling
                aiOutputText.textContent = "";
                aiOutputGroup.style.display = "block";
                aiOutputGroup.scrollIntoView({ behavior: "smooth", block: "nearest" });

                const reader = res.body.getReader();
                const decoder = new TextDecoder();
                let done = false;
                let buffer = "";

                while (!done) {
                    const { value, done: readerDone } = await reader.read();
                    done = readerDone;
                    if (value) {
                        const chunk = decoder.decode(value, { stream: !done });
                        buffer += chunk;
                        
                        // Check if error occurred inside the generator stream
                        if (buffer.includes("[STREAM_ERROR:")) {
                            const errorMatch = buffer.match(/\[STREAM_ERROR:\s*(.*?)\]/);
                            const errorMsg = errorMatch ? errorMatch[1] : "Stream error occurred";
                            throw new Error(errorMsg);
                        }

                        aiOutputText.textContent = buffer;
                    }
                }

                showSuccess("AI Optimization complete!");
            } catch (err) {
                console.error("Optimization Error:", err);
                const msg = err.message === 'Failed to fetch' 
                    ? "Could not connect to the server. Please ensure the backend is running."
                    : err.message;
                showError(msg);
            } finally {
                aiRefineBtn.disabled = false;
                if (btnText) btnText.style.opacity = "1";
                if (btnLoader) btnLoader.style.display = "none";
            }
        });
    }

    if (aiCopyBtn) {
        aiCopyBtn.addEventListener("click", () => {
            const text = aiOutputText.textContent;
            if (!text) return;

            navigator.clipboard.writeText(text).then(() => {
                showSuccess("Copied to clipboard!");
            }).catch(err => {
                showError("Failed to copy text.");
            });
        });
    }

    // â”€â”€ DASHBOARD VIEW ROUTER â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    function switchDashboardView(targetId, smoothScroll = true) {
        const targetView = document.getElementById(targetId);
        if (!targetView) {
            console.warn(`Dashboard view "${targetId}" not found.`);
            return;
        }

        sidebarLinks.forEach((link) => {
            if (link.getAttribute("data-target") === targetId) {
                link.classList.add("active");
            } else {
                link.classList.remove("active");
            }
        });

        dashboardViews.forEach((view) => {
            if (view.id === targetId) {
                view.classList.add("active");
                view.style.display = "block";
            } else {
                view.classList.remove("active");
                view.style.display = "none";
            }
        });

        if (smoothScroll) {
            if (dashboardContent) {
                dashboardContent.scrollTo({ top: 0, behavior: "smooth" });
            } else {
                window.scrollTo({ top: 0, behavior: "smooth" });
            }
        } else if (dashboardContent) {
            dashboardContent.scrollTop = 0;
        }
    }

    window.switchDashboardView = switchDashboardView;

    sidebarLinks.forEach((link) => {
        link.addEventListener("click", (e) => {
            e.preventDefault();
            const targetId = link.getAttribute("data-target");
            if (targetId) switchDashboardView(targetId);
        });
    });

    // Initialize Auth
    checkAuth();
})();

