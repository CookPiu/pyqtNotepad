import os
import requests
from urllib.parse import urljoin, unquote, urlparse # Keep unquote here
from bs4 import BeautifulSoup
from tqdm import tqdm
from . import utils # 导入我们自己的 utils 模块
import re   # 导入 re 用于更复杂的 文件名提取
from . import checker # 导入新的 checker 模块
from .classifier import FileClassifier # 导入分类器

log = utils.log # 复用 utils 中的 logger

def _get_filename_from_headers(headers):
    """尝试从 Content-Disposition 响应头中提取文件名"""
    content_disposition = headers.get('Content-Disposition')
    if content_disposition:
        # 常见的格式是 attachment; filename="some file.pdf" 或 attachment; filename*=UTF-8''some%20file.pdf
        # 使用正则表达式匹配 filename= 和 filename*=
        filenames = re.findall(r'filename\*?=([^;]+)', content_disposition, re.IGNORECASE)
        if filenames:
            filename_raw = filenames[0].strip()
            # 处理 filename="file.ext" 的情况
            if filename_raw.startswith('"') and filename_raw.endswith('"'):
                filename = filename_raw[1:-1]
            # 处理 filename*=UTF-8''encoded%20name.ext 的情况
            elif filename_raw.lower().startswith("utf-8''"):
                 filename = unquote(filename_raw[len("utf-8''"):])
            else:
                 filename = unquote(filename_raw) # 尝试直接 unquote
            if filename:
                return filename
    return None

def _get_filename_from_url(url):
    """从 URL 路径中提取文件名"""
    parsed_url = urlparse(url)
    filename = os.path.basename(parsed_url.path)
    if filename:
        return unquote(filename)
    return None

