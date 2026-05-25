import re

def fix_html():
    with open('templates/index.html', 'r', encoding='utf-8') as f:
        text = f.read()

    # Find the essential blocks by taking only their FIRST occurrence
    # 1. Everything up to NAVBAR
    nav_start = text.find('<!-- ═══════════════════ NAVBAR ═══════════════════ -->')
    head_part = text[:nav_start]

    # 2. NAVBAR up to LANDING VIEW
    landing_start = text.find('<!-- ═══════════════════ LANDING VIEW ═══════════════════ -->')
    nav_part = text[nav_start:landing_start]

    # 3. LANDING VIEW up to UPLOAD SECTION
    upload_start = text.find('<!-- ═══════════════════ UPLOAD SECTION ═══════════════════ -->')
    if upload_start == -1:
        # Fallback if the exact comment is missing
        upload_start = text.find('<section class="section upload-section" id="upload-section">')
    landing_part = text[landing_start:upload_start]

    # 4. UPLOAD SECTION up to LOADING STATE
    loading_start = text.find('<!-- ═══════════════════ LOADING STATE ═══════════════════ -->')
    upload_part = text[upload_start:loading_start]

    # Clean the upload part in case it has the duplicate nav/hero
    # The clean upload part should just be the section ending with </div> <!-- End view-landing -->
    upload_end = upload_part.find('</div> <!-- End view-landing -->')
    if upload_end != -1:
        upload_part = upload_part[:upload_end + len('</div> <!-- End view-landing -->') + 1]

    # 5. LOADING STATE to END
    # We only want the first loading state to the end, but we need to make sure there are no trailing duplicates
    loading_part = text[loading_start:]
    
    # Check if there is another NAVBAR inside the loading part (due to my previous duplication)
    second_nav = loading_part.find('<!-- ═══════════════════ NAVBAR ═══════════════════ -->')
    if second_nav != -1:
        loading_part = loading_part[:second_nav]

    final_html = head_part + nav_part + landing_part + upload_part + "\n" + loading_part

    # Ensure no duplicate navbar/music logic remains by stripping any extra scripts or audio tags
    final_html = re.sub(r'<audio id="ambient-music".*?</audio>', '', final_html, flags=re.DOTALL)
    
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(final_html)
    print("Fixed!")

fix_html()
