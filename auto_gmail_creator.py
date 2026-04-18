#!/usr/bin/env python3
"""
Gmail Creator Pro v2.0.0
Advanced automated Gmail account creation tool with anti-detection,
phone verification bypass, 5sim integration, and beautiful modern interface.

Educational purposes only. Use responsibly.
"""

import json
import os
import random
import secrets
import string
import sys
import time
from datetime import datetime

import requests
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from rich.text import Text
from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait
from unidecode import unidecode
from webdriver_manager.chrome import ChromeDriverManager

# ── Globals ──────────────────────────────────────────────────────────────────
console = Console()

ACCOUNTS_FILE = "data/accounts.json"
BANNER = r"""
   ██████╗ ███╗   ███╗ █████╗ ██╗██╗
  ██╔════╝ ████╗ ████║██╔══██╗██║██║
  ██║  ███╗██╔████╔██║███████║██║██║
  ██║   ██║██║╚██╔╝██║██╔══██║██║██║
  ╚██████╔╝██║ ╚═╝ ██║██║  ██║██║███████╗
   ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝╚══════╝
       Creator Pro  v2.0.0
"""

# ── Configuration helpers ────────────────────────────────────────────────────

def load_config():
    """Load configuration from config/config.py."""
    config = {
        "YOUR_BIRTHDAY": "2 4 1950",
        "YOUR_GENDER": "1",
        "YOUR_PASSWORD": "",
        "FIVESIM_API_KEY": "",
        "FIVESIM_COUNTRY": "usa",
        "FIVESIM_OPERATOR": "any",
        "USE_ARABIC_NAMES": True,
        "NAMES_FILE": "data/names.txt",
        "USER_AGENTS_FILE": "config/user_agents.txt",
    }
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "config.py")
    if os.path.exists(config_path):
        import ast
        with open(config_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Skip comments and blank lines
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    # Strip inline comments
                    value = value.split("#")[0].strip()
                    if key in config:
                        try:
                            config[key] = ast.literal_eval(value)
                        except (ValueError, SyntaxError):
                            config[key] = value.strip('"').strip("'")
    return config


def load_password(config):
    """Return password from config or password.txt."""
    if config["YOUR_PASSWORD"]:
        return config["YOUR_PASSWORD"]
    pw_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "password.txt")
    if os.path.exists(pw_path):
        with open(pw_path, "r", encoding="utf-8") as f:
            password = f.read().strip()
            if password:
                return password
    console.print("[red]Error: No password configured! Set it in config.py or config/password.txt[/red]")
    return None


def load_api_key(config):
    """Return 5sim API key from config or 5sim_config.txt."""
    if config["FIVESIM_API_KEY"]:
        return config["FIVESIM_API_KEY"]
    api_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "5sim_config.txt")
    if os.path.exists(api_path):
        with open(api_path, "r", encoding="utf-8") as f:
            key = f.read().strip()
            if key and key != "YOUR_5SIM_API_KEY_HERE":
                return key
    return ""


def load_names(config):
    """Load names from names file."""
    base = os.path.dirname(os.path.abspath(__file__))
    names_path = os.path.join(base, config["NAMES_FILE"])
    names = []
    if os.path.exists(names_path):
        with open(names_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    names.append(line)
    if not names:
        console.print("[red]Error: names.txt is empty or not found![/red]")
        return []
    return names


def load_user_agents(config):
    """Load user agents list."""
    base = os.path.dirname(os.path.abspath(__file__))
    ua_path = os.path.join(base, config["USER_AGENTS_FILE"])
    agents = []
    if os.path.exists(ua_path):
        with open(ua_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    agents.append(line)
    if not agents:
        agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        ]
    return agents


# ── Account storage ──────────────────────────────────────────────────────────

def load_accounts():
    """Load saved accounts from JSON file."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ACCOUNTS_FILE)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []


def save_account(account_data):
    """Save a new account to JSON file."""
    accounts = load_accounts()
    accounts.append(account_data)
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ACCOUNTS_FILE)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(accounts, f, indent=2, ensure_ascii=False)


# ── Anti-detection helpers ───────────────────────────────────────────────────

def human_type(element, text, min_delay=0.1, max_delay=0.3):
    """Type text character-by-character with random delays."""
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(min_delay, max_delay))


def random_delay(min_sec=0.5, max_sec=1.2):
    """Sleep for a random duration between min and max seconds."""
    time.sleep(random.uniform(min_sec, max_sec))


def warm_session(driver):
    """Visit several popular sites to warm the browser session."""
    warming_urls = [
        "https://www.google.com",
        "https://www.bbc.com",
        "https://en.wikipedia.org",
        "https://www.youtube.com",
    ]
    for url in warming_urls:
        try:
            driver.get(url)
            random_delay(1.0, 3.0)
        except WebDriverException:
            continue


def create_driver(user_agent):
    """Create a Chrome WebDriver with anti-detection settings."""
    options = Options()
    options.add_argument(f"user-agent={user_agent}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-infobars")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    except WebDriverException:
        driver = webdriver.Chrome(options=options)

    # Hide webdriver property
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                window.chrome = {runtime: {}};
            """
        },
    )
    return driver