# downloader.py (Updated with manifest check and pre-classification)
def download_file(session, file_url, base_course_folder, manifest, classifier: FileClassifier): # 添加 classifier, 修改 dest_folder->base_course_folder
    """
    下载单个文件。先确定分类，然后检查Manifest/大小。
    直接下载到 基础课程目录/分类目录 下。
    直接下载到 基础课程目录/分类目录 下。
    下载后更新 manifest。
    Returns:
        str: 'DOWNLOADED', 'SKIPPED', or 'FAILED'
    """
    # 1. 解析并确定初步文件名
    filename = None
    try:
         filename_raw = os.path.basename(urlparse(file_url).path)
         filename = unquote(filename_raw) # Use unquote
         filename = re.sub(r'[\\/*?:"<>|]', "_", filename).strip()
         if not filename: filename = "downloaded_file_unnamed"
    except Exception as e:
         log.error(f"从 URL {file_url} 解析文件名失败: {e}")
         filename = "downloaded_file_error" # Fallback

    # --- 在发起网络请求前，如果已有初步文件名，先尝试分类 ---
    # 这允许我们在 HEAD 请求失败时仍能确定目标目录
    category = classifier.default # Default category
    if filename and filename != "downloaded_file_error":
        try:
            category = classifier.get_category_for_file(filename)
            log.debug(f"初步分类 '{filename}' 为 '{category}'.")
        except Exception as classify_err:
             log.error(f"对文件名 '{filename}' 进行初步分类时出错: {classify_err}. 将使用默认分类 '{category}'.")

    # 初步确定目标文件夹 (可能被 header 中的文件名覆盖后重新计算)
    final_dest_folder = os.path.join(base_course_folder, category)
    local_path = os.path.join(final_dest_folder, filename or "unknown_file") # Need a valid path even if filename parsing failed

    # --- 开始网络请求 ---
    remote_size = 0
    headers = {}
    final_url = file_url # Start with the original URL
    mode = "wb" # Default write mode

    try:
        # 2. 先 HEAD 拿远端文件大小和最终URL/文件名
        log.debug(f"发送 HEAD 请求检查 {file_url}...")
        head = session.head(file_url, allow_redirects=True, timeout=20)
        head.raise_for_status() # Will raise HTTPError for bad responses (4xx or 5xx)
        remote_size = int(head.headers.get("Content-Length", 0))
        final_url = head.url # Get the URL after any redirects

        # 尝试从 Content-Disposition 获取更准确的文件名
        header_filename_raw = _get_filename_from_headers(head.headers)
        if header_filename_raw:
            header_filename = re.sub(r'[\\/*?:"<>|]', "_", header_filename_raw).strip()
            if header_filename and header_filename != filename: # Use header filename if valid and different
                     log.info(f"使用 header 中的文件名: '{header_filename}' (替代 URL 中的: '{filename}')")
                     filename = header_filename
                     # --- 文件名改变，需要重新分类并确定最终路径 ---
                     try:
                         category = classifier.get_category_for_file(filename)
                         log.debug(f"基于 header 文件名重新分类为 '{category}'.")
                     except Exception as classify_err:
                         log.error(f"对 header 文件名 '{filename}' 分类时出错: {classify_err}. 使用默认分类 '{classifier.default}'.")
                         category = classifier.default
                     final_dest_folder = os.path.join(base_course_folder, category)
                     local_path = os.path.join(final_dest_folder, filename) # 更新最终本地路径

    except requests.exceptions.HTTPError as e:
         # Handle specific HTTP errors like 404 Not Found, 403 Forbidden
         log.error(f"HTTP Error {e.response.status_code} during HEAD request for {file_url}: {e}")
         return None # Fail download if HEAD gives definite error
    except requests.exceptions.RequestException as e:
        log.error(f"HEAD request failed for {file_url}: {e}. 无法检查大小或断点续传。将尝试直接下载。")
        remote_size = 0 # Assume size unknown if HEAD fails
    except ValueError:
         log.warning(f"无法从 HEAD 响应解析 Content-Length {file_url}。无法断点续传/跳过。")
         remote_size = 0 # Assume size unknown

    # --- 确保目标目录存在 (在所有潜在的路径计算之后) ---
    utils.safe_mkdir(final_dest_folder)

    # 3. 检查本地文件是否存在于 *最终目标路径*
    local_size = 0
    if os.path.exists(local_path):
        try:
             local_size = os.path.getsize(local_path)
        except OSError as e:
             log.error(f"无法获取本地文件大小 {local_path}: {e}。将尝试重新下载。")
             local_size = -1 # Indicate error state

    should_download = True # Default: assume download needed

    if local_size > 0: # Only check signature if file exists and size > 0
        # --- 计算 Manifest Key (相对于总的 downloads 目录) ---
        manifest_key = None
        try:
             # base_course_folder 的父目录应该是 downloads 根目录
             downloads_root = os.path.dirname(base_course_folder)
             manifest_key = os.path.relpath(local_path, downloads_root).replace('\\', '/')
             # Example: CS101/Lectures/lecture1.pdf
        except ValueError as e:
             log.error(f"无法计算 manifest 的相对路径 for {local_path} relative to {os.path.dirname(base_course_folder)}: {e}. 可能无法检查/更新 Manifest。")
             manifest_key = None # Cannot reliably use manifest

        # --- 检查 Manifest ---
        if manifest_key:
            try:
                 local_sig = checker.extract_text_signature(local_path)
                 old_sig = manifest.get(manifest_key)

                 if old_sig and local_sig and local_sig == old_sig:
                     log.info(f"[SKIP] '{filename}' 内容签名未变 ({local_sig[:8]}...)，位于 '{category}'。跳过。")
                     should_download = False # Signature match, skip download
                 elif old_sig and local_sig:
                     log.info(f"[INFO] '{filename}' 内容签名已变化 (旧: {old_sig[:8]}..., 新: {local_sig[:8]}...) 位于 '{category}'。需要下载。")
                 # else: No old signature or failed to get local sig, proceed to size check
            except Exception as sig_err:
                 log.warning(f"检查文件签名时出错 '{filename}' (位于 {category}): {sig_err}。将基于文件大小决定。")
        # else: manifest_key is None, proceed to size check

        # --- 如果未被签名跳过，则检查大小 (仅当 remote_size 已知) ---
        if should_download and remote_size > 0:
            if local_size == remote_size:
                log.info(f"[SKIP] '{filename}' 大小一致 ({local_size} bytes) 位于 '{category}'，但签名不匹配/检查失败。跳过。")
                should_download = False # Size match, skip download
            elif local_size < remote_size:
                log.info(f"[RESUME] 准备续传 '{filename}' (位于 {category}) 从 {local_size} bytes.")
                headers = {"Range": f"bytes={local_size}-"}
                mode = "ab" # Append mode
                downloaded_so_far = local_size
            else: # local_size > remote_size
                log.info(f"[REDOWNLOAD] 本地文件 '{filename}' ({local_size} bytes) 大于远程 ({remote_size} bytes) 位于 '{category}'。重新下载。")
                headers = {} # Reset headers for full download
                mode = "wb" # Overwrite mode
                downloaded_so_far = 0
        elif should_download and remote_size <= 0: # Remote size unknown, but signature check didn't skip
             log.info(f"[REDOWNLOAD] 本地文件 '{filename}' ({local_size} bytes) 存在于 '{category}'，但远程大小未知且签名检查未跳过。重新下载。")
             headers = {}
             mode = "wb"
             downloaded_so_far = 0
        # else: should_download is False (skipped by signature or size match)

    elif local_size == 0: # File exists but is empty
         log.info(f"[REDOWNLOAD] 本地文件 '{filename}' 存在但为空于 '{category}'。重新下载。")
         headers = {}
         mode = "wb"
         downloaded_so_far = 0
    elif local_size < 0: # Error getting size
         log.info(f"[REDOWNLOAD] 无法获取本地文件大小 '{filename}' (位于 {category})。重新下载。")
         headers = {}
         mode = "wb"
         downloaded_so_far = 0
    else: # File does not exist locally
        log.info(f"准备下载新文件: '{filename}' 到 '{category}' 目录")
        headers = {}
        mode = "wb"
        downloaded_so_far = 0

    # 4. 如果需要下载，执行 GET 请求
    if not should_download:
        # If we skipped based on signature or size match
        return 'SKIPPED' # Return status instead of path

    # --- 执行下载 ---
    try:
        log.debug(f"发送 GET 请求下载 {final_url}...")
        with session.get(final_url, stream=True, headers=headers, timeout=300) as r:
            r.raise_for_status() # Check for HTTP errors on GET

            # Determine total size for progress bar
            get_content_length = r.headers.get("Content-Length") # Size reported by GET
            total_for_pbar = None
            try:
                 if mode == "wb" and get_content_length:
                     total_for_pbar = int(get_content_length)
                 elif mode == "ab" and remote_size > 0: # Resuming
                     # total should be the remaining bytes
                     total_for_pbar = remote_size - downloaded_so_far
                 elif remote_size > 0: # Fallback to HEAD size if GET doesn't provide reliable length
                     total_for_pbar = remote_size if mode == "wb" else remote_size - downloaded_so_far
            except (ValueError, TypeError):
                 log.warning(f"无法确定 '{filename}' 的下载总大小，进度条可能不准确。")
                 total_for_pbar = None

            # Write to file, ensure path is correct
            log.debug(f"准备写入文件到: {local_path}")
            try:
                # Use a slightly adjusted tqdm description
                pbar_desc = f"{category}/{filename}"[:50] # Limit desc length
                with open(local_path, mode) as f, tqdm(
                    total=total_for_pbar, unit="B", unit_scale=True,
                    desc=pbar_desc, initial=0, leave=False
                 ) as bar:
                     for chunk in r.iter_content(chunk_size=1024*10): # 10KB chunks
                         if chunk:
                             bytes_written = f.write(chunk)
                             bar.update(bytes_written)
            except OSError as e:
                 log.error(f"写入文件失败 {local_path}: {e}")
                 # Attempt cleanup if download was interrupted/failed
                 if os.path.exists(local_path):
                     # Only remove if we were writing from scratch (mode wb)
                     if mode == 'wb':
                         try:
                             os.remove(local_path)
                             log.debug(f"Removed potentially incomplete file: {local_path}")
                         except OSError: pass
                 return None # Indicate failure

            # --- 下载完成，验证大小并更新 Manifest ---
            try:
                 final_size = os.path.getsize(local_path)
                 if remote_size > 0 and final_size != remote_size:
                     log.warning(f"下载完成 '{filename}'，但大小不匹配！预期 {remote_size}, 实际 {final_size}。文件可能损坏。")
                 elif remote_size > 0:
                     log.info(f"[完成] '{filename}' 已成功下载到 '{category}' ({final_size} bytes).")
                 else:
                     log.info(f"[完成] '{filename}' 已下载到 '{category}' ({final_size} bytes). 远程大小未知。")

                 # 更新 manifest (使用正确的相对路径)
                 manifest_key = None
                 try:
                      downloads_root = os.path.dirname(base_course_folder)
                      manifest_key = os.path.relpath(local_path, downloads_root).replace('\\', '/')
                      new_sig = checker.extract_text_signature(local_path)
                      if new_sig:
                          manifest[manifest_key] = new_sig
                          log.debug(f"已更新 Manifest: '{manifest_key}' -> {new_sig[:8]}...")
                      else:
                          log.warning(f"下载后无法计算签名 '{filename}' (位于 {category})，Manifest 未更新。")
                 except ValueError as e:
                      log.error(f"无法计算 Manifest 键 {local_path} rel to {downloads_root}: {e}")
                 except Exception as post_sig_err:
                      log.warning(f"下载后更新 manifest 签名时出错 '{filename}' (位于 {category}): {post_sig_err}")

                 return 'DOWNLOADED' # Return status on successful download

            except OSError as e:
                 log.error(f"下载后无法获取文件大小 {local_path}: {e}")
                 return 'FAILED' # Indicate failure if cannot get size after download

    except requests.exceptions.RequestException as e:
        log.error(f"GET request failed for {final_url}: {e}")
        return 'FAILED' # Indicate failure
    except Exception as e:
         log.error(f"下载 {filename} 时发生意外错误: {e}", exc_info=True)
         # Attempt cleanup if writing from scratch
         if mode == 'wb' and os.path.exists(local_path):
             try: os.remove(local_path)
             except OSError: pass
         return 'FAILED' # Indicate failure

