# config.py
#
# Purpose: Configuration loading, saving, and management
#
# This module:
# - Loads and saves config from ~/.config/nlsh/config
# - Provides setup wizard and interactive config menu

import os

CONFIG_DIR = os.path.expanduser("~/.config/nlsh")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config")
REQUIRED_KEYS = ["NLSH_BASE_URL", "NLSH_MODEL"]

_loaded_from_config = set()

def load_config():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    if key not in os.environ:
                        os.environ[key] = value
                        _loaded_from_config.add(key)

def save_config():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        f.write("# nlsh configuration\n")
        f.write(f"NLSH_API_KEY={os.environ.get('NLSH_API_KEY', '')}\n")
        for key in REQUIRED_KEYS:
            f.write(f"{key}={os.environ.get(key, '')}\n")

def is_configured():
    return all(os.environ.get(k) for k in REQUIRED_KEYS)

def is_loaded_from_config(key: str) -> bool:
    return key in _loaded_from_config

def setup_api_key():
    print(f"\n\033[36mOpenAI-compatible API setup\033[0m\n")

    while not os.environ.get("NLSH_BASE_URL"):
        base_url = input("\033[33mBase URL: \033[0m").strip()
        if base_url:
            os.environ["NLSH_BASE_URL"] = base_url
        else:
            print("Base URL required.")

    while not os.environ.get("NLSH_MODEL"):
        model = input("\033[33mModel: \033[0m").strip()
        if model:
            os.environ["NLSH_MODEL"] = model
        else:
            print("Model required.")

    api_key = input("\033[33mAPI key (enter to skip): \033[0m").strip()
    if api_key:
        os.environ["NLSH_API_KEY"] = api_key

    save_config()
    print("\033[32m✓ Config saved!\033[0m\n")

def config_menu():
    original = {
        'NLSH_BASE_URL': os.environ.get('NLSH_BASE_URL', ''),
        'NLSH_MODEL': os.environ.get('NLSH_MODEL', ''),
        'NLSH_API_KEY': os.environ.get('NLSH_API_KEY', ''),
    }
    
    while True:
        print("\033[36m!api menu\033[0m")
        print(f"  \033[33m1\033[0m Base URL: {os.environ.get('NLSH_BASE_URL', '(not set)')}")
        print(f"  \033[33m2\033[0m Model: {os.environ.get('NLSH_MODEL', '(not set)')}")
        api_key = os.environ.get('NLSH_API_KEY', '')
        masked = api_key[:8] + '...' + api_key[-4:] if len(api_key) > 12 else api_key or '(not set)'
        print(f"  \033[33m3\033[0m API key: {masked}")
        print("  \033[33ms\033[0m Save & exit")
        print("  \033[33mc\033[0m Cancel")
        print()
        
        choice = input("\033[33mSelect: \033[0m").strip().lower()
        
        if choice == "1":
            current = os.environ.get('NLSH_BASE_URL', '')
            val = input(f"\033[33mBase URL [{current}]: \033[0m").strip()
            if val:
                os.environ['NLSH_BASE_URL'] = val
                print("\033[36m(staged)\033[0m")
        elif choice == "2":
            current = os.environ.get('NLSH_MODEL', '')
            val = input(f"\033[33mModel [{current}]: \033[0m").strip()
            if val:
                os.environ['NLSH_MODEL'] = val
                print("\033[36m(staged)\033[0m")
        elif choice == "3":
            val = input("\033[33mAPI key: \033[0m").strip()
            if val:
                os.environ['NLSH_API_KEY'] = val
                print("\033[36m(staged)\033[0m")
            elif input("\033[33mClear API key? [y/N] \033[0m").strip().lower() == "y":
                os.environ['NLSH_API_KEY'] = ''
                print("\033[36m(staged - cleared)\033[0m")
        elif choice == "s":
            save_config()
            print("\033[32m✓ Saved\033[0m\n")
            break
        elif choice == "c":
            for key, val in original.items():
                if val:
                    os.environ[key] = val
                else:
                    os.environ.pop(key, None)
            print("\033[33m✗ Cancelled\033[0m\n")
            break
        else:
            print("\033[31mInvalid option\033[0m")