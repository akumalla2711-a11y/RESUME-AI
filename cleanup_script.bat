@echo off
echo Cleaning up unnecessary files...

del /Q Resume.csv
del /Q test_gemini.py
del /Q test_models.py
del /Q verify_gemini.py
del /Q fix_html.py
del /Q fix_html_regex.py
del /Q modify_html.py
del /Q modify_js.py
del /Q generate_notebook.py
del /Q cookies.txt
del /Q verify_cookie.txt
del /Q test_resume.txt
del /Q recruiter_summaries.txt
del /Q resume_processing.log
del /Q server_run.log
del /Q server.out.log
del /Q Resume_ATS_System.ipynb
del /Q Resume_ATS_System_v2.ipynb

rmdir /S /Q .ipynb_checkpoints

echo Cleanup complete! The unnecessary files and 56MB of waste have been removed.
echo You can now close this window and delete this 'cleanup_script.bat' file too!
pause
