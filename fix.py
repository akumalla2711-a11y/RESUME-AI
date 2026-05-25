import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# We know the duplicate starts with <button class="theme-toggle" id="theme-toggle"
# and ends right before <!-- File Preview --> in the upload section.
# We also have an issue where <div class="upload-icon-wrapper"> is duplicated.

# Let's just fix it properly by finding the first <!-- ═══════════════════ UPLOAD SECTION ═══════════════════ -->
# and everything before it, and then appending the clean upload section, loading section, and results section.

clean_part_1 = content.split('<!-- ═══════════════════ UPLOAD SECTION ═══════════════════ -->')[0]

clean_part_2 = """<!-- ═══════════════════ UPLOAD SECTION ═══════════════════ -->
<section class="section upload-section" id="upload-section">
    <div class="container">
        <div class="section-header">
            <span class="section-badge">Get Started</span>
            <h2 class="section-title">Analyze Your Resume</h2>
            <p class="section-subtitle">Upload your resume and let AI do the heavy lifting</p>
        </div>

        <div class="upload-wrapper">
            <div class="upload-zone" id="upload-zone">
                <div class="upload-zone-content">
                    <div class="upload-icon-wrapper">
                        <svg class="upload-icon" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                            <polyline points="17 8 12 3 7 8"/>
                            <line x1="12" y1="3" x2="12" y2="15"/>
                        </svg>
                    </div>
                    <h3 class="upload-title">Drop your resume here</h3>
                    <p class="upload-subtitle">or <span class="upload-browse" id="upload-browse">browse files</span></p>
                    <p class="upload-formats">Supports PDF, DOCX, TXT — Max 10 MB</p>
                </div>
                <input type="file" id="file-input" accept=".pdf,.docx,.doc,.txt" hidden>
            </div>

            <!-- File Preview -->
            <div class="file-preview" id="file-preview" style="display: none;">
                <div class="file-preview-info">
                    <div class="file-icon" id="file-icon">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                    </div>
                    <div class="file-details">
                        <span class="file-name" id="file-name"></span>
                        <span class="file-size" id="file-size"></span>
                    </div>
                    <button class="file-remove" id="file-remove" aria-label="Remove file">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                    </button>
                </div>
                <button class="btn btn-primary btn-lg btn-analyze" id="analyze-btn">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10"/></svg>
                    Analyze Resume
                </button>
            </div>
        </div>
    </div>
</section>

</div> <!-- End view-landing -->
"""

clean_part_3 = "<!-- ═══════════════════ LOADING STATE ═══════════════════ -->" + content.split('<!-- ═══════════════════ LOADING STATE ═══════════════════ -->')[-1]

final_html = clean_part_1 + clean_part_2 + clean_part_3

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(final_html)

print("Successfully fixed index.html!")
