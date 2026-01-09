#!/usr/bin/env python3
"""
Unified Console Interface for LLM Documentation Processing
Provides folder input/output selection and debugging for rate limiter failures.
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Colors:
    """ANSI color codes for console output"""

    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


class ConsoleInterface:
    def __init__(self):
        self.input_folder = ""
        self.output_folder = ""
        self.script_dir = Path(__file__).parent / "scripts"

    def print_header(self):
        """Display the application header"""
        print(f"\n{Colors.HEADER}{Colors.BOLD}=" * 60)
        print("    LLM DOCUMENTATION PROCESSING CONSOLE")
        print("=" * 60 + Colors.ENDC)
        print(
            f"{Colors.OKCYAN}Build knowledge bases and chat with your documents{Colors.ENDC}"
        )
        print()

    def check_dependencies(self):
        """Check if required dependencies are installed"""
        print(f"{Colors.OKBLUE}Checking dependencies...{Colors.ENDC}")

        required_packages = [
            "voyageai",
            "lancedb",
            "pypdf",
            "dotenv",
            "sentence-transformers",
            "anthropic",
        ]
        missing_packages = []

        for package in required_packages:
            try:
                __import__(package.replace("-", "_"))
                print(f"  ✓ {package}")
            except ImportError:
                missing_packages.append(package)
                print(f"  {Colors.WARNING}✗ {package} (missing){Colors.ENDC}")

        if missing_packages:
            print(f"\n{Colors.WARNING}Missing packages detected!{Colors.ENDC}")
            print("Install with: pip install " + " ".join(missing_packages))
            return False

        print(f"{Colors.OKGREEN}All dependencies satisfied!{Colors.ENDC}")
        return True

    def check_env_vars(self):
        """Check if required environment variables are set"""
        print(f"\n{Colors.OKBLUE}Checking environment variables...{Colors.ENDC}")

        required_vars = ["VOYAGE_API_KEY", "ANTHROPIC_API_KEY"]
        missing_vars = []

        for var in required_vars:
            if os.getenv(var):
                print(f"  ✓ {var}")
            else:
                missing_vars.append(var)
                print(f"  {Colors.WARNING}✗ {var} (not set){Colors.ENDC}")

        if missing_vars:
            print(f"\n{Colors.WARNING}Missing environment variables!{Colors.ENDC}")
            print("Create a .env file with:")
            for var in missing_vars:
                print(f"  {var}=your_api_key_here")
            return False

        print(f"{Colors.OKGREEN}Environment variables configured!{Colors.ENDC}")
        return True

    def get_folder_input(self, prompt_text, default_path=""):
        """Get folder path from user with validation"""
        while True:
            if default_path:
                user_input = input(f"{prompt_text} [{default_path}]: ").strip()
                folder_path = user_input if user_input else default_path
            else:
                folder_path = input(f"{prompt_text}: ").strip()

            if not folder_path:
                print(f"{Colors.WARNING}Please enter a folder path.{Colors.ENDC}")
                continue

            # Expand user path and resolve
            folder_path = Path(folder_path).expanduser().resolve()

            if folder_path.exists():
                return str(folder_path)
            else:
                print(f"{Colors.WARNING}Folder not found: {folder_path}{Colors.ENDC}")
                create = input("Create this folder? (y/n): ").strip().lower()
                if create in ["y", "yes"]:
                    try:
                        folder_path.mkdir(parents=True, exist_ok=True)
                        print(f"{Colors.OKGREEN}Created: {folder_path}{Colors.ENDC}")
                        return str(folder_path)
                    except Exception as e:
                        print(f"{Colors.FAIL}Failed to create folder: {e}{Colors.ENDC}")

    def configure_folders(self):
        """Configure input and output folders"""
        print(f"\n{Colors.HEADER}FOLDER CONFIGURATION{Colors.ENDC}")

        # Default paths from build_knowledge_v4.py
        default_input = "E:\\My Drive\\sean@group9\\5_LAW - REFERENCE\\LAW-RCW"
        default_output = "G:\\Code\\llm-docs\\docs-ai"

        self.input_folder = self.get_folder_input(
            f"{Colors.OKCYAN}Input folder (containing .pdf/.md files){Colors.ENDC}",
            default_input,
        )

        self.output_folder = self.get_folder_input(
            f"{Colors.OKCYAN}Output folder (for knowledge database){Colors.ENDC}",
            default_output,
        )

        print(f"\n{Colors.OKGREEN}Configuration saved:{Colors.ENDC}")
        print(f"  Input:  {self.input_folder}")
        print(f"  Output: {self.output_folder}")

    def run_build_knowledge(self):
        """Run the knowledge base builder with rate limiter debugging"""
        print(f"\n{Colors.HEADER}BUILDING KNOWLEDGE BASE{Colors.ENDC}")

        if not self.input_folder or not self.output_folder:
            print(f"{Colors.WARNING}Please configure folders first.{Colors.ENDC}")
            return

        print(f"{Colors.OKBLUE}Starting knowledge base build...{Colors.ENDC}")
        print(f"Input:  {self.input_folder}")
        print(f"Output: {self.output_folder}")
        print()

        # Run the improved build_knowledge_v4.py script
        build_script = self.script_dir / "build_knowledge_v4.py"

        if not build_script.exists():
            print(f"{Colors.FAIL}Build script not found: {build_script}{Colors.ENDC}")
            return

        cmd = [
            sys.executable,
            str(build_script),
            "--input",
            self.input_folder,
            "--output",
            self.output_folder,
        ]

        print(f"{Colors.OKCYAN}Running: {' '.join(cmd)}{Colors.ENDC}")
        print(f"{Colors.OKCYAN}Rate limiter debugging enabled...{Colors.ENDC}")
        print()

        try:
            # Run with real-time output
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
            )

            # Stream output in real-time
            for line in process.stdout:
                print(line, end="")

            process.wait()

            if process.returncode == 0:
                print(
                    f"\n{Colors.OKGREEN}Knowledge base build completed successfully!{Colors.ENDC}"
                )
            else:
                print(
                    f"\n{Colors.WARNING}Build completed with warnings (return code: {process.returncode}){Colors.ENDC}"
                )

        except Exception as e:
            print(f"{Colors.FAIL}Error running build script: {e}{Colors.ENDC}")

    def run_chat_interface(self):
        """Run the chat interface"""
        print(f"\n{Colors.HEADER}CHAT WITH DOCUMENTS{Colors.ENDC}")

        if not self.output_folder:
            print(f"{Colors.WARNING}Please configure output folder first.{Colors.ENDC}")
            return

        # Check if knowledge base exists
        db_path = Path(self.output_folder) / "my_knowledge_db"
        if not db_path.exists():
            print(f"{Colors.WARNING}No knowledge base found at: {db_path}{Colors.ENDC}")
            print("Please build the knowledge base first.")
            return

        chat_script = self.script_dir / "chat.py"

        if not chat_script.exists():
            print(f"{Colors.FAIL}Chat script not found: {chat_script}{Colors.ENDC}")
            return

        print(f"{Colors.OKBLUE}Starting chat interface...{Colors.ENDC}")
        print(f"Database: {db_path}")
        print()

        try:
            # Change to the correct directory so relative paths work
            original_cwd = os.getcwd()
            os.chdir(Path(__file__).parent)

            # Run the chat script
            subprocess.run([sys.executable, str(chat_script)], check=False)

        except Exception as e:
            print(f"{Colors.FAIL}Error running chat interface: {e}{Colors.ENDC}")
        finally:
            os.chdir(original_cwd)

    def debug_rate_limiter(self):
        """Display rate limiter debugging information"""
        print(f"\n{Colors.HEADER}RATE LIMITER DEBUG INFO{Colors.ENDC}")

        print(f"{Colors.OKBLUE}Rate Limiting Configuration:{Colors.ENDC}")
        print("  • Batch Size: 8 items per batch")
        print("  • RPM Delay: 1 second between batches")
        print("  • Max Retries: 5 attempts per batch")
        print("  • Backoff Strategy: Exponential (30s → 60s → 120s → 240s → 300s)")
        print("  • Error Detection: rate limit, 429, 500, 502, 503, timeout")

        print(f"\n{Colors.OKBLUE}Recent Improvements:{Colors.ENDC}")
        print("  ✓ Fixed typo: 'timout' → 'timeout'")
        print("  ✓ Added retry limit to prevent infinite loops")
        print("  ✓ Enhanced error messages with attempt counter")
        print("  ✓ Graceful batch failure handling")

        print(f"\n{Colors.OKBLUE}Troubleshooting Tips:{Colors.ENDC}")
        print("  • If you hit rate limits, the system will automatically retry")
        print("  • Progress is saved after each batch - safe to restart")
        print("  • Reduce BATCH_SIZE in build_knowledge_v4.py if needed")
        print("  • Check your API quotas at voyage.ai dashboard")

        print(f"\n{Colors.WARNING}Common Issues:{Colors.ENDC}")
        print("  • Monthly quota exceeded: Wait for quota reset")
        print("  • Network timeouts: Check internet connection")
        print("  • Invalid API key: Verify VOYAGE_API_KEY in .env file")

    def show_main_menu(self):
        """Display and handle the main menu"""
        while True:
            print(f"\n{Colors.HEADER}MAIN MENU{Colors.ENDC}")
            print("1. Configure Input/Output Folders")
            print("2. Build Knowledge Base")
            print("3. Chat with Documents")
            print("4. Rate Limiter Debug Info")
            print("5. Check System Requirements")
            print("6. Exit")

            choice = input(
                f"\n{Colors.OKCYAN}Select option (1-6): {Colors.ENDC}"
            ).strip()

            if choice == "1":
                self.configure_folders()
            elif choice == "2":
                self.run_build_knowledge()
            elif choice == "3":
                self.run_chat_interface()
            elif choice == "4":
                self.debug_rate_limiter()
            elif choice == "5":
                self.check_dependencies()
                self.check_env_vars()
            elif choice == "6":
                print(f"{Colors.OKGREEN}Goodbye!{Colors.ENDC}")
                break
            else:
                print(
                    f"{Colors.WARNING}Invalid option. Please choose 1-6.{Colors.ENDC}"
                )

    def run(self):
        """Main application entry point"""
        try:
            self.print_header()

            # Quick system check
            deps_ok = self.check_dependencies()
            env_ok = self.check_env_vars()

            if not deps_ok or not env_ok:
                print(
                    f"\n{Colors.WARNING}System requirements not met. Please fix the issues above.{Colors.ENDC}"
                )
                input("Press Enter to continue anyway...")

            self.show_main_menu()

        except KeyboardInterrupt:
            print(f"\n\n{Colors.OKGREEN}Interrupted by user. Goodbye!{Colors.ENDC}")
        except Exception as e:
            print(f"\n{Colors.FAIL}Unexpected error: {e}{Colors.ENDC}")
            raise


if __name__ == "__main__":
    interface = ConsoleInterface()
    interface.run()
