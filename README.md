# Schedule I Mod Menu

## Features
- Basic Command Line Interface
- Clean trash from `.json` files
- Permanently disable or re-enable Trash Generation (Does not prevent user or NPC-generated trash from spawning)
- Executable file ready to go in Releases (https://github.com/XOWithSauce/schedule-mod/releases/download/v1.0/ScheduleMods.exe)

## How To Use
- Download the executable from Releases section
- Run the file and choose from the displayed options

## How to Build from Source
1. Clone the repository:
   ```sh
   git clone https://github.com/XOWithSauce/schedule-mod.git
   cd schedule-mod
   ```
2. Build an executable with PyInstaller:
   ```sh
   pyinstaller main.py --onefile
   ```
   This will create a standalone executable in the `dist/` folder.

3. (Optional) Run the script without building:
   ```sh
   python main.py
   ```

