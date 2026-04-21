from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from dotenv import load_dotenv
import time
import json
import os
import random
import boto3
import re   
from datetime import datetime

# --- 1. CẤU HÌNH ---
load_dotenv()

DRIVER_PATH = r"src/ingestion/msedgedriver.exe" # Kiểm tra lại đường dẫn này
RESTART_EVERY_N_PAGES = 10 # <--- TẮT BẬT LẠI SAU MỖI 10 TRANG

AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
S3_BUCKET = os.getenv("S3_BUCKET_NAME")
S3_REGION = os.getenv("AWS_REGION")
S3_FOLDER = os.getenv("S3_FOLDER_PREFIX", "bronze/ebay_raw")

SEARCH_CONFIGS =[
    {
        "id": "Men's Athletic Shoes",
        "url": "https://www.ebay.com/sch/15709/i.html?_nkw=shoes&_from=R40&_oac=1"
    },
    {
        "id": "Women's Athletic Shoes",
        "url": "https://www.ebay.com/sch/95672/i.html?_nkw=shoes&_from=R40&_oac=1"
    },
    {
        "id": "Men's Casual Shoes",
        "url": "https://www.ebay.com/sch/24087/i.html?_nkw=shoes&_from=R40&_oac=1"
    },
    {
        "id": "Women's Heels",
        "url": "https://www.ebay.com/sch/55793/i.html?_nkw=shoes&_from=R40&_oac=1"
    },
    {
        "id": "Women's Boots",
        "url": "https://www.ebay.com/sch/53557/i.html?_nkw=shoes&_from=R40&_oac=1"
    },
    {
        "id": "Men's Dress Shoes",
        "url": "https://www.ebay.com/sch/53120/i.html?_nkw=shoes&_from=R40&_oac=1"
    },
    {
        "id": "Women's Flats",
        "url": "https://www.ebay.com/sch/45333/i.html?_nkw=shoes&_from=R40&_oac=1"
    },
    {
        "id": "Women's Sandals",
        "url": "https://www.ebay.com/sch/62107/i.html?_nkw=shoes&_from=R40&_oac=1"
    }
]

MAX_PAGES = 50
STATE_FILE = "crawler_state.json"

# --- 2. HÀM CHECKPOINT & S3  ---
def save_checkpoint(category_id, page_num):
    try:
        current_state = {}
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                current_state = json.load(f)
        current_state[category_id] = page_num
        with open(STATE_FILE, 'w') as f:
            json.dump(current_state, f)
        print(f"Checkpoint saved: {category_id} -> Page {page_num}")
    except Exception as e:
        print(f"Lỗi save checkpoint: {e}")

def load_checkpoint(category_id):
    if not os.path.exists(STATE_FILE): return 0
    try:
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
            return state.get(category_id, 0)
    except: return 0

def upload_to_s3(local_path, s3_key):
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY,
            region_name=S3_REGION
        )
        s3_client.upload_file(local_path, S3_BUCKET, s3_key)
        print(f"   ☁️ S3 Upload OK: {s3_key}")
        return True
    except Exception as e:
        print(f"   ❌ S3 Upload Failed: {e}")
        return False

# --- 3. HÀM KHỞI TẠO DRIVER ---
def init_driver():
    print("🔧 (Re)Starting Microsoft Edge...")
    edge_options = Options()
    edge_options.add_argument("--disable-blink-features=AutomationControlled")
    edge_options.add_argument("--start-maximized")
    # edge_options.add_argument("--headless") # Bật dòng này nếu muốn chạy ngầm
    edge_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    edge_options.add_experimental_option('useAutomationExtension', False)
    
    # Chặn ảnh để load nhanh hơn (Optional)
    # prefs = {"profile.managed_default_content_settings.images": 2}
    # edge_options.add_experimental_option("prefs", prefs)

    try:
        service = Service(executable_path=DRIVER_PATH)
        driver = webdriver.Edge(service=service, options=edge_options)
        return driver
    except Exception as e:
        print(f"❌ Lỗi mở Edge: {e}")
        raise e