def bulk_download(session, res_list, dest_folder_base, manifest, classifier: FileClassifier): # 添加 classifier
    """
    批量下载资源列表中的文件，直接下载到分类后的目录，使用 manifest 跳过。
    Returns:
        tuple: (downloaded_count, skipped_count, failed_count)
    """
    if not res_list:
        log.info("批量下载：没有资源需要处理。")
        return 0, 0, 0 # Return zero counts

    log.info(f"开始批量下载/检查 {len(res_list)} 个资源，基础课程目录: {dest_folder_base}")
    # Base folder should already exist from main.py logic
    actually_downloaded_count = 0
    skipped_count = 0
    failed_count = 0

    for i, (resource_name, res_page_url) in enumerate(tqdm(res_list, desc="处理课程资源")):
        log.debug(f"--- 处理资源 {i+1}/{len(res_list)}: '{resource_name}' ({res_page_url}) ---")
        file_url_to_download = None # Reset for each resource
        status = 'FAILED' # Default status if errors occur before download_file is called
        try:
            # 1. 尝试获取真实文件下载链接
            log.debug(f"访问资源页面 {res_page_url}...")
            r = session.get(res_page_url, timeout=30, allow_redirects=True) # Allow redirects
            r.raise_for_status()
            final_page_url = r.url
            log.debug(f"资源页面最终 URL: {final_page_url}")

            # --- 查找下载链接 (Improved Logic) ---
            soup = BeautifulSoup(r.text, "lxml")
            link_selectors = [
                'div.resourcecontent a[href*="pluginfile.php"]',
                'div.activityinstance a[href*="pluginfile.php"]',
                'a.realworkaround[href*="pluginfile.php"]', # Might exist in some themes
                'a[href*="pluginfile.php"]' # General fallback
            ]
            file_link_tag = None
            for selector in link_selectors:
                file_link_tag = soup.select_one(selector)
                if file_link_tag: break

            if file_link_tag and file_link_tag.get('href'):
                href = file_link_tag['href']
                # Ensure URL is absolute
                file_url_to_download = urljoin(final_page_url, href)
                log.debug(f"找到 pluginfile 链接: {file_url_to_download}")
            else:
                # If no specific link, check if the page itself is the file
                content_type = r.headers.get('Content-Type', '').split(';')[0].strip().lower()
                content_disposition = r.headers.get('Content-Disposition', '').lower()
                is_attachment = 'attachment' in content_disposition
                is_likely_file = is_attachment or (content_type and content_type not in ['text/html', 'text/plain', ''])

                if is_likely_file:
                     log.info(f"资源页面 {final_page_url} (Type: '{content_type}', Disp: '{content_disposition}') 可能是文件本身。")
                     file_url_to_download = final_page_url
                else:
                     log.warning(f"在 '{final_page_url}' (Type: '{content_type}') 未找到下载链接。跳过 '{resource_name}'.")
                     failed_count += 1
                     continue # Skip this resource

            # --- 调用下载函数并记录状态 ---
            if file_url_to_download:
                log.debug(f"调用 download_file for '{file_url_to_download}'")
                status = download_file(session, file_url_to_download, dest_folder_base, manifest, classifier)
                if status == 'DOWNLOADED':
                    actually_downloaded_count += 1
                elif status == 'SKIPPED':
                    skipped_count += 1
                else: # FAILED
                    failed_count += 1
            # No else needed, handled by continue above

        except requests.exceptions.Timeout:
             log.error(f"访问资源页面超时: {res_page_url}")
             failed_count += 1
        except requests.exceptions.RequestException as e:
            log.error(f"访问资源页面失败: {res_page_url} - {e}")
            failed_count += 1
        except Exception as e:
            log.exception(f"处理资源 '{resource_name}' ({res_page_url}) 时发生未预料错误")
            failed_count += 1
        # Log resource completion regardless of status for clarity, maybe not needed?
        # log.debug(f"--- 资源 '{resource_name}' 处理结束 (Status: {status}) ---")


    log.info(f"本课程批量处理完成。下载: {actually_downloaded_count}, 跳过: {skipped_count}, 失败: {failed_count}.")
    return actually_downloaded_count, skipped_count, failed_count # 返回详细计数
