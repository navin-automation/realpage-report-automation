import time
import pandas as pd
import os
import glob
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

# ================= CONFIG =================
EXCEL_PATH = "RR.xlsx" # Updated to match your file name
DOWNLOAD_FOLDER = "RealPage_Reports" # Verify that this path is correct

# ================= LOAD EXCEL (A2 to A22) =================
df_full = pd.read_excel(EXCEL_PATH)

# Python Index 0 = Excel Row 2
# Excel Row 22 = Index 20
# Slice 0:21 (Rows 1 to 18)
df = df_full.iloc[0:19] #0 20

print(f"🎯 Targeted Rows: {len(df)} (From Excel Row 2 to 22)")

# ================= HELPER FUNCTIONS =================
def start_browser():
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    
    # Auto-Download Settings (Disables popups to allow custom renaming)
    prefs = {
        "download.default_directory": DOWNLOAD_FOLDER,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True,
        "safebrowsing.enabled": True
    }
    options.add_experimental_option("prefs", prefs)
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def get_latest_file(folder):
    """Finds the most recently created file in the folder"""
    files = glob.glob(os.path.join(folder, "*"))
    if not files:
        return None
    return max(files, key=os.path.getctime)

def clean_filename(name):
    """Removes invalid characters from the filename"""
    return "".join([c for c in name if c.isalnum() or c in (' ', '-', '_')]).strip()

def wait_and_force_rename(community_name, files_before_click):
    """
    1. Waits until a new file is downloaded.
    2. Renames the new file to match the Community Name.
    """
    print(f"   🕵️ Waiting for new file for: '{community_name}'...")
    
    timeout = 60  # Waits for up to 60 seconds
    start_time = time.time()
    downloaded_file_path = None

    while time.time() - start_time < timeout:
        # Check current files
        files_now = set(glob.glob(os.path.join(DOWNLOAD_FOLDER, "*")))
        
        # Identify the newly downloaded file
        new_files = files_now - files_before_click
        
        if new_files:
            # If a new file is found, ensure it is fully downloaded (not .crdownload or .tmp)
            for f in new_files:
                if not f.endswith('.crdownload') and not f.endswith('.tmp'):
                    downloaded_file_path = f
                    break
            
            if downloaded_file_path:
                break # Target file found!
        
        time.sleep(1)

    if downloaded_file_path:
        # File identified, proceeding to rename
        extension = os.path.splitext(downloaded_file_path)[1] # Extract extension (e.g., .xml, .pdf)
        safe_name = clean_filename(community_name)
        new_filename = f"{safe_name}{extension}"
        new_file_path = os.path.join(DOWNLOAD_FOLDER, new_filename)

        # If a file with the same name exists, delete it to prevent rename errors
        if os.path.exists(new_file_path):
            try: os.remove(new_file_path)
            except: pass
        
        # Core rename execution
        try:
            # Retry loop for renaming (handles temporary file locks)
            for _ in range(5):
                try:
                    os.rename(downloaded_file_path, new_file_path)
                    print(f"   ✨ SUCCESS: File Renamed to -> {new_filename}")
                    return True
                except PermissionError:
                    time.sleep(1) # Wait 1 second before retrying
            
            print("   ❌ Rename Error: File was locked by another process.")
            return False
        except Exception as e:
            print(f"   ❌ Rename Failed: {e}")
            return False
    else:
        print("   ⚠️ Error: Download Timeout (File was not generated).")
        return False

