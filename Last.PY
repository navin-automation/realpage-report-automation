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
EXCEL_PATH = "RR.xlsx"
DOWNLOAD_FOLDER = "RealPage_Reports" # Ensure this folder exists or is correctly targeted

# ================= LOAD EXCEL (RANGE A23 - A39) =================
df_full = pd.read_excel(EXCEL_PATH)

# Excel Row 23 = Index 21
# Excel Row 39 = Index 37 (Inclusive 38)
df = df_full.iloc[35:44] 

print(f"🎯 Targeted Rows: {len(df)} (From Excel Row 23 to 39)")

# ================= VARIABLES =================
driver = None
current_username = None
current_portfolio = None 

# ================= HELPER FUNCTIONS =================
def start_browser():
    """Browser settings with MULTIPLE DOWNLOAD ALLOWED"""
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    
    # --- MAGIC SETTINGS TO FIX DOWNLOAD BLOCKS ---
    prefs = {
        "download.default_directory": os.path.abspath(DOWNLOAD_FOLDER),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True,
        
        # This line allows MULTIPLE DOWNLOADS automatically
        "profile.default_content_setting_values.automatic_downloads": 1, 
        
        "safebrowsing.enabled": True
    }
    options.add_experimental_option("prefs", prefs)
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def clean_filename(name):
    """Makes the filename safe by removing invalid characters"""
    return "".join([c for c in name if c.isalnum() or c in (' ', '-', '_')]).strip()

def wait_and_force_rename(community_name, files_before_click):
    """
    Waits after clicking generate and renames the newly downloaded file.
    """
    print(f"   🕵️ Waiting for new file for: '{community_name}'...")
    
    timeout = 60  # Wait up to 60 seconds
    start_time = time.time()
    downloaded_file_path = None

    while time.time() - start_time < timeout:
        files_now = set(glob.glob(os.path.join(DOWNLOAD_FOLDER, "*")))
        new_files = files_now - files_before_click
        
        if new_files:
            for f in new_files:
                if not f.endswith('.crdownload') and not f.endswith('.tmp'):
                    downloaded_file_path = f
                    break
            if downloaded_file_path:
                break 
        time.sleep(1)

    if downloaded_file_path:
        extension = os.path.splitext(downloaded_file_path)[1]
        safe_name = clean_filename(community_name)
        new_filename = f"{safe_name}{extension}"
        new_file_path = os.path.join(DOWNLOAD_FOLDER, new_filename)

        if os.path.exists(new_file_path):
            try: os.remove(new_file_path)
            except: pass
        
        try:
            for _ in range(5):
                try:
                    os.rename(downloaded_file_path, new_file_path)
                    print(f"   ✨ SUCCESS: File Renamed to -> {new_filename}")
                    return True
                except PermissionError:
                    time.sleep(1)
            print("   ❌ Rename Error: File was locked.")
            return False
        except Exception as e:
            print(f"   ❌ Rename Failed: {e}")
            return False
    else:
        print("   ⚠️ Error: Download Timeout (File was not generated).")
        return False

def navigate_to_sde(driver):
    wait = WebDriverWait(driver, 30)
    print("   ⌛ Navigating to SDE Extracts...")
    try:
        time.sleep(2)
        reports_arrow = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "omnibar-navigation-item[page-id='reporting'] omnibar-icon.o-item-arrow")))
        driver.execute_script("arguments[0].click();", reports_arrow)

        time.sleep(1)
        manage_reports = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a.o-item-button[title='Manage Reports']")))
        driver.execute_script("arguments[0].click();", manage_reports)

        time.sleep(2)
        wait.until(EC.presence_of_element_located((By.ID, "sde-extracts-tab")))
        driver.execute_script("document.querySelector('#sde-extracts-tab').click();")
        print("   ✅ SDE Tab Reached")
    except Exception as e:
        print(f"   ⚠️ Navigation Error: {e}")
        driver.refresh()
        time.sleep(5)

