@echo off
cd /d "C:\Users\aakhtari\Documents\MATLAB"
matlab -batch "run('run_plvhfo1.m')"
exit /b %ERRORLEVEL%
