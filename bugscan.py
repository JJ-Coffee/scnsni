import ssl
import socket
import threading
from queue import Queue
import sys
import os
import glob


# Colors
cyan = "\033[0;36m"
yellow = "\033[1;33m"
green = "\033[0;32m"
red = "\033[0;31m"
reset = "\033[0m"

def show_banner():
    clear_screen()
    print(f"""{cyan}
          ╔══╗──────────────────────────╔╗
          ║╔╗║──────────────────────────║║
          ║╚╝╚╦╗╔╦══╗╔══╦══╦══╦═╗─╔══╦══╣║
          ║╔═╗║║║║╔╗║║══╣╔═╣╔╗║╔╗╗║══╣══╣║
          ║╚═╝║╚╝║╚╝║╠══║╚═╣╔╗║║║║╠══╠══║╚╗
          ╚═══╩══╩═╗║╚══╩══╩╝╚╩╝╚╝╚══╩══╩═╝
                 ╔═╝║
                 ╚══╝
{yellow}───────────────────────────────────────────────────
{green}Telgram Group: https://t.me/marketgroox\n{reset}
""")

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def check_tls_only(server_addr, port, bug_host, timeout=10):
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    try:
        server_ip = socket.gethostbyname(server_addr)
        with socket.create_connection((server_ip, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=bug_host) as ssock:
                return True
    except Exception:
        return False

def print_progress(done, total_bugs):
    percent = (done / total_bugs) * 100
    bar_length = 30
    filled_length = int(bar_length * done // total_bugs)
    bar = '#' * filled_length + '-' * (bar_length - filled_length)
    sys.stdout.write(f"\r{cyan}[{bar}] {percent:.2f}% ({done}/{total_bugs}){reset}")
    sys.stdout.flush()

def worker(server_addr, port, queue, valid_bugs, total_bugs, lock, progress):
    while not queue.empty():
        bug_host = queue.get()
        is_valid = check_tls_only(server_addr, port, bug_host)
        
        with lock:
            progress[0] += 1
            done = progress[0]

            if is_valid:
                valid_bugs.put(bug_host)

                sys.stdout.write('\r')
                sys.stdout.write(' ' * 80)
                sys.stdout.write('\r')

                print(f"{green}[VALID] {bug_host}{reset}")

            print_progress(done, total_bugs)

        queue.task_done()

def select_bugs_file():
    show_banner()
    print(f"{yellow}Select a bug file from the following options:{reset}")
    files = glob.glob('*.txt')  # This will list all .txt files in the current directory
    if not files:
        print(f"{red}No .txt files found in the directory.{reset}")
        sys.exit(1)

    for idx, file in enumerate(files, start=1):
        print(f"{cyan}{idx}. {file}{reset}")

    while True:
        try:
            choice = int(input(f"{yellow}Enter the number of the file you want to select: {reset}"))
            if 1 <= choice <= len(files):
                return files[choice - 1]
            else:
                print(f"{red}Invalid choice. Please try again.{reset}")
        except ValueError:
            print(f"{red}Please enter a valid number.{reset}")

def scan_bugs_tls_only(server_addr, port):
    show_banner()
    
    # Select a bug file interactively
    bugs_file = select_bugs_file()

    try:
        with open(bugs_file, 'r') as f:
            bugs = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"[ERROR] Cannot open {bugs_file}: {e}")
        return

    # Ask user input for thread count
    try:
        user_input = input(f"{yellow}Enter thread count (recommended: 100): {reset}")
        if user_input.strip():
            thread_count = int(user_input)
            print(f"{cyan}Using {thread_count} threads.{reset}")
        else:
            thread_count = 100
            print(f"{cyan}Using default 100 threads.{reset}")
    except ValueError:
        thread_count = 100
        print(f"{cyan}Invalid input. Using default 100 threads.{reset}")

    queue = Queue()
    valid_bugs = Queue()
    lock = threading.Lock()
    progress = [0]
    total_bugs = len(bugs)

    for bug in bugs:
        queue.put(bug)

    print(f"\n{yellow}[INFO] Starting TLS-only scan for {total_bugs} bugs with {thread_count} threads...{reset}\n")

    threads = []
    for _ in range(thread_count):
        t = threading.Thread(target=worker, args=(server_addr, port, queue, valid_bugs, total_bugs, lock, progress))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    # CLEAR SCREEN AFTER SCAN
    clear_screen()

    valid_list = list(valid_bugs.queue)

    if valid_list:
        with open('valid_bugs.txt', 'w') as f:
            for bug in valid_list:
                f.write(bug + '\n')
        show_banner()
        print(f"{green}[INFO] {len(valid_list)} valid bugs saved to valid_bugs.txt{reset}")
    else:
        show_banner()
        print(f"{red}[INFO] No valid bugs found.{reset}")

if __name__ == "__main__":
    # Example usage
    server_addr = 'sg-sshws.bypass.id'
    port = 443
    scan_bugs_tls_only(server_addr, port)
