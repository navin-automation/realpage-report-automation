import os
from playwright.sync_api import sync_playwright
import time

# --- PROPERTY LIST ---
PROPERTY_LIST = [
    "Demo Property 1",
    "Demo Property 2",
    "Demo Property 3"
]

# --- FOLDER SETUP ---
REPORT_FOLDER = "RealPage_Reports"
USER_DATA_DIR = "Chrome_Profile" 

if not os.path.exists(REPORT_FOLDER):
    os.makedirs(REPORT_FOLDER)

print(f"📂 REPORTS WILL BE SAVED HERE: {os.path.abspath(REPORT_FOLDER)}")

# --- HELPER FUNCTIONS ---
def get_frame_with_selector(page, selector):
    for frame in page.frames:
        try:
            if frame.locator(selector).count() > 0:
                return frame
        except:
            continue
    return None

def handle_potential_popups(page):
    print("👀 Checking for blocking popups...")
    time.sleep(3)
    popup_found = False
    for frame in page.frames:
        try:
            new_popup_btn = frame.locator("#btn3 > button")
            old_popup_btn = frame.locator("#btnCloseLabel")

            if new_popup_btn.is_visible():
                print("⚠️ ALERT: New Month-end Popup detected! Clicking Cancel...")
                new_popup_btn.click()
                popup_found = True
            elif old_popup_btn.is_visible():
                print("⚠️ ALERT: Old Property Date Popup detected! Clicking Close...")
                old_popup_btn.click()
                popup_found = True

            if popup_found:
                print("✅ Popup handled successfully.")
                time.sleep(2)
                break
        except:
            continue
    if not popup_found:
        print("👍 No blocking popups found.")    

