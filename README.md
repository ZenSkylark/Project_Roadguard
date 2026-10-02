# Roadguard Software
The Main Software that is Dedicated for the Entire Project
It is most the Server Side


# Instructions on How to Operate for Version 2.1-alpha
- It is highly Recommend to Open 3 Open Different Terminals to Run Simultaneously

## Requirements
- Uses Python 3.12 for its Stable Use make sure to have a Global Interpreter

### BackEnd
1. Open New Terminal in VS Code
2. Type `C:\...\Roadguard\Software` to change Directory
3. Type `.\server_env\Scripts\Activate.ps1` to Allow in Activating the Script
4. Type `uvicorn backend.main:app --reload -port 8000` to Run the Backend Server

### FrontEnd
1. Open New Terminal in VS Code
2. Type `C:\...\Roadguard\Software\frontend` to change Directory
3. Type `.\server_env\Scripts\Activate.ps1` to Allow in Activating the Script (Optional but try making the use of .venv)
4. Type `npm run dev` to Run the FrontEnd Server

### How to Access Dashboard
1. Run `http://localhost:5173`
2. Enter the Credentials created default by the Code: Username:`admin` and Password:`Admin123!`
3. MFA Step (If Activated): Check the BackEnd Terminal there should be a `A OTP Given`

## Developer Stuff

## How to Run the Edge Simulator
1. Check if Both FrontEnd and BackEnd Are Active
2. Open New Terminal in VS Code
3. Type `C:\...\Roadguard\Software` to change Directory
4. Type `.\server_env\Scripts\Activate.ps1` to Allow in Activating the Script
5. Type `python edge\simulator` to Run the Simulations
6. Press `P` for With License, `V` for Without License, `O` for Aged Readable License, `U` for Aged Unreadable License and Q to Quit the Simulator

## How to Run the Tests (To see if it Passed or Fails)
1. Open New Terminal in VS Code
2. Type `C:\...\Roadguard\Software` to change Directory
3. Type `.\server_env\Scripts\Activate.ps1` to Allow in Activating the Script
4. Type `python -m pytest tests/ -v` to Run the Test
5. It Must All Pass to make sure it the Software Runs as Intended

## How to Run the Tests (To see if it Passed or Fails)
1. Open New Terminal in VS Code
2. Type `.\server_env\Scripts\Activate.ps1` to Allow in Activating the Script
3. To Run This What are its Use and Purpose
   1. Type `python tools\make_test_plates.py --count 5` to Create 5 Fake Plates
   2. Type `python tools\ocr_check.py test_plates\plate_00_ABC1234.jpg` to select and see the OCR Check for that Specific File
   3. Type `python tools\ocr_batch.py` to see all of the OCR Check in the Directory
   4. Type `python tools\test_mailtrap_direct.py` to see if Email has been Sent in the Simulation
   5. Type `python tools\test_resend_direct.py` to see if Email has been Sent to the Production using Resend (Inactive Feature)

## How to Change Email Delivery System (Mailtrap)
1. Go to `Roadguard\Software\.env`
2. Look for the Following
   1.  MAILTRAP_USERNAME=(266acb407b9615) - Found In Credentials
   2.  MAILTRAP_PASSWORD=(954212bcfdb008) - Found In Credentials
   3.  MAILTRAP_FROM=noreply@roadguard.ph - Choose Whatever Name You Like
3.  Go to [Mailtrap](https://mailtrap.io/sandboxes/)
4.  Look for Credentials
5.  Copy and Paste It
6.  Your Done, Try to Test out using `python tools\test_mailtrap_direct.py`


# System Dependencies that Weren't Included in the pip

### System dependencies (not installed by pip)
- **Tesseract OCR binary** — needed by `tools/ocr_*.py`
  Installer: https://github.com/UB-Mannheim/tesseract/wiki (default path auto-detected)
- **PaddleOCR models** — downloaded automatically on first backend OCR use

