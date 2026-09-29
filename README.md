# Roadguard Software
The Main Software that is Dedicated for the Entire Project
Uses Python 3.12 for its Stable Use make sure to have a Global Interpreter



# Instructions on How to Operate for Version 1.0.3-alpha
- It is highly Recommend to Open 3 Open Different Terminals to Run Simultaneously (BackEnd, FrontEnd, and Simulator)

## BackEnd
1. Open New Terminal in VS Code
2. Type `C:\...\Roadguard\Software` to change Directory
3. Type `.\server_env\Scripts\Activate.ps1` to Allow in Activating the Script
4. Type `uvicorn backend.main:app --reload -port 8000` to Run the Backend Server

## FrontEnd
1. Open New Terminal in VS Code
2. Type `C:\...\Roadguard\Software\frontend` to change Directory
3. Type `.\server_env\Scripts\Activate.ps1` to Allow in Activating the Script
4. Type `npm run dev` to Run the Backend Server

## How to Access Dashboard
1. Run `http://localhost:5173`
2. Enter the Credentials created default by the Code: Username:`admin` and Password:`Admin123!`
3. MFA Step (If Activated): Check the BackEnd Terminal there should be a `[DEV SMS]` and type the OTP

## How to Run the Edge Simulator
1. Open New Terminal in VS Code
2. Type `C:\...\Roadguard\Software` to change Directory
3. Type `.\server_env\Scripts\Activate.ps1` to Allow in Activating the Script
4. Type `python edge\simulator` to Run the Simulations
5. Press P for With License, V for Without License, and Q to Quit the Simulator