def run():
    with sync_playwright() as p:
        print("🚀 Launching Browser...")
        
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False, 
            slow_mo=50,
            accept_downloads=True,
            viewport={"width": 1366, "height": 768},
            args=["--start-maximized"]
        )
        
        if len(context.pages) > 0:
            login_page = context.pages[0]
        else:
            login_page = context.new_page()

        # --- LOGIN ---
        print("🚀 Step 1: Login Process Started...")
        login_page.goto("https://demo.onesite.realpage.com/") # Replaced with demo URL

        try:
            login_page.wait_for_selector('iframe[name="logonFrm"]', timeout=5000)
            login_frame = login_page.frame(name="logonFrm")
            login_frame.fill("#txtLogin", "your_demo_username") 
            login_frame.fill("#txtPassword", "your_demo_password") 
            print("👆 Clicking Sign On...")
            login_frame.click('button:has-text("Sign on"), input[value="Sign on"]')
        except:
            print("ℹ️ Already logged in?")

        print("⏳ Waiting for Dashboard Window (10 sec)...")
        login_page.wait_for_timeout(10000)
        
        dashboard_page = None
        for page in context.pages:
            if "multishell" in page.url:
                dashboard_page = page
                dashboard_page.bring_to_front()
                print("✅ Found Multishell Window!")
                break
            elif "dashboards" in page.url:
                page.close()
        
        if not dashboard_page:
            if "multishell" in login_page.url:
                dashboard_page = login_page
            else:
                print("🚨 Error: Dashboard window not found!")
                return

        dashboard_page.wait_for_load_state('networkidle')

        # --- 🟢 POPUP CHECK 1: Immediately after login ---
        handle_potential_popups(dashboard_page)

        # ============================================================
        # MAIN LOOP
        # ============================================================
        
        for index, prop_name in enumerate(PROPERTY_LIST):
            print(f"\n==================================================")
            print(f"🏢 Processing {index + 1}/{len(PROPERTY_LIST)}: {prop_name}")
            print(f"==================================================")

            try:
                # -----------------------------------------------
                # PART A: CHANGE PROPERTY
                # -----------------------------------------------
                print("🔄 Switching Property...")
                time.sleep(2)

                # 1. Click Header
                header_clicked = False
                try:
                    header = dashboard_page.locator('#sitename, #raul-header-properties').first
                    if header.is_visible():
                        header.click()
                        header_clicked = True
                    else:
                        shell = dashboard_page.frame_locator('iframe[name="ifrmShell"]')
                        header = shell.locator('#sitename, #raul-header-properties').first
                        if header.is_visible():
                            header.click()
                            header_clicked = True
                except: pass

                if not header_clicked:
                    print("❌ Error: Header not found!")
                    continue 

                print("⏳ Popup wait (2s)...")
                time.sleep(2) 

                # 2. Typing & Enter
                print(f"⌨️ Typing: {prop_name}")
                dashboard_page.keyboard.type(prop_name, delay=50)
                time.sleep(1)
                dashboard_page.keyboard.press("Enter")
                time.sleep(3)

                # 3. Select Result
                result_frame = get_frame_with_selector(dashboard_page, '#tblPropertyList_ST')
                if result_frame:
                    result_link = result_frame.locator('#tblPropertyList_ST > tbody > tr > td:nth-child(2) > a').first
                    if result_link.is_visible():
                        result_link.click()
                        print("✅ Property Selected!")
                    else:
                        print(f"⚠️ Property not found in list.")
                        dashboard_page.keyboard.press("Escape")
                        continue
                else:
                    print("❌ Search table not found.")
                    dashboard_page.keyboard.press("Escape")
                    continue

                print("⏳ Waiting for Page Reload...")
                time.sleep(6) 
                dashboard_page.wait_for_load_state('networkidle')

                # --- 🟢 POPUP CHECK 2: After property switch ---
                handle_potential_popups(dashboard_page)

                # -----------------------------------------------
                # PART B: GENERATE REPORT
                # -----------------------------------------------
                
                shell_frame = dashboard_page.frame_locator('iframe[name="ifrmShell"]')
                page_frame = shell_frame.frame_locator('#ifrmPage')

                # Step 2: SDE
                sde_tab = page_frame.locator('#tab_SDE')
                sde_tab.wait_for(state="visible", timeout=20000)
                sde_tab.click()
                time.sleep(4)

                # Step 3: Convergent Billing
                tab_frame = page_frame.frame_locator('#ifrmTab')
                billing_row = tab_frame.get_by_text("Convergent Billing", exact=True)
                billing_row.wait_for(state="visible")
                billing_row.scroll_into_view_if_needed()
                billing_row.click()
                time.sleep(1)
                billing_row.click()
                time.sleep(2)

                # Step 4: Generate Link
                wk_frame = tab_frame.frame_locator('#wkframe')
                generate_link = wk_frame.get_by_role("link", name="Generate")
                generate_link.wait_for(state="visible")
                generate_link.click()

                # Step 5: Popup Handling
                print("👉 Handling Generate Popup...")
                time.sleep(4)
                gen_popup_frame = get_frame_with_selector(dashboard_page, '#btnSaveLabel')
                if gen_popup_frame:
                    gen_popup_frame.locator('#btnSaveLabel').click()
                    print("✅ Generate Clicked!")
                else:
                    try:
                        modal = shell_frame.frame_locator('#IframeModal1 iframe').first
                        modal.locator('#btnSaveLabel').click()
                        print("✅ Fallback Clicked!")
                    except: pass

                # Step 6: Smart Refresh Loop
                print("👉 Refreshing until Ready...")
                time.sleep(2)
                max_retries = 30
                report_ready = False
                
                for attempt in range(1, max_retries + 1):
                    refresh_btn = wk_frame.locator('#btnRefreshLabel')
                    if refresh_btn.is_visible():
                        refresh_btn.click()
                    time.sleep(4)
                    
                    download_link = wk_frame.locator("#tblReports_ST > tbody > tr").first.locator("td:nth-child(3) > a")
                    if download_link.is_visible():
                        print(f"✅ Report Ready! (Attempt {attempt})")
                        report_ready = True
                        break
                    else:
                        print(f"⏳ In Process... ({attempt}/{max_retries})")
                
                if not report_ready:
                    print(f"❌ Timeout skipping {prop_name}")
                    continue

                # -----------------------------------------------
                # PART C: DOWNLOAD
                # -----------------------------------------------
                print("👉 Downloading...")
                try:
                    with dashboard_page.expect_download(timeout=60000) as download_info:
                        download_link.click()

                    download = download_info.value
                    safe_name = prop_name.replace(" ", "_")
                    final_filename = f"{safe_name}.xml"
                    save_path = os.path.join(REPORT_FOLDER, final_filename)
                    download.save_as(save_path)
                    print(f"🎉 SAVED: {final_filename}")

                except Exception as e:
                    print(f"❌ Download Error: {e}")

            except Exception as e:
                print(f"❌ Error on {prop_name}: {e}")

            time.sleep(2)

        print("\n✅ ALL DONE!")
        context.close()

if __name__ == "__main__":
    run()