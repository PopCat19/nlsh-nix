# config.py
#
# Purpose: Configuration loading, saving, and management
#
# This module:
# - Defines Config dataclass with load/save
# - Provides setup wizard and interactive config menu

import os
from dataclasses import dataclass

CONFIG_DIR = os.path.expanduser("~/.config/nlsh")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config")


@dataclass
class Config:
    base_url: str = ""
    model: str = ""
    api_key: str = ""

    @classmethod
    def load(cls):
        config = cls(
            base_url=os.environ.get("NLSH_BASE_URL", ""),
            model=os.environ.get("NLSH_MODEL", ""),
            api_key=os.environ.get("NLSH_API_KEY", ""),
        )
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        if key == "NLSH_BASE_URL":
                            config.base_url = config.base_url or value
                        elif key == "NLSH_MODEL":
                            config.model = config.model or value
                        elif key == "NLSH_API_KEY":
                            config.api_key = config.api_key or value
        return config

    def save(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            f.write("# nlsh configuration\n")
            f.write(f"NLSH_API_KEY={self.api_key}\n")
            f.write(f"NLSH_BASE_URL={self.base_url}\n")
            f.write(f"NLSH_MODEL={self.model}\n")

    @property
    def is_configured(self):
        return bool(self.base_url and self.model)

    def apply_to_env(self):
        if self.base_url:
            os.environ["NLSH_BASE_URL"] = self.base_url
        if self.model:
            os.environ["NLSH_MODEL"] = self.model
        if self.api_key:
            os.environ["NLSH_API_KEY"] = self.api_key
        else:
            os.environ.pop("NLSH_API_KEY", None)


def setup_wizard(config):
    print(f"\n\033[36mOpenAI-compatible API setup\033[0m\n")

    while not config.base_url:
        base_url = input("\033[33mBase URL: \033[0m").strip()
        if base_url:
            config.base_url = base_url
        else:
            print("Base URL required.")

    while not config.model:
        model = input("\033[33mModel: \033[0m").strip()
        if model:
            config.model = model
        else:
            print("Model required.")

    api_key = input("\033[33mAPI key (enter to skip): \033[0m").strip()
    if api_key:
        config.api_key = api_key

    config.save()
    print("\033[32m✓ Config saved!\033[0m\n")


def config_menu(config):
    original = Config(
        base_url=config.base_url,
        model=config.model,
        api_key=config.api_key,
    )

    while True:
        print("\033[36m!api menu\033[0m")
        print(f"  \033[33m1\033[0m Base URL: {config.base_url or '(not set)'}")
        print(f"  \033[33m2\033[0m Model: {config.model or '(not set)'}")
        api_key = config.api_key
        masked = (
            api_key[:8] + "..." + api_key[-4:]
            if len(api_key) > 12
            else api_key or "(not set)"
        )
        print(f"  \033[33m3\033[0m API key: {masked}")
        print("  \033[33ms\033[0m Save & exit")
        print("  \033[33mc\033[0m Cancel")
        print()

        choice = input("\033[33mSelect: \033[0m").strip().lower()

        if choice == "1":
            current = config.base_url
            val = input(f"\033[33mBase URL [{current}]: \033[0m").strip()
            if val:
                config.base_url = val
                print("\033[36m(staged)\033[0m")
        elif choice == "2":
            current = config.model
            val = input(f"\033[33mModel [{current}]: \033[0m").strip()
            if val:
                config.model = val
                print("\033[36m(staged)\033[0m")
        elif choice == "3":
            val = input("\033[33mAPI key: \033[0m").strip()
            if val:
                config.api_key = val
                print("\033[36m(staged)\033[0m")
            elif input("\033[33mClear API key? [y/N] \033[0m").strip().lower() == "y":
                config.api_key = ""
                print("\033[36m(staged - cleared)\033[0m")
        elif choice == "s":
            config.save()
            print("\033[32m✓ Saved\033[0m\n")
            break
        elif choice == "c":
            config.base_url = original.base_url
            config.model = original.model
            config.api_key = original.api_key
            print("\033[31m✗ Cancelled\033[0m\n")
            break
        else:
            print("\033[31mInvalid option\033[0m")