# ── 5sim API ─────────────────────────────────────────────────────────────────

class FiveSimAPI:
    """Wrapper around the 5sim.net SMS API."""

    BASE_URL = "https://5sim.net/v1"

    def __init__(self, api_key, country="usa", operator="any"):
        self.api_key = api_key
        self.country = country
        self.operator = operator
        self.headers = {"Authorization": f"Bearer {api_key}"}

    def buy_number(self):
        """Purchase a phone number for Google verification."""
        url = f"{self.BASE_URL}/user/buy/activation/{self.country}/{self.operator}/google"
        try:
            resp = requests.get(url, headers=self.headers, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "id": data.get("id"),
                    "phone": data.get("phone"),
                    "status": "success",
                }
            console.print(f"[red]5sim API error: {resp.status_code} - {resp.text}[/red]")
            return None
        except requests.RequestException as exc:
            console.print(f"[red]5sim request failed: {exc}[/red]")
            return None

    def get_sms_code(self, order_id, timeout=120):
        """Wait for SMS code to arrive."""
        url = f"{self.BASE_URL}/user/check/{order_id}"
        start = time.time()
        while time.time() - start < timeout:
            try:
                resp = requests.get(url, headers=self.headers, timeout=30)
                if resp.status_code == 200:
                    data = resp.json()
                    sms_list = data.get("sms", [])
                    if sms_list:
                        code = sms_list[0].get("code")
                        if code:
                            return code
            except requests.RequestException:
                pass
            time.sleep(5)
        return None

    def cancel_order(self, order_id):
        """Cancel an unused number order."""
        url = f"{self.BASE_URL}/user/cancel/{order_id}"
        try:
            requests.get(url, headers=self.headers, timeout=30)
        except requests.RequestException:
            pass


# ── Gmail creation logic ─────────────────────────────────────────────────────

def generate_username(first_name, last_name):
    """Generate a Gmail-compatible username from a name."""
    first = unidecode(first_name).lower().replace(" ", "")
    last = unidecode(last_name).lower().replace(" ", "")
    rand_digits = "".join(secrets.choice(string.digits) for _ in range(secrets.randbelow(4) + 3))
    patterns = [
        f"{first}.{last}{rand_digits}",
        f"{first}{last}{rand_digits}",
        f"{first}_{last}{rand_digits}",
        f"{last}.{first}{rand_digits}",
        f"{first}{rand_digits}",
    ]
    username = secrets.choice(patterns)
    # Keep only alphanumeric, dots, underscores
    username = "".join(c for c in username if c.isalnum() or c in "._")
    return username


def _click_next_button(driver, wait):
    """Click the Next / Continue button on a Google sign-up page."""
    selectors = [
        (By.XPATH, "//span[text()='Next']/ancestor::button"),
        (By.XPATH, "//span[text()='التالي']/ancestor::button"),
        (By.CSS_SELECTOR, "#identifierNext button"),
        (By.CSS_SELECTOR, "button[jsname='LgbsSe']"),
        (By.XPATH, "//button[contains(@class, 'VfPpkd-LgbsSe')]"),
    ]
    for by, selector in selectors:
        try:
            btn = wait.until(EC.element_to_be_clickable((by, selector)))
            btn.click()
            return True
        except (NoSuchElementException, TimeoutException):
            continue
    return False


