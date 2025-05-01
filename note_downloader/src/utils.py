import os
import requests
import yaml
import logging
import time
# Selenium imports remain necessary for launching browser and getting cookies
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
# By, Keys, WebDriverWait, EC might not be strictly needed for manual login,
# but keep them for now in case of future modifications or partial automation.
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import WebDriverException, TimeoutException # Import specific exceptions

# 配置日志记录 (保留)
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
log = logging.getLogger(__name__)

def load_config(path="config.yaml"):
    """加载 YAML 配置文件"""
    # (load_config 函数保持不变)
    try:
        with open(path, 'r', encoding="utf-8") as f:
            config = yaml.safe_load(f)
            log.info(f"配置文件 '{path}' 加载成功。")
            return config
    except FileNotFoundError:
        log.error(f"错误：配置文件 '{path}' 未找到。")
        raise
    except yaml.YAMLError as e:
        log.error(f"错误：解析配置文件 '{path}' 失败: {e}")
        raise
    except Exception as e:
        log.error(f"加载配置文件时发生未知错误: {e}")
        raise

# 手动登录版本的 get_session 函数
def get_session(cfg):
    """
    手动登录版：
    1. 启动带界面的 Chrome
    2. 打开登录页，用户在浏览器里完成用户名/密码输入及验证
    3. 按回车后，脚本把浏览器 Cookie 导入 requests.Session
    """
    base_url = cfg.get("base_url")
    login_path = cfg.get("login_path", "/login/index.php")
    credentials = cfg.get("credentials", {}) # 获取凭证，虽然不用自动填，但检查配置可能有用

    # 检查 base_url 是否配置
    if not base_url:
        log.error("配置错误：'base_url' 缺失。")
        raise ValueError("配置信息不完整，无法确定登录 URL。")

    login_url = base_url.rstrip('/') + '/' + login_path.lstrip('/')

    # 1. 启动有界面的 Chrome
    log.info("启动 Selenium WebDriver (Chrome)...")
    chrome_opts = Options()
    # 确保没有 headless 参数
    # chrome_opts.add_argument("--headless") # 保持注释或移除
    chrome_opts.add_argument("--disable-gpu") # 某些系统需要
    # 可以添加其他选项，例如指定用户数据目录 (如果想复用浏览器配置/扩展)
    # chrome_opts.add_argument("--user-data-dir=path/to/your/chrome/profile")
    chrome_opts.add_argument("--window-size=1024,768") # 可以调整窗口大小
    chrome_opts.add_argument("--log-level=3")
    
    driver = None # 初始化 driver 变量
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_opts)
        log.info("WebDriver 启动成功，将打开浏览器窗口。")
    except WebDriverException as e:
         log.error(f"启动 WebDriver 时出错: {e}")
         log.error("请确保 Chrome 浏览器已安装，并且网络连接正常以下载/更新 ChromeDriver。")
         raise RuntimeError("无法启动 Chrome WebDriver。") from e
    except Exception as e:
         log.exception("启动 WebDriver 时发生未预料的错误")
         raise RuntimeError("启动 Chrome WebDriver 失败。") from e

    session = None # 初始化 session

    try:
        # 2. 打开登录页
        log.info(f"请在打开的浏览器窗口中完成登录，登录页面：{login_url}")
        log.info("完成所有登录步骤（包括用户名、密码、验证码、二次验证等）后，")
        log.info("确保已跳转到 Moodle 主界面或仪表盘页面。")
        driver.get(login_url)

        # === 自动检测登录状态 ===
        log.info("等待用户在浏览器中登录...")
        wait_timeout = 300 # 设置超时时间（秒），例如 5 分钟
        try:
            # 等待 URL 不再是登录页，并且包含基础 URL (表示可能跳转成功)
            # 注意: 如果登录后跳转到完全不同的域，此逻辑可能需要调整
            # 更可靠的方法是等待某个登录后才出现的特定元素 ID
            WebDriverWait(driver, wait_timeout).until(
                lambda d: login_url not in d.current_url and base_url in d.current_url
                # 或者等待某个特定元素出现:
                # EC.presence_of_element_located((By.ID, "some_element_id_only_visible_after_login"))
            )
            log.info("检测到页面跳转，可能已登录成功。")
        except TimeoutException:
            log.error(f"在 {wait_timeout} 秒内未检测到登录成功（URL 未改变或未包含基础 URL）。请检查浏览器窗口。")
            raise RuntimeError(f"登录超时（{wait_timeout}秒）。")
        except Exception as wait_err:
             log.error(f"等待登录时发生错误: {wait_err}")
             raise RuntimeError("等待登录时出错。") from wait_err

        # 3. 检测到登录后，把所有 Cookie 导入 requests.Session
        log.info("尝试从浏览器获取 Cookies...")
        session = requests.Session()
        session.headers.update({
             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }) # 保留 User-Agent

        selenium_cookies = driver.get_cookies()
        if not selenium_cookies:
             # 用户可能未登录成功就按了回车，或者 Cookies 获取失败
             current_url = driver.current_url
             log.error(f"未能从浏览器获取到任何 Cookies。当前浏览器 URL: {current_url}")
             log.error("请确保你已在浏览器中成功登录到 Moodle 主界面。如果已登录，这可能是一个罕见错误。")
             raise RuntimeError("无法获取浏览器 Cookies，登录失败或 Cookie 提取出错。")

        log.info(f"成功获取 {len(selenium_cookies)} 个 Cookies，开始注入到 requests.Session...")
        for c in selenium_cookies:
            cookie_args = {
                "name": c.get("name"), "value": c.get("value"),
                "domain": c.get("domain"), "path": c.get("path", "/")
            }
            if c.get("expiry"): cookie_args["expires"] = int(c["expiry"])
            cookie_args["secure"] = c.get("secure", False)
            cookie_args = {k: v for k, v in cookie_args.items() if v is not None and k is not None} # 再次检查 key 也不是 None
            # 增加调试日志级别
            log.debug(f"处理 Cookie: Name={cookie_args.get('name')}, Domain={cookie_args.get('domain')}, Path={cookie_args.get('path')}")
            try:
                if cookie_args.get('name') and cookie_args.get('value') is not None: # 确保 name 和 value 存在
                    session.cookies.set(**cookie_args)
                else:
                    log.warning(f"跳过无效的 Cookie 数据: {c}")
            except Exception as cookie_err:
                 log.warning(f"设置 Cookie 时出错 (Name: {c.get('name')}, Domain: {c.get('domain')}): {cookie_err} - 跳过此 Cookie。")


        session.base_url = base_url.rstrip('/') # 存储 base_url
        log.info("[SUCCESS] 已成功导入浏览器 Cookie，返回已认证的 requests.Session。")
        return session

    except Exception as e:
         # 捕获 input 等待期间或 Cookie 处理中的错误
         log.exception("处理手动登录或 Cookie 注入时发生错误")
         raise RuntimeError("手动登录过程中发生错误。") from e
    finally:
        # 确保浏览器在脚本结束或出错时关闭
        if driver:
            log.info("关闭 Selenium WebDriver 浏览器窗口...")
            driver.quit()
            log.info("WebDriver 已关闭。")

# 保留原来的 safe_mkdir 函数
def safe_mkdir(path):
    """安全地创建目录（如果不存在）"""
    if not os.path.exists(path):
        log.info(f"创建目录：{path}")
        os.makedirs(path)
    else:
        log.debug(f"目录已存在：{path}")
