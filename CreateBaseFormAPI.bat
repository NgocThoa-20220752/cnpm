@echo off
@REM setlocal EnableDelayedExpansion
@REM set /p project_name="Nhập tên dự án FastAPI: "

@REM REM Tạo thư mục chính và đi vào
@REM mkdir %project_name%
@REM cd %project_name%

REM Tạo file main.py và requirements.txt rỗng
echo. > main.py
REM Tạo requirements.txt rỗng
echo fastapi > requirements.txt
echo uvicorn >> requirements.txt

REM Tạo thư mục app và các module con
mkdir app
cd app
mkdir api models schemas services core functions
mkdir api\v1

REM Tạo file __init__.py cho mỗi thư mục
(for %%f in ("." "api" "api\v1" "models" "schemas" "services" "core" "functions") do echo. > %%f\__init__.py)

REM Tạo các file task module (rỗng)
echo. > api\v1\order.py
echo. > api\v1\task.py
echo. > api\v1\render.py
echo. > models\objmodel.py
echo. > schemas\rules.py
echo. > services\objservice.py
echo. > core\config.py

cd ../..

echo Dự án FastAPI với cấu trúc file rỗng đã được tạo tại: %project_name%
pause
