#!/usr/bin/env python3

import os
import sys
import json
import shutil
import logging
import webbrowser
from pathlib import Path
import webview

class WebToApp:
    def __init__(self):
        # Initialize base directories
        self.config_dir = Path.home() / '.config' / 'webtoapp'
        self.apps_dir = Path.home() / '.local' / 'share' / 'applications'
        self.storage_dir = Path.home() / '.local' / 'share' / 'webtoapp' / 'storage'
        self.launchers_dir = self.config_dir / 'launchers'
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger('WebToApp')
        
        # Initialize directories
        self.init_directories()

    def init_directories(self):
        """Create necessary directories if they don't exist"""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            self.apps_dir.mkdir(parents=True, exist_ok=True)
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            self.launchers_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.logger.error(f"Failed to create directories: {e}")
            sys.exit(1)

    def show_menu(self):
        """Display the main menu"""
        while True:
            print("\n///////WebToApp////////")
            print("1. Create new web app")
            print("2. List existing apps")
            print("3. Delete an app")
            print("4. Exit")
            
            try:
                choice = input("\nSelect an option (1-4): ").strip()
                
                if choice == "1":
                    self.create_app()
                elif choice == "2":
                    self.list_apps()
                elif choice == "3":
                    self.delete_app()
                elif choice == "4":
                    print("Goodbye!")
                    sys.exit(0)
                else:
                    print("Invalid option, please try again.")
            except KeyboardInterrupt:
                print("\nGoodbye!")
                sys.exit(0)
            except Exception as e:
                self.logger.error(f"Menu error: {e}")

    def create_app(self):
        """Create a new web application"""
        try:
            print("\n///////WebToApp////////")
            print("Hello! Let's create a new app for ya!")
            
            # Get application details
            app_name = input("Please give a name: ").strip()
            url = input("Please give the URL: ").strip()
            icon_path = input("Please write the icon path for the app: ").strip()

            if not app_name or not url:
                print("Error: Name and URL are required!")
                return False

            # Ensure URL has protocol
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url

            # Validate icon path if provided
            if icon_path:
                icon_path = str(Path(icon_path).resolve())
                if not Path(icon_path).exists():
                    print("Warning: Icon file not found. The app will use default icon.")

            # Ask for app type
            while True:
                app_type = input("\nYou want this shortcut to be a OIB(Open in browser) or a Webview? (oib/webview): ").strip().lower()
                if app_type in ['oib', 'webview']:
                    break
                print("Please enter either 'oib' or 'webview'")

            # Create app-specific storage directory
            app_storage_dir = self.storage_dir / app_name.lower().replace(" ", "_")
            app_storage_dir.mkdir(exist_ok=True)

            # Create launcher and desktop entry
            if app_type == 'webview':
                launcher_script = self.create_launcher_script(app_name, url, app_storage_dir)
            else:
                launcher_script = self.create_browser_launcher_script(app_name, url)
            
            desktop_entry = self.create_desktop_entry(app_name, launcher_script, icon_path)
            
            print("Creating your app..")
            
            # Save configuration
            self.save_config(app_name, {
                'name': app_name,
                'url': url,
                'icon': icon_path,
                'type': app_type,
                'launcher': str(launcher_script),
                'desktop': str(desktop_entry),
                'storage_dir': str(app_storage_dir)
            })
            
            print("it's done!")
            print("-----------+----------------")
            return True

        except Exception as e:
            self.logger.error(f"Error creating app: {e}")
            return False

    def create_browser_launcher_script(self, app_name: str, url: str) -> Path:
        """Create the Python launcher script for browser-based app"""
        try:
            script_path = self.launchers_dir / f'{app_name.lower().replace(" ", "_")}_launcher.py'
            
            script_content = f'''#!/usr/bin/env python3
import webbrowser

def main():
    webbrowser.open("{url}")

if __name__ == '__main__':
    main()
'''
            
            with open(script_path, 'w') as f:
                f.write(script_content)
            
            script_path.chmod(0o755)
            return script_path

        except Exception as e:
            self.logger.error(f"Error creating browser launcher script: {e}")
            raise

    def create_launcher_script(self, app_name: str, url: str, storage_dir: Path) -> Path:
        """Create the Python launcher script for the web app"""
        try:
            script_path = self.launchers_dir / f'{app_name.lower().replace(" ", "_")}_launcher.py'
            
            script_content = f'''#!/usr/bin/env python3
import webview
import logging
import sqlite3
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename="{storage_dir}/webview.log",
    filemode='a'
)
logger = logging.getLogger(__name__)

class Storage:
    def __init__(self):
        self.db_path = Path("{storage_dir}/app_data.db")
        self.init_db()

    def init_db(self):
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL,
                    value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def save_data(self, key, value):
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO user_data (key, value) VALUES (?, ?)",
                (key, value)
            )
            conn.commit()

    def get_data(self, key):
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT value FROM user_data WHERE key = ? ORDER BY id DESC LIMIT 1",
                (key,)
            )
            result = cursor.fetchone()
            return result[0] if result else None

    def delete_data(self, key):
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_data WHERE key = ?", (key,))
            conn.commit()

    def list_all_data(self):
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value, created_at FROM user_data ORDER BY created_at DESC")
            return cursor.fetchall()

class Api:
    def __init__(self):
        self.storage = Storage()

    def save_data(self, key, value):
        try:
            self.storage.save_data(key, value)
            return {{"success": True}}
        except Exception as e:
            logger.error(f"Error saving data: {{e}}")
            return {{"success": False, "error": str(e)}}

    def get_data(self, key):
        try:
            value = self.storage.get_data(key)
            return {{"success": True, "value": value}}
        except Exception as e:
            logger.error(f"Error getting data: {{e}}")
            return {{"success": False, "error": str(e)}}

    def delete_data(self, key):
        try:
            self.storage.delete_data(key)
            return {{"success": True}}
        except Exception as e:
            logger.error(f"Error deleting data: {{e}}")
            return {{"success": False, "error": str(e)}}

    def list_all_data(self):
        try:
            data = self.storage.list_all_data()
            return {{"success": True, "data": data}}
        except Exception as e:
            logger.error(f"Error listing data: {{e}}")
            return {{"success": False, "error": str(e)}}

def main():
    try:
        api = Api()
        
        webview.settings.update({{
            'allow_file_access_from_file_urls': True,
            'allow_universal_access_from_file_urls': True,
            'enable_download_notifications': True
        }})

        window = webview.create_window(
            "{app_name}",
            "{url}",
            width=1024,
            height=768,
            resizable=True,
            fullscreen=False,
            min_size=(400, 300),
            text_select=True,
            confirm_close=True,
            background_color='#FFFFFF',
            js_api=api
        )

        webview.start(debug=True)
    except Exception as e:
        logger.error(f"Error starting application: {{e}}")
        raise

if __name__ == '__main__':
    main()
'''
            
            with open(script_path, 'w') as f:
                f.write(script_content)
            
            script_path.chmod(0o755)
            return script_path

        except Exception as e:
            self.logger.error(f"Error creating launcher script: {e}")
            raise

    def create_desktop_entry(self, app_name: str, launcher_script: Path, icon_path: str) -> Path:
        """Create .desktop entry for the application"""
        try:
            desktop_file = self.apps_dir / f'{app_name.lower().replace(" ", "-")}.desktop'
            
            python_path = sys.executable
            launcher_path = launcher_script.absolute()
            icon_path = Path(icon_path).absolute() if icon_path else ""
            
            entry_content = f'''[Desktop Entry]
Version=1.0
Name={app_name}
Exec="{python_path}" "{launcher_path}"
Icon={icon_path}
Type=Application
Categories=Network;WebApp;
Comment=Web application for {app_name}
Terminal=false
StartupNotify=true
'''
            
            with open(desktop_file, 'w') as f:
                f.write(entry_content)
            
            desktop_file.chmod(0o755)
            
            os.system('update-desktop-database ~/.local/share/applications')
            
            return desktop_file

        except Exception as e:
            self.logger.error(f"Error creating desktop entry: {e}")
            raise

    def list_apps(self):
        """List all created web applications"""
        try:
            config_file = self.config_dir / 'apps.json'
            if not config_file.exists():
                print("\nNo apps created yet!")
                return

            with open(config_file, 'r') as f:
                apps = json.load(f)

            if not apps:
                print("\nNo apps created yet!")
                return

            print("\nExisting Web Apps:")
            print("-" * 40)
            for name, details in apps.items():
                print(f"Name: {name}")
                print(f"URL: {details['url']}")
                print(f"Type: {details.get('type', 'webview')}")
                print(f"Icon: {details['icon']}")
                print("-" * 40)

        except Exception as e:
            self.logger.error(f"Error listing apps: {e}")

    def delete_app(self):
        """Delete an existing web application"""
        try:
            config_file = self.config_dir / 'apps.json'
            if not config_file.exists():
                print("\nNo apps to delete!")
                return

            with open(config_file, 'r') as f:
                apps = json.load(f)

            if not apps:
                print("\nNo apps to delete!")
                return

            print("\nSelect an app to delete:")
            app_names = list(apps.keys())
            for i, name in enumerate(app_names, 1):
                print(f"{i}. {name}")

            choice = input("\nEnter the number of the app to delete (0 to cancel): ")
            
            try:
                choice = int(choice)
            except ValueError:
                print("Invalid input! Please enter a number.")
                return

            if choice == 0:
                return
            if choice < 1 or choice > len(app_names):
                print("Invalid selection!")
                return

            app_name = app_names[choice - 1]
            app_config = apps[app_name]

            # Remove launcher script
            launcher_path = Path(app_config['launcher'])
            if launcher_path.exists():
                launcher_path.unlink()

            # Remove desktop entry
            desktop_path = Path(app_config['desktop'])
            if desktop_path.exists():
                desktop_path.unlink()

            # Remove storage directory if it exists
            storage_path = Path(app_config['storage_dir'])
            if storage_path.exists():
                shutil.rmtree(storage_path)

            # Remove from config
            del apps[app_name]
            with open(config_file, 'w') as f:
                json.dump(apps, f, indent=4)

            # Update desktop database
            os.system('update-desktop-database ~/.local/share/applications')

            print(f"\nSuccessfully deleted {app_name}!")

        except Exception as e:
            self.logger.error(f"Error deleting app: {e}")

    def save_config(self, app_name: str, config: dict):
        """Save app configuration to config directory"""
        try:
            config_file = self.config_dir / 'apps.json'
            
            existing_config = {}
            if config_file.exists():
                with open(config_file, 'r') as f:
                    existing_config = json.load(f)
            
            existing_config[app_name] = config
            
            with open(config_file, 'w') as f:
                json.dump(existing_config, f, indent=4)

        except Exception as e:
            self.logger.error(f"Error saving config: {e}")
            raise

def main():
    try:
        import webview
    except ImportError:
        print("Error: pywebview is not installed. Please install it using:")
        print("pip install pywebview --user")
        sys.exit(1)

    try:
        app = WebToApp()
        app.show_menu()
    except KeyboardInterrupt:
        print("\nGoodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
