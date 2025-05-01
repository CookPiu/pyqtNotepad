from bs4 import BeautifulSoup
from urllib.parse import urljoin
from . import utils # 导入我们自己的 utils 模块
import requests # 需要导入 requests 来处理异常

log = utils.log # 复用 utils 中的 logger

# crawler.py (New function provided by user)
def get_course_list(session, cfg):
    """
    抓取“我的课程”列表。依次尝试三种方式：
      1. li.list-group-item-course-listitem a[href*='course/view.php']
      2. div.coursebox a[href*='course/view.php']
      3. 所有 href 中带 course/view.php?id= 的 <a> 标签
    都找不到时，把 /my/ 页面的 HTML dump 到 my_html_dump.html 供调试。
    """
    my_courses_path = cfg.get("my_courses_path", "/my/") # Use configured path or default
    url = urljoin(cfg["base_url"], my_courses_path) # Use urljoin for robustness
    try:
        r = session.get(url, timeout=30) # Add timeout
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        # Handle potential request errors (like connection issues, timeouts)
        print(f"[ERROR] 访问课程列表页面失败 ({url}): {e}") # Print error instead of log
        return [] # Return empty list on error

    soup = BeautifulSoup(r.text, "lxml")

    courses = []

    # 方式 1: More specific selector first
    selector1 = "li.list-group-item.course-list-item a.aalink[href*='course/view.php?id=']" # Example of a potentially more specific selector
    # Original selector from user prompt
    selector1_alt = "li.list-group-item-course-listitem a[href*='course/view.php']"
    
    elements = soup.select(selector1)
    if not elements:
        elements = soup.select(selector1_alt) # Fallback to user's original selector 1

    for a in elements:
        name = a.get_text(strip=True)
        # Try finding a more specific name element if direct text is generic
        name_span = a.find("span", class_="coursename")
        if name_span and name_span.get_text(strip=True):
            name = name_span.get_text(strip=True)
        elif not name: # If name is still empty, try title/aria-label
             name = a.get("title", "").strip() or a.get("aria-label", "").strip()

        if name: # Only add if we have a name
            href = urljoin(cfg["base_url"], a["href"])
            courses.append((name, href))

    # 方式 2: Common dashboard course box selector
    if not courses:
        selector2 = "div.coursebox.clearfix a.coursename[href*='course/view.php?id=']" # Another specific example
         # Original selector from user prompt
        selector2_alt = "div.coursebox a[href*='course/view.php']"

        elements = soup.select(selector2)
        if not elements:
             elements = soup.select(selector2_alt) # Fallback to user's original selector 2

        for a in elements:
            name = a.get_text(strip=True)
            # Coursebox might have name directly in the link
            if not name: # If name is still empty, try title/aria-label
                 name = a.get("title", "").strip() or a.get("aria-label", "").strip()

            if name: # Only add if we have a name
                href = urljoin(cfg["base_url"], a["href"])
                courses.append((name, href))

    # 方式 3: Generic fallback based on URL pattern
    if not courses:
        # User's original selector 3 - find all links matching the pattern
        for a in soup.find_all("a", href=lambda x: x and "course/view.php?id=" in x):
            # Avoid duplicates already found by specific selectors
            href = urljoin(cfg["base_url"], a["href"])
            if any(c[1] == href for c in courses):
                continue

            name = a.get_text(strip=True)
            if not name:
                # If a tag has no text, maybe look inside children like spans, or use title/aria-label
                inner_span = a.find('span') # Basic check
                if inner_span and inner_span.get_text(strip=True):
                    name = inner_span.get_text(strip=True)
                else:
                     name = a.get("title", "").strip() or a.get("aria-label", "").strip()

            # Try finding common parent structure for context if name is still missing
            if not name:
                 parent_box = a.find_parent(['div', 'li'], class_=lambda c: c and 'course' in c)
                 if parent_box:
                     # Try finding a heading or prominent text within the parent
                     heading = parent_box.find(['h1','h2','h3','h4','span'], class_=lambda c: c and 'name' in c)
                     if heading:
                         name = heading.get_text(strip=True)

            if name: # Only add if we have a name
                courses.append((name, href))
            # else: # Optional: log if a link is found but no name can be extracted
            #     print(f"[DEBUG] Found course link {href} but could not extract name.")


    # 全部失败时保存 HTML 供调试
    if not courses:
        dump_filename = "my_html_dump.html"
        try:
            with open(dump_filename, "w", encoding="utf-8") as f:
                f.write(r.text)
            print(f"[WARNING] 未找到课程列表，已将 {url} 页面的源码保存到 {dump_filename}，请打开查看并根据真实结构调整选择器。")
        except IOError as e:
            print(f"[ERROR] 无法写入调试文件 {dump_filename}: {e}")

    # Remove duplicates based on URL, keeping the first found instance
    seen_urls = set()
    unique_courses = []
    for name, href in courses:
        if href not in seen_urls:
            unique_courses.append((name, href))
            seen_urls.add(href)

    if courses and len(unique_courses) < len(courses):
        print(f"[INFO] 移除了 {len(courses) - len(unique_courses)} 个重复的课程链接。")


    print(f"[INFO] 找到 {len(unique_courses)} 门唯一课程。") # Use print instead of log
    return unique_courses


def get_resource_links(session, course_url, cfg):
    """从单个课程页面抓取资源详情页链接"""
    log.info(f"开始抓取课程资源链接：{course_url}")
    links = []
    try:
        r = session.get(course_url, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")

        # 选择器 'a.aalink[href*="mod/resource/view.php"]' 用于查找指向文件资源的链接
        # 'a.aalink[href*="mod/folder/view.php"]' 用于查找指向文件夹资源的链接 (可选，看需求)
        # 'a.aalink[href*="mod/url/view.php"]' 用于查找外部 URL 资源 (可选)
        # 可以根据需要扩展
        resource_selectors = [
            'a.aalink[href*="mod/resource/view.php"]',
            # 'a.aalink[href*="mod/folder/view.php"]', # 如果需要抓取文件夹
        ]

        for selector in resource_selectors:
            for a in soup.select(selector):
                href = a.get("href")
                if not href: continue

                # 提取资源实例名称
                inst_span = a.find("span", class_="instancename")
                if inst_span:
                    inst = inst_span.text.strip()
                else:
                    # 如果没有 instancename span，尝试直接获取 <a> 标签文本
                    inst = a.get_text(strip=True)
                    if not inst: # 如果文本也为空，使用 URL 作为备用名称
                         inst = href
                         log.warning(f"无法提取资源名称，使用链接作为名称: {inst}")


                # 确保链接是绝对 URL
                if not href.startswith(('http://', 'https://')):
                    href = urljoin(session.base_url, href)

                links.append((inst, href))
                log.debug(f"找到资源：名称='{inst}', 链接='{href}'")

        log.info(f"在课程 '{course_url}' 中找到 {len(links)} 个资源链接。")
        log.info(f"在课程 '{course_url}' 中找到 {len(links)} 个资源链接。")
        return links

    except requests.exceptions.Timeout as e:
        log.error(f"抓取课程资源页面时网络超时 ({course_url}): {e}")
        return []
    except requests.exceptions.RequestException as e:
        log.error(f"抓取课程资源页面时发生网络请求错误 ({course_url}): {e}")
        return []
    except Exception as e:
        log.exception(f"解析课程资源页面时发生未预料的错误 ({course_url})") # 使用 log.exception 记录 traceback
        return []