def _select_dropdown_value(driver, wait, element_id, value):
    """Select a value from a dropdown, handling both native <select> and custom dropdowns."""
    el = wait.until(EC.presence_of_element_located((By.ID, element_id)))

    # Strategy 1: Use Select class for native <select> elements
    if el.tag_name.lower() == "select":
        try:
            Select(el).select_by_value(str(value))
            return
        except NoSuchElementException:
            pass

    # Strategy 2: Click the element, then wait for option to become clickable
    el.click()
    random_delay(0.5, 1.0)

    option_selectors = [
        (By.CSS_SELECTOR, f"#{element_id} option[value='{value}']"),
        (By.CSS_SELECTOR, f"#{element_id} [data-value='{value}']"),
        (By.XPATH, f"//ul[@role='listbox']//li[@data-value='{value}']"),
    ]
    for by, sel in option_selectors:
        try:
            opt = wait.until(EC.element_to_be_clickable((by, sel)))
            opt.click()
            return
        except (NoSuchElementException, TimeoutException):
            continue

    raise NoSuchElementException(
        f"Could not select value '{value}' from dropdown '#{element_id}'"
    )


def try_skip_phone_verification(driver, wait):
    """Attempt to skip or bypass phone verification using multiple strategies."""
    skip_selectors = [
        (By.XPATH, "//span[text()='Skip']/ancestor::button"),
        (By.XPATH, "//span[text()='تخطي']/ancestor::button"),
        (By.XPATH, "//span[contains(text(),'Skip')]/ancestor::button"),
        (By.XPATH, "//button[contains(text(),'Skip')]"),
        (By.XPATH, "//a[contains(text(),'Skip')]"),
        (By.XPATH, "//div[contains(text(),'Skip')]"),
    ]
    for by, selector in skip_selectors:
        try:
            el = driver.find_element(by, selector)
            el.click()
            console.print("[green]  ✓ Skipped phone verification[/green]")
            return True
        except NoSuchElementException:
            continue

    # Try "Not now" buttons
    not_now_selectors = [
        (By.XPATH, "//span[text()='Not now']/ancestor::button"),
        (By.XPATH, "//span[text()='ليس الآن']/ancestor::button"),
        (By.XPATH, "//button[contains(text(),'Not now')]"),
    ]
    for by, selector in not_now_selectors:
        try:
            el = driver.find_element(by, selector)
            el.click()
            console.print("[green]  ✓ Clicked 'Not now' to skip verification[/green]")
            return True
        except NoSuchElementException:
            continue

    # Try "Try another way"
    try:
        alt = driver.find_element(By.XPATH, "//button[contains(text(),'Try another way')]")
        alt.click()
        random_delay(1, 2)
        # Look for skip in alternative flow
        for by, selector in skip_selectors:
            try:
                el = driver.find_element(by, selector)
                el.click()
                console.print("[green]  ✓ Skipped via alternative method[/green]")
                return True
            except NoSuchElementException:
                continue
    except NoSuchElementException:
        pass

    return False


def handle_phone_with_5sim(driver, wait, fivesim):
    """Use 5sim API to handle phone verification."""
    console.print("[yellow]  ⏳ Purchasing phone number from 5sim...[/yellow]")
    number_info = fivesim.buy_number()
    if not number_info:
        console.print("[red]  ✗ Failed to purchase number[/red]")
        return False

    phone = number_info["phone"]
    order_id = number_info["id"]
    console.print(f"[green]  ✓ Got number: {phone}[/green]")

    # Enter phone number
    try:
        phone_input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='tel']"))
        )
        phone_input.clear()
        human_type(phone_input, phone)
        random_delay()
        _click_next_button(driver, wait)
        random_delay(2, 4)
    except (NoSuchElementException, TimeoutException) as exc:
        console.print(f"[red]  ✗ Failed to enter phone number: {exc}[/red]")
        fivesim.cancel_order(order_id)
        return False

    # Wait for SMS code
    console.print("[yellow]  ⏳ Waiting for SMS code...[/yellow]")
    code = fivesim.get_sms_code(order_id)
    if not code:
        console.print("[red]  ✗ SMS code not received[/red]")
        fivesim.cancel_order(order_id)
        return False

    console.print(f"[green]  ✓ Received SMS code: {code}[/green]")

    # Enter verification code
    try:
        code_input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='tel']"))
        )
        code_input.clear()
        human_type(code_input, code)
        random_delay()
        _click_next_button(driver, wait)
        random_delay(2, 3)
        return True
    except (NoSuchElementException, TimeoutException) as exc:
        console.print(f"[red]  ✗ Failed to enter verification code: {exc}[/red]")
        return False