def perform_login_and_navigate(driver, url, user, pwd):
    wait = WebDriverWait(driver, 30)
    print(f"🔐 Logging in as: {user}...")
    driver.get(url)

    wait.until(EC.presence_of_element_located((By.ID, "Username"))).send_keys(user)
    driver.execute_script("arguments[0].click();", wait.until(EC.presence_of_element_located((By.XPATH, "//button[@type='submit']"))))
    
    wait.until(EC.presence_of_element_located((By.ID, "Password"))).send_keys(pwd)
    driver.execute_script("arguments[0].click();", wait.until(EC.presence_of_element_located((By.XPATH, "//button[@type='submit']"))))
    print("🎉 Login successful")
    
    print("⌛ Navigating to SDE Extracts...")
    reports_arrow = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "omnibar-navigation-item[page-id='reporting'] omnibar-icon.o-item-arrow")))
    driver.execute_script("arguments[0].click();", reports_arrow)

    manage_reports = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a.o-item-button[title='Manage Reports']")))
    driver.execute_script("arguments[0].click();", manage_reports)

    wait.until(EC.presence_of_element_located((By.ID, "sde-extracts-tab")))
    driver.execute_script("document.querySelector('#sde-extracts-tab').click();")
    print("✅ SDE Tab Reached")

# ================= MAIN LOOP =================
driver = None
current_username = None

print("🚀 Starting Batch Processing (Row A2 - A22)...")

for index, row in df.iterrows():
    row_user = str(row["UserName"]).strip()
    row_pass = str(row["Password"]).strip()
    row_url = str(row["PlatForm URL"]).strip()
    community_name = str(row["Community Name"]).strip()

    print(f"\n🔄 Processing Row {index + 2}: {community_name} (User: {row_user})")

    # --- CHECK 1: LOGIN CHANGE ---
    if row_user != current_username:
        if driver is not None:
            driver.quit()
        
        driver = start_browser()
        wait = WebDriverWait(driver, 30)
        
        try:
            perform_login_and_navigate(driver, row_url, row_user, row_pass)
            current_username = row_user
        except Exception as e:
            print(f"❌ Login Failed: {e}")
            current_username = None
            continue

    # --- CHECK 2: TASK ---
    try:
        # A. Convergent Billing
        time.sleep(3)
        driver.execute_script("""
        (() => {
          const billing = [...document.querySelectorAll("span.r-cursor-pointer")]
              .find(el => el.textContent.trim() === "Convergent Billing");
          if(billing) {
            billing.scrollIntoView({ behavior: "smooth", block: "center" });
            billing.click();
          }
        })();
        """)

        # B. Open Dropdown
        time.sleep(2)
        driver.execute_script("""
        (() => {
          const btn = document.querySelector("raul-select[label='Select Property'] button.r-select__toggle");
          if(btn) { btn.click(); }
        })();
        """)

        # C. Search & Clear
        print(f"   ⌛ Searching: {community_name}")
        time.sleep(2)
        try: driver.switch_to.active_element.clear()
        except: pass
        driver.switch_to.active_element.send_keys(community_name)

        # D. Select
        time.sleep(2)
        try:
            wait = WebDriverWait(driver, 5)
            result_item = wait.until(EC.presence_of_element_located((
                By.XPATH, f"//div[contains(text(), '{community_name}')]"
            )))
            driver.execute_script("arguments[0].click();", result_item)
            print(f"   ✅ Selected: {community_name}")

            # E. Generate & Rename
            time.sleep(1)
            generate_btn = wait.until(EC.element_to_be_clickable((
                By.CSS_SELECTOR, "button.dynamic-form-button-rb-save"
            )))
            
            # --- SNAPSHOT BEFORE CLICK (Core Logic) ---
            # Record existing files before triggering the download
            files_before = set(glob.glob(os.path.join(DOWNLOAD_FOLDER, "*")))
            
            # Click Generate
            driver.execute_script("arguments[0].click();", generate_btn)
            print("   🚀 Generate Clicked - Waiting for download...")
            
            # --- WAIT AND RENAME ---
            wait_and_force_rename(community_name, files_before)

        except TimeoutException:
            print(f"   ⚠️ Not Found: {community_name}")
            try: webdriver.ActionChains(driver).send_keys("\ue00c").perform()
            except: pass
            continue

    except Exception as e:
        print(f"   ❌ Error: {e}")
        continue

print("\n🛑 PROCESS COMPLETE (A2-A22)")
while True:
    time.sleep(60)