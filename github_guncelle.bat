@echo off
cd /d "C:\Users\Doyuum\Desktop\restoran"

git add -A
git diff --cached --quiet
if %errorlevel% == 0 (
    echo Degisiklik yok, push atlanidi.
) else (
    git commit -m "Otomatik guncelleme - %date% %time%"
    git push
    echo GitHub guncellendi!
)