def create_gmail_account(config, user_agents, names, fivesim=None):
    """Create a single Gmail account."""
    # Pick random name and user agent
    name_line = random.choice(names)
    parts = name_line.split(maxsplit=1)
    first_name = parts[0]
    last_name = parts[1] if len(parts) > 1 else random.choice(["Ahmed", "Ali", "Hassan", "Omar"])

    user_agent = random.choice(user_agents)
    password = load_password(config)
    if not password:
        return None

    birthday_parts = config["YOUR_BIRTHDAY"].split()
    if len(birthday_parts) != 3:
        console.print("[red]Error: Invalid birthday format in config (expected 'month day year')[/red]")
        return None

    birth_month, birth_day, birth_year = birthday_parts
    gender = config["YOUR_GENDER"]

    username = generate_username(first_name, last_name)
    console.print(f"[cyan]  → Name: {first_name} {last_name}[/cyan]")
    console.print(f"[cyan]  → Username: {username}@gmail.com[/cyan]")

    driver = None
    try:
        driver = create_driver(user_agent)
        wait = WebDriverWait(driver, 15)

        # Session warming
        console.print("[yellow]  ⏳ Warming session...[/yellow]")
        warm_session(driver)

        # Navigate to Gmail sign-up
        driver.get("https://accounts.google.com/signup/v2/createaccount?flowName=GlifWebSignIn&flowEntry=SignUp")
        random_delay(2, 4)

        # ── Step 1: Enter name ────────────────────────────────────────────
        console.print("[yellow]  ⏳ Entering name...[/yellow]")
        try:
            first_input = wait.until(EC.presence_of_element_located((By.NAME, "firstName")))
            last_input = driver.find_element(By.NAME, "lastName")
            human_type(first_input, first_name)
            random_delay()
            human_type(last_input, last_name)
            random_delay()
            _click_next_button(driver, wait)
            random_delay(2, 3)
        except (NoSuchElementException, TimeoutException) as exc:
            console.print(f"[red]  ✗ Failed to enter name: {exc}[/red]")
            return None

        # ── Step 2: Birthday & gender ─────────────────────────────────────
        console.print("[yellow]  ⏳ Entering birthday and gender...[/yellow]")
        try:
            _select_dropdown_value(driver, wait, "month", birth_month)
            random_delay()

            day_input = wait.until(EC.presence_of_element_located((By.ID, "day")))
            day_input.clear()
            human_type(day_input, birth_day)
            random_delay()

            year_input = wait.until(EC.presence_of_element_located((By.ID, "year")))
            year_input.clear()
            human_type(year_input, birth_year)
            random_delay()

            _select_dropdown_value(driver, wait, "gender", gender)
            random_delay()

            _click_next_button(driver, wait)
            random_delay(2, 3)
        except (NoSuchElementException, TimeoutException) as exc:
            console.print(f"[red]  ✗ Failed to enter birthday/gender: {exc}[/red]")
            return None

        # ── Step 3: Choose email ──────────────────────────────────────────
        console.print("[yellow]  ⏳ Setting up email address...[/yellow]")
        try:
            # Try to click "Create your own Gmail address"
            create_own_selectors = [
                (By.XPATH, "//div[contains(text(),'Create your own Gmail address')]"),
                (By.XPATH, "//span[contains(text(),'Create your own Gmail address')]"),
                (By.XPATH, "//div[contains(text(),'إنشاء عنوان Gmail')]"),
            ]
            for by, selector in create_own_selectors:
                try:
                    el = driver.find_element(by, selector)
                    el.click()
                    random_delay(1, 2)
                    break
                except NoSuchElementException:
                    continue

            # Enter custom username
            email_input = wait.until(
                EC.presence_of_element_located((By.NAME, "Username"))
            )
            email_input.clear()
            human_type(email_input, username)
            random_delay()
            _click_next_button(driver, wait)
            random_delay(2, 3)
        except (NoSuchElementException, TimeoutException) as exc:
            console.print(f"[red]  ✗ Failed to set email: {exc}[/red]")
            return None

        # ── Step 4: Password ──────────────────────────────────────────────
        console.print("[yellow]  ⏳ Setting password...[/yellow]")
        try:
            passwd_input = wait.until(
                EC.presence_of_element_located((By.NAME, "Passwd"))
            )
            confirm_input = driver.find_element(By.NAME, "PasswdAgain")
            human_type(passwd_input, password)
            random_delay()
            human_type(confirm_input, password)
            random_delay()
            _click_next_button(driver, wait)
            random_delay(2, 4)
        except (NoSuchElementException, TimeoutException) as exc:
            console.print(f"[red]  ✗ Failed to set password: {exc}[/red]")
            return None

        # ── Step 5: Phone verification ────────────────────────────────────
        console.print("[yellow]  ⏳ Handling phone verification...[/yellow]")
        phone_handled = try_skip_phone_verification(driver, wait)

        if not phone_handled and fivesim:
            phone_handled = handle_phone_with_5sim(driver, wait, fivesim)

        if not phone_handled:
            console.print("[red]  ✗ Phone verification required but could not be handled[/red]")
            # Still try to continue; Google may not always require it

        random_delay(2, 3)

        # ── Step 6: Accept terms ──────────────────────────────────────────
        console.print("[yellow]  ⏳ Accepting terms...[/yellow]")
        agree_selectors = [
            (By.XPATH, "//span[text()='I agree']/ancestor::button"),
            (By.XPATH, "//span[text()='أوافق']/ancestor::button"),
            (By.XPATH, "//button[contains(text(),'I agree')]"),
            (By.XPATH, "//span[contains(text(),'I agree')]/ancestor::button"),
        ]
        for by, selector in agree_selectors:
            try:
                btn = driver.find_element(by, selector)
                btn.click()
                random_delay(2, 3)
                break
            except NoSuchElementException:
                continue

        # ── Step 7: Verify success ────────────────────────────────────────
        random_delay(3, 5)
        email = f"{username}@gmail.com"

        # Check if we reached the account page
        current_url = driver.current_url
        if "myaccount" in current_url or "mail.google" in current_url or "gds" in current_url:
            console.print(f"[green]  ✓ Account created successfully: {email}[/green]")
        else:
            console.print(f"[yellow]  ⚠ Account may have been created: {email}[/yellow]")
            console.print(f"[yellow]    Final URL: {current_url}[/yellow]")

        account_data = {
            "email": email,
            "password": password,
            "first_name": first_name,
            "last_name": last_name,
            "birthday": config["YOUR_BIRTHDAY"],
            "gender": config["YOUR_GENDER"],
            "created_at": datetime.now().isoformat(),
            "status": "active",
        }
        save_account(account_data)
        return account_data

    except WebDriverException as exc:
        console.print(f"[red]  ✗ Browser error: {exc}[/red]")
        return None
    finally:
        if driver:
            try:
                driver.quit()
            except WebDriverException:
                pass