def change_company(driver, portfolio_name):
    wait = WebDriverWait(driver, 20)
    print(f"🏢 Changing Company to: {portfolio_name}...")
    try:
        profile_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.o-user__info")))
        driver.execute_script("arguments[0].click();", profile_btn)
        time.sleep(1)

        change_comp_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div[title='Change Company']")))
        driver.execute_script("arguments[0].click();", change_comp_btn)
        time.sleep(2) 

        toggle_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.o-select__toggle")))
        driver.execute_script("arguments[0].click();", toggle_btn)
        time.sleep(1)

        search_box = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input.o-select__search__input")))
        search_box.clear()
        search_box.send_keys(portfolio_name)
        time.sleep(2)

        company_option = wait.until(EC.element_to_be_clickable((
            By.XPATH, f"//div[contains(@class, 'o-option__text__title') and contains(text(), '{portfolio_name}')]"
        )))
        driver.execute_script("arguments[0].click();", company_option)
        print(f"   ✅ Selected: {portfolio_name}")
        time.sleep(1)

        try:
            ok_element = wait.until(EC.presence_of_element_located((
                By.XPATH, "//omnibar-modal-footer//span[normalize-space()='Ok']"
            )))
            driver.execute_script("arguments[0].click();", ok_element)
            print("   ✅ OK Clicked")
        except:
            ok_element = driver.find_element(By.CSS_SELECTOR, "omnibar-modal-footer omnibar-button:last-child button")
            driver.execute_script("arguments[0].click();", ok_element)
            print("   ✅ OK Clicked (Backup)")

        print("   ⏳ Waiting 15s for Dashboard Reload...")
        time.sleep(15)
        return True
    except Exception as e:
        print(f"   ❌ Change Company Failed: {e}")
        try: webdriver.ActionChains(driver).send_keys("\ue00c").perform()
        except: pass
        return False

# ================= MAIN LOOP =================
print("🚀 Starting FIX Test (A23 - A39)...")

# Ensure download directory exists
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

for index, row in df.iterrows():
    row_user = str(row["UserName"]).strip()
    row_pass = str(row["Password"]).strip()
    row_url = str(row["PlatForm URL"]).strip()
    community_name = str(row["Community Name"]).strip()
    portfolio_name = str(row["Portfolio Name"]).strip() 

    print(f"\n🔄 Processing Excel Row {index + 2}: {community_name}")
    print(f"   👤 User: {row_user} | 🏢 Target Portfolio: {portfolio_name}")

    # --- 1. LOGIN LOGIC ---
    if row_user != current_username:
        if driver is not None:
            print("🛑 Closing previous session...")
            driver.quit()
        
        driver = start_browser()
        wait = WebDriverWait(driver, 30)
        
        try:
            print(f"🔐 Logging in as: {row_user}...")
            driver.get(row_url)
            wait.until(EC.presence_of_element_located((By.ID, "Username"))).send_keys(row_user)
            driver.execute_script("arguments[0].click();", wait.until(EC.presence_of_element_located((By.XPATH, "//button[@type='submit']"))))
            wait.until(EC.presence_of_element_located((By.ID, "Password"))).send_keys(row_pass)
            driver.execute_script("arguments[0].click();", wait.until(EC.presence_of_element_located((By.XPATH, "//button[@type='submit']"))))
            print("🎉 Login successful")
            
            navigate_to_sde(driver)
            current_username = row_user
            current_portfolio = None 
            
        except Exception as e:
            print(f"❌ Login Error: {e}")
            current_username = None
            continue

    # --- 2. CHANGE COMPANY LOGIC ---
    if portfolio_name != current_portfolio:
        success = change_company(driver, portfolio_name)
        if success:
        
            current_portfolio = portfolio_name
            navigate_to_sde(driver)
        else:
            print(f"⚠️ Warning: Could not switch to {portfolio_name}. Continuing...")

    # --- 3. TASK LOGIC ---
    try:
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

        time.sleep(2)
        driver.execute_script("""
        (() => {
          const btn = document.querySelector("raul-select[label='Select Property'] button.r-select__toggle");
          if(btn) { btn.click(); }
        })();
        """)

        print(f"   ⌛ Searching: {community_name}")
        time.sleep(2)
        try: driver.switch_to.active_element.clear()
        except: pass
        driver.switch_to.active_element.send_keys(community_name)
        time.sleep(2)

        try:
            wait = WebDriverWait(driver, 5)
            result_item = wait.until(EC.presence_of_element_located((
                By.XPATH, f"//div[contains(text(), '{community_name}')]"
            )))
            driver.execute_script("arguments[0].click();", result_item)
            print(f"   ✅ Selected: {community_name}")
            
            time.sleep(1)
            generate_btn = wait.until(EC.element_to_be_clickable((
                By.CSS_SELECTOR, "button.dynamic-form-button-rb-save"
            )))
            
            files_before = set(glob.glob(os.path.join(DOWNLOAD_FOLDER, "*")))
            driver.execute_script("arguments[0].click();", generate_btn)
            print("   🚀 Generate Clicked - Waiting for download...")
            
            wait_and_force_rename(community_name, files_before)
            
            print("   ✅ Waiting 5s before next row...")
            time.sleep(5)    

        except TimeoutException:
            print(f"   ⚠️ Not Found: {community_name}")
            try: webdriver.ActionChains(driver).send_keys("\ue00c").perform()
            except: pass

    except Exception as e:
        print(f"❌ Error: {e}")
        continue

print("\n🛑 Test A23-A39 Complete.")
while True:
    time.sleep(60)