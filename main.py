import struct
import os
import winreg
import json
import glob
import time

# Comparison instruction in the game - changes max trash limit
# The first 81 FB is an CMP asm instruction
# Latter D0 07 00 00 represents 2000 number (compare current trashcount to the number)
TRASH_LIMIT_PATTERN = bytes([0x81, 0xFB, 0xD0, 0x07, 0x00, 0x00])
# To revert back to original we have the following memory pattern in the dll file
TRASH_LIMIT_MOD_PATTERN = bytes([0x81, 0xFB, 0x02, 0x00, 0x00, 0x00])

# For Create trash functions we have 4 offset locations (First 2 are probably CreateTrashBag (offline+online), latter 2 CreateTrash functions)
# They all share same memory pattern of adding trash to the game so we can override the default 2000 limit with 2
TRASH_CRT_PATTERN = bytes([0x00, 0x81, 0x78, 0x18, 0xD0, 0x07, 0x00, 0x00])
TRASH_CRT_MOD_PATTERN = bytes([0x00, 0x81, 0x78, 0x18, 0x02, 0x00, 0x00, 0x00])

""" Region Modify the game assembly dll file """

def get_steam_install_path():
    """Retrieves Steam's main installation path from the Windows Registry."""
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam") as key:
            return winreg.QueryValueEx(key, "InstallPath")[0]
    except FileNotFoundError:
        return None

def get_game_assembly_path():
    """Finds the Schedule I directory and adjacent GameAssembly.dll file"""
    steam_path = get_steam_install_path()
    
    # Ensure Steam exists
    if not steam_path:
        print("Failed to locate Steam installation.")
        return None
    
    # Create a path to the dll file
    game_assembly_path = os.path.join(steam_path, "steamapps", "common", "Schedule I", "GameAssembly.dll")
    
    # Ensure path exists
    if not os.path.exists(game_assembly_path):
        print("Failed to locate Schedule I Game Assembly")
        return None    
    
    return game_assembly_path

# Function to find the pattern in the file
def find_pattern(dll_path, pattern):
    with open(dll_path, "rb") as f:
        data = f.read()
        index = data.find(pattern)
        if index == -1:
            print("Error: The expected pattern was not found in the file.")
            return None
        return index

def find_all_patterns(dll_path, pattern):
    with open(dll_path, "rb") as f:
        data = f.read()
        indexes = []
        index = data.find(pattern)
        while index != -1:
            indexes.append(index)
            index = data.find(pattern, index + 1)
        if not indexes:
            print(f"Error: The expected pattern was not found in the file.")
            return None
        return indexes

# Read and modify the Game Assembly trash pattern
def modify_trash_limit(dll_path, limit):
    trash_limit_pattern = TRASH_LIMIT_MOD_PATTERN if limit else TRASH_LIMIT_PATTERN
    trash_crt_pattern = TRASH_CRT_MOD_PATTERN if limit else TRASH_CRT_PATTERN

    offset = find_pattern(dll_path, trash_limit_pattern)
    crt_offsets = find_all_patterns(dll_path, trash_crt_pattern)

    if not offset or not crt_offsets:
        print("Offset not found")
        return

    # Determine the actual limit value (defaulting to 2000 if False)
    actual_limit = 2 if limit else 2000

    # Write the new limit
    with open(dll_path, "r+b") as f:
        f.seek(offset)
        f.write(trash_limit_pattern)
    print(f"Modified at offset {hex(offset)} to set max trash limit to {actual_limit}")

    # Modify trash creation function
    with open(dll_path, "r+b") as f:
        for off in crt_offsets:
            f.seek(off)
            f.write(trash_crt_pattern)
            print(f"Modified trash creation function at offset {hex(off)} to have max trash limit {actual_limit}")

def permanent_trash_gen(limit: int):
    path = get_game_assembly_path()
    modify_trash_limit(path, limit)
    return None


"""Region Clear Trash .json files"""