# ── Menu actions ─────────────────────────────────────────────────────────────

def action_create_accounts(config, user_agents, names):
    """Menu option 1 – Create Gmail accounts."""
    try:
        count = int(console.input("[bold cyan]How many accounts to create? [/bold cyan]"))
        if count < 1:
            console.print("[red]Number must be at least 1[/red]")
            return
    except ValueError:
        console.print("[red]Invalid number[/red]")
        return

    api_key = load_api_key(config)
    fivesim = None
    if api_key:
        fivesim = FiveSimAPI(api_key, config["FIVESIM_COUNTRY"], config["FIVESIM_OPERATOR"])
        console.print("[green]✓ 5sim API configured[/green]")
    else:
        console.print("[yellow]⚠ 5sim API not configured – phone verification may fail[/yellow]")

    created = 0
    failed = 0
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task = progress.add_task("Creating accounts...", total=count)
        for i in range(count):
            progress.update(task, description=f"Account {i + 1}/{count}")
            console.print(f"\n[bold]── Account {i + 1}/{count} ──[/bold]")
            result = create_gmail_account(config, user_agents, names, fivesim)
            if result:
                created += 1
                console.print(f"[green]✓ Success: {result['email']}[/green]")
            else:
                failed += 1
                console.print("[red]✗ Failed to create account[/red]")
            progress.advance(task)
            if i < count - 1:
                delay = random.uniform(5, 15)
                console.print(f"[dim]  Waiting {delay:.0f}s before next account...[/dim]")
                time.sleep(delay)

    console.print()
    table = Table(title="Creation Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Total Attempted", str(count))
    table.add_row("Created", str(created))
    table.add_row("Failed", str(failed))
    rate = (created / count * 100) if count else 0
    table.add_row("Success Rate", f"{rate:.1f}%")
    console.print(table)


