# RealPage Report Automation 🚀

An automated web scraping and reporting tool designed to streamline property management workflows on RealPage portals. By utilizing Python, Selenium, and Playwright, this project eliminates manual data extraction tasks, saving significant time and reducing human error.

## 🛠️ Tech Stack
- **Language:** Python
- **Automation Frameworks:** Playwright, Selenium WebDriver
- **Data Handling:** Pandas, OpenPyXL

## ✨ Key Features
- **Automated Authentication:** Seamlessly logs into RealPage dashboards and handles session management.
- **Multi-Property Navigation:** Dynamically searches and switches between different communities and portfolios.
- **Smart Download Handling:** Automatically waits for reports to generate, intercepts the downloads, and renames files cleanly based on the target community.
- **Popup Management:** Intelligently detects and dismisses blocking iframes and alerts during the workflow.
- **Batch Processing:** Reads target parameters sequentially from an Excel file (`RR.xlsx`) for scalable batch runs.

## ⚙️ Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/navin-automation/realpage-report-automation.git](https://github.com/navin-automation/realpage-report-automation.git)
   cd realpage-report-automation