# --- 4. HÀM CÀO DỮ LIỆU TRANG (Core Logic) ---
def extract_page_items(driver):
    products = []
    try:
        # Lấy link sản phẩm (Chỉ lấy link sạch, bỏ tham số rác sau dấu ?)
        links = driver.find_elements(By.XPATH, "//a[contains(@href, '/itm/')]")
        urls = list(set([l.get_attribute("href").split("?")[0] for l in links]))
        
        # Giới hạn số lượng nếu cần test nhanh (bỏ dòng này để lấy hết)
        # urls = urls[:5] 
        
        print(f"   found {len(urls)} items. Extracting...")
        
        for url in urls:
            # Mở tab mới để giữ tab danh sách không bị load lại
            driver.execute_script("window.open('');")
            driver.switch_to.window(driver.window_handles[-1])
            
            try:
                driver.get(url)
                time.sleep(random.uniform(1, 2)) # Nghỉ ngắn để tránh bị block
                
                item = {"url": url, "specs": {}, "image_url": None}
                
                # A. Lấy Specs (Thông số kỹ thuật)
                try:
                    box = driver.find_element(By.CSS_SELECTOR, ".ux-layout-section-module-evo, .x-about-this-item")
                    labels = box.find_elements(By.CLASS_NAME, "ux-labels-values__labels")
                    values = box.find_elements(By.CLASS_NAME, "ux-labels-values__values")
                    for l, v in zip(labels, values):
                        key = l.text.replace(":", "").strip()
                        if key: item["specs"][key] = v.text.strip()
                except: pass
                
                # B. Lấy Ảnh (Chỉ lấy 1 ảnh nét nhất)
                try:
                    img_candidates = driver.find_elements(By.CSS_SELECTOR, 
                        ".x-photos-min-view__main-image img, .ux-image-carousel-item.active img"
                    )
                    for img in img_candidates:
                        src = img.get_attribute("src") or ""
                        if "i.ebayimg.com" in src:
                            item["image_url"] = re.sub(r's-l\d+', 's-l1600', src) # Force HD
                            break
                except: pass

                # C. Tên & Giá
                try: item["name"] = driver.find_element(By.CSS_SELECTOR, "h1.x-item-title__mainTitle span").text
                except: item["name"] = "Unknown"
                
                try: item["price"] = driver.find_element(By.CSS_SELECTOR, ".x-price-primary, .x-price-approx__price").text
                except: item["price"] = "0"
                
                if item["name"] != "Unknown":
                    products.append(item)
                    
            except Exception as e:
                # print(f"Lỗi item: {e}") 
                pass
            finally:
                driver.close() # Đóng tab sản phẩm
                driver.switch_to.window(driver.window_handles[0]) # Quay về tab danh sách
                
    except Exception as e:
        print(f"   ⚠️ Lỗi trang danh sách: {e}")
        
    return products

# --- 5. HÀM CHẠY CHÍNH (UPDATE LOGIC RESTART) ---
def run_smart_crawler():
    if not AWS_ACCESS_KEY:
        print("❌ LỖI: Chưa cấu hình .env")
        return

    batch_date = datetime.now().strftime("%Y-%m-%d")
    driver = None # Khởi tạo biến driver

    try:
        for config in SEARCH_CONFIGS:
            cat_id = config["id"]
            base_url = config["url"]
            
            # Load Checkpoint xem đã cào đến đâu rồi
            last_page_done = load_checkpoint(cat_id)
            start_page = last_page_done + 1
            
            print(f"\n📦 CATEGORY: {cat_id}")
            if start_page > MAX_PAGES:
                print(f"   ✅ Đã xong danh mục này.")
                continue
            
            print(f"   🔄 Tiếp tục từ trang {start_page}...")

            # --- VÒNG LẶP TRANG ---
            for page in range(start_page, MAX_PAGES + 1):
                
                # 1. KIỂM TRA & KHỞI TẠO DRIVER
                # Nếu chưa có driver HOẶC đến lúc phải restart
                if driver is None or (page - 1) % RESTART_EVERY_N_PAGES == 0:
                    if driver:
                        print(f"♻️ Đã cào {RESTART_EVERY_N_PAGES} trang. Restarting driver để giải phóng RAM...")
                        driver.quit()
                        time.sleep(5) # Nghỉ chút cho máy mát
                    
                    driver = init_driver()

                print(f"   📄 Processing Page {page}/{MAX_PAGES}...")
                
                # 2. MỞ TRANG DANH SÁCH
                separator = "&" if "?" in base_url else "?"
                target_url = f"{base_url}{separator}_pgn={page}"
                
                try:
                    driver.get(target_url)
                    time.sleep(3)
                    
                    if "No exact matches found" in driver.page_source:
                        print("   ⚠️ Hết hàng. Dừng.")
                        save_checkpoint(cat_id, MAX_PAGES)
                        break
                    
                    # 3. CÀO DỮ LIỆU
                    data = extract_page_items(driver)
                    
                    # 4. LƯU & UPLOAD
                    if data:
                        filename = f"{cat_id}_p{page}_{int(time.time())}.json"
                        
                        # Lưu tạm
                        with open(filename, 'w', encoding='utf-8') as f:
                            json.dump(data, f, indent=4, ensure_ascii=False)
                        
                        # Upload S3
                        s3_key = f"{S3_FOLDER}/{batch_date}/{cat_id}/{filename}"
                        if upload_to_s3(filename, s3_key):
                            os.remove(filename) # Xóa ngay sau khi upload
                            save_checkpoint(cat_id, page) # Lưu checkpoint
                    else:
                        print("   ⚠️ Trang trống (có thể lỗi mạng hoặc hết hàng).")
                        
                except Exception as e:
                    print(f"❌ Lỗi xử lý trang {page}: {e}")
                    # Nếu lỗi nặng (mất mạng/driver chết), force restart ở vòng lặp sau
                    try: driver.quit()
                    except: pass
                    driver = None 
                    continue # Thử lại trang này (vì chưa save checkpoint)

    except KeyboardInterrupt:
        print("\n🛑 Dừng thủ công.")
    except Exception as e:
        print(f"❌ ERROR LỚN: {e}")
    finally:
        if driver:
            print("👋 Đóng trình duyệt...")
            driver.quit()

if __name__ == "__main__":
    run_smart_crawler()