def action_view_statistics():
    """Menu option 2 – View statistics."""
    accounts = load_accounts()
    total = len(accounts)
    active = sum(1 for a in accounts if a.get("status") == "active")
    rate = (active / total * 100) if total else 0
    last_created = accounts[-1]["created_at"] if accounts else "N/A"

    table = Table(title="📊 Account Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Total Accounts Created", str(total))
    table.add_row("Active Accounts", str(active))
    table.add_row("Success Rate", f"{rate:.1f}%")
    table.add_row("Last Creation", str(last_created))
    console.print(table)


def action_settings(config):
    """Menu option 3 – Show current settings."""
    table = Table(title="⚙️  Current Settings")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Birthday", config["YOUR_BIRTHDAY"])
    table.add_row("Gender", {"1": "Male", "2": "Female", "3": "Other"}.get(config["YOUR_GENDER"], config["YOUR_GENDER"]))
    table.add_row("5sim Country", config["FIVESIM_COUNTRY"])
    table.add_row("5sim Operator", config["FIVESIM_OPERATOR"])
    table.add_row("5sim API Key", "Configured" if load_api_key(config) else "Not set")
    table.add_row("Arabic Names", str(config["USE_ARABIC_NAMES"]))
    table.add_row("Names File", config["NAMES_FILE"])
    table.add_row("User Agents File", config["USER_AGENTS_FILE"])
    console.print(table)
    console.print("\n[dim]Edit config/config.py to change settings.[/dim]")


def action_view_accounts():
    """Menu option 4 – View saved accounts."""
    accounts = load_accounts()
    if not accounts:
        console.print("[yellow]No accounts saved yet.[/yellow]")
        return

    table = Table(title="📁 Saved Accounts")
    table.add_column("#", style="dim")
    table.add_column("Email", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Created", style="yellow")
    table.add_column("Status", style="magenta")

    for idx, acct in enumerate(accounts, 1):
        name = f"{acct.get('first_name', '')} {acct.get('last_name', '')}".strip()
        table.add_row(
            str(idx),
            acct.get("email", ""),
            name,
            acct.get("created_at", ""),
            acct.get("status", "unknown"),
        )
    console.print(table)


# ── Main ─────────────────────────────────────────────────────────────────────

def show_banner():
    """Display welcome banner."""
    console.print(Panel(Text(BANNER, style="bold cyan"), title="Gmail Creator Pro", subtitle="v2.0.0"))
    features = [
        "✅ Advanced Anti-Detection System",
        "✅ Phone Verification Bypass",
        "✅ 5sim API Integration",
        "✅ Beautiful Modern Interface",
        "✅ Auto-Save Accounts",
        "✅ Smart Retry Logic",
    ]
    for feat in features:
        console.print(f"  {feat}")
    console.print()


def show_menu():
    """Display the interactive menu and return user choice."""
    menu = Table(show_header=False, box=None, padding=(0, 2))
    menu.add_column(style="bold cyan")
    menu.add_column()
    menu.add_row("1.", "Create Gmail Accounts 🚀")
    menu.add_row("2.", "View Statistics 📊")
    menu.add_row("3.", "Settings ⚙️")
    menu.add_row("4.", "View Saved Accounts 📁")
    menu.add_row("5.", "Exit 👋")
    console.print(Panel(menu, title="Menu"))
    return console.input("[bold cyan]Select option (1-5): [/bold cyan]").strip()


def main():
    """Application entry point."""
    show_banner()

    config = load_config()
    user_agents = load_user_agents(config)
    names = load_names(config)
    if not names:
        console.print("[red]Cannot start without names. Add names to data/names.txt[/red]")
        sys.exit(1)

    while True:
        choice = show_menu()
        if choice == "1":
            action_create_accounts(config, user_agents, names)
        elif choice == "2":
            action_view_statistics()
        elif choice == "3":
            action_settings(config)
        elif choice == "4":
            action_view_accounts()
        elif choice == "5":
            console.print("[bold green]Goodbye! 👋[/bold green]")
            break
        else:
            console.print("[red]Invalid option. Please select 1-5.[/red]")
        console.print()


if __name__ == "__main__":
    main()