def get_saves_directory():
    """Finds the user's save game directory inside AppData/LocalLow/TVGS/Schedule I/Saves"""
    base_path = os.path.join(os.path.dirname(os.path.expandvars(r"%APPDATA%")), "LocalLow", "TVGS", "Schedule I", "Saves")
    print(base_path)
    if not os.path.exists(base_path):
        print("Error: Could not locate the Saves directory.")
        return None

    # Identify the folder with the Steam ID number
    for folder in os.listdir(base_path):
        steam_id_path = os.path.join(base_path, folder)
        if os.path.isdir(steam_id_path) and folder.isdigit():
            return steam_id_path
    
    print("Error: No valid Steam ID folder found inside Saves.")
    return None

def get_save_games():
    """Finds all save game folders and extracts the OrganisationName from Game.json"""
    saves_dir = get_saves_directory()
    if not saves_dir:
        return []

    save_games = []
    
    # Look for SaveGame_X folders
    for folder in sorted(os.listdir(saves_dir)):  
        save_path = os.path.join(saves_dir, folder)
        game_json_path = os.path.join(save_path, "Game.json")
        
        if os.path.isdir(save_path) and folder.startswith("SaveGame_") and os.path.exists(game_json_path):
            try:
                with open(game_json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    org_name = data.get("OrganisationName", "Unknown Save")  # Default if missing
                    save_games.append((folder, org_name, save_path))
            except (json.JSONDecodeError, IOError):
                print(f"Warning: Could not read {game_json_path}")

    return save_games

def select_save():
    """Prompts the user to select a save based on OrganisationName"""
    save_games = get_save_games()
    
    if not save_games:
        print("No save games found.")
        return None

    print("\nAvailable Options:")
    print("0 - Return to Menu")
    for i, (folder, org_name, _) in enumerate(save_games, 1):
        print(f"{i} - {org_name}")

    while True:
        choice = input("Select a save number: ")
        if choice == "0": #Return to menu
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(save_games):
            return save_games[int(choice) - 1][2]
        print("Invalid selection. Please enter a valid number.")

def clear_trash_task():
    """Clears the trash by emptying the 'Items' list in Trash.json and 'GeneratedItems' in all generator logs."""
    
    # Get path to SaveGame_X folder
    save_path = select_save()
    if not save_path:
        return
    
    trash_folder = os.path.join(save_path, "Trash")
    trash_file = os.path.join(trash_folder, "Trash.json")
    generators_folder = os.path.join(trash_folder, "Generators")

    # Clear Trash.json
    if os.path.exists(trash_file):
        try:
            with open(trash_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            if "Items" in data:
                data["Items"] = []

            with open(trash_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)

            print(f"Cleared trash in: {trash_file}")

        except (json.JSONDecodeError, IOError) as e:
            print(f"Error modifying Trash.json: {e}")

    # Clear each generator log
    if os.path.exists(generators_folder):
        for generator_file in glob.glob(os.path.join(generators_folder, "Generator_*.json")):
            try:
                with open(generator_file, "r", encoding="utf-8") as f:
                    gen_data = json.load(f)

                if "GeneratedItems" in gen_data:
                    gen_data["GeneratedItems"] = []

                with open(generator_file, "w", encoding="utf-8") as f:
                    json.dump(gen_data, f, indent=4)

                print(f"Cleared generated items in: {generator_file}")

            except (json.JSONDecodeError, IOError) as e:
                print(f"Error modifying {generator_file}: {e}")

    print("All trash and generated items cleared successfully!")

def main():
    print("Schedule I Mod Menu - Created by XOWithSauce\n")
    
    while True:
        print("____________________________________________")
        print("1 - Clear trash from a Saved Game")
        print("2 - Disable trash generation")
        print("3 - Enable trash generation")
        print("5 - Exit the Mod Menu")
        opt = input("Type your option number: ")
        print("____________________________________________\n")
        
        if not opt.isnumeric() or len(opt) > 1:
            print("Invalid input. Type your option number and press enter.")
            
        match opt:
            case "1":
                clear_trash_task()
                continue
            
            case "2":
                permanent_trash_gen(True)
                continue
            
            case "3":
                permanent_trash_gen(False)
                continue
            
            case "5":
                print("\n"*20 + "Exiting in 5 seconds...")
                print("Thank you for using the program.")
                time.sleep(5)
                exit()
        

if __name__ == "__main__":
    main()
