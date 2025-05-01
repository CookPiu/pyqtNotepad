from . import utils
from . import crawler
from . import downloader
from .classifier import FileClassifier # 导入类
from . import checker # 导入 checker 以便提前加载 manifest
import os
import re
import sys
import time # 导入 time 模块

log = utils.log # 复用 utils 中的 logger

def sanitize_foldername(name):
    """清理字符串，使其成为安全的文件夹名称"""
    # 移除或替换 Windows 和 Linux/Mac 文件系统中非法的字符
    name = re.sub(r'[\\/*?:"<>|\r\n]+', '_', name)
    # 移除可能导致问题的首尾空格或点
    name = name.strip('. ')
    # 防止空文件名
    if not name:
        name = "untitled_course"
    return name

def main():
    """主执行函数"""
    start_time = time.time() # 记录开始时间
    log.info("=" * 50)
    log.info("--- Note Downloader 开始运行 ---")
    log.info("=" * 50)
    cfg = None
    session = None
    # --- 新增总计计数器 ---
    total_courses_found = 0
    processed_courses_success = 0
    processed_courses_failed = 0
    total_files_downloaded = 0
    total_files_skipped = 0
    total_files_failed = 0

    try:
        # === 步骤 1: 加载配置 ===
        config_file_path = os.path.join("config", "config.yaml")
        log.info(f"[步骤 1/5] 加载配置文件 '{config_file_path}'...")
        try:
            cfg = utils.load_config(config_file_path)
        except Exception as config_err:
            log.critical(f"加载配置文件失败，无法继续: {config_err}")
            sys.exit(1)

        # === 步骤 1b: 定义下载目录和 Manifest 路径 ===
        download_dir_name = cfg.get("download_directory", "downloads")
        downloads_root = os.path.abspath(download_dir_name)
        manifest_path  = os.path.join(downloads_root, "manifest.json") # Manifest 文件放在下载根目录
        # === 步骤 1c: 加载 Manifest (替换旧的预分类/构建逻辑) ===
        log.info(f"--- [预处理 1/2] 加载现有文件清单: {manifest_path} ---")
        manifest = checker.load_manifest(manifest_path) # load_manifest 会处理文件不存在或错误的情况

        # === 步骤 1d: 初始化分类器 ===
        log.info(f"--- [预处理 2/2] 初始化文件分类器...")
        # 修正规则文件路径，假设脚本从 note_downloader 目录运行
        rules_file_path = os.path.join("config", "classify_rules.yaml")
        classifier_instance = FileClassifier(rules_path=rules_file_path)
        # FileClassifier 的 __init__ 会处理规则文件不存在或错误的情况

        # === 步骤 2: 登录并获取 session === (保持不变)
        log.info("[步骤 2/5] 登录 Moodle 并获取会话...")
        try:
            session = utils.get_session(cfg)
        except Exception as login_err:
            log.critical(f"登录 Moodle 失败，无法继续: {login_err}")
            sys.exit(1)

        # === 步骤 3: 获取课程列表 ===
        log.info("[步骤 3/5] 获取课程列表...")
        try:
            courses = crawler.get_course_list(session, cfg) # crawler.py 内部已有错误处理和日志
            total_courses_found = len(courses)
            if not courses:
                log.warning("未能从 Moodle 获取到任何课程列表。请检查登录状态或 Moodle 页面结构。")
                # 不退出，但后面循环不会执行
            else:
                 log.info(f"成功获取 {total_courses_found} 门课程。")
        except Exception as crawl_list_err:
             log.error(f"获取课程列表时发生错误，无法继续: {crawl_list_err}", exc_info=True)
             sys.exit(1)


        # === 步骤 4: 定义基础下载目录 ===
        # 允许在 config.yaml 配置下载目录，默认为 'downloads'
        download_dir_name = cfg.get("download_directory", "downloads")
        base_download_dir = os.path.abspath(download_dir_name)
        log.info(f"[步骤 4/5] 检查/创建基础下载目录: {base_download_dir}")
        try:
             utils.safe_mkdir(base_download_dir)
        except Exception as mkdir_err:
             log.critical(f"无法创建基础下载目录 '{base_download_dir}'，无法继续: {mkdir_err}")
             sys.exit(1)


        # === 步骤 5: 遍历课程，下载和分类资源 ===
        if total_courses_found > 0:
            log.info(f"[步骤 5/5] 开始遍历 {total_courses_found} 门课程进行处理...")
            for i, (course_name, course_url) in enumerate(courses):
                course_start_time = time.time()
                log.info("-" * 40)
                log.info(f"-> 开始处理课程 [{i+1}/{total_courses_found}]: '{course_name}'")
                log.debug(f"   课程 URL: {course_url}")
                course_failed_flag = False # 标记当前课程处理是否失败

                try:
                    # --- 5.1 创建课程目录 ---
                    safe_course_name = sanitize_foldername(course_name)
                    course_download_folder = os.path.join(base_download_dir, safe_course_name)
                    log.debug(f"   创建课程子目录: {course_download_folder}")
                    utils.safe_mkdir(course_download_folder)

                    # --- 5.2 获取资源链接 ---
                    log.info(f"   [{i+1}/{total_courses_found}] 获取 '{course_name}' 的资源链接...")
                    resource_links = crawler.get_resource_links(session, course_url, cfg) # crawler.py 内有日志
                    if not resource_links:
                        log.info(f"   [{i+1}/{total_courses_found}] 课程 '{course_name}' 中未找到有效资源链接，跳过下载和分类。")
                        # 即使没有资源也算处理成功（指课程本身处理流程没出错）

                    else:
                        log.info(f"   [{i+1}/{total_courses_found}] 找到 {len(resource_links)} 个资源链接，准备下载...")

                        # --- 5.3 批量下载 (现在需要传递 manifest) ---
                        log.info(f"   [{i+1}/{total_courses_found}] 开始批量下载/检查资源到: {course_download_folder}")
                        # downloader.py 内的 download_file 现在会处理分类和 Manifest 更新
                        # 将 classifier_instance 传递给 bulk_download 并接收返回的计数
                        downloaded, skipped, failed = downloader.bulk_download(
                            session,
                            resource_links,
                            course_download_folder,
                            manifest,
                            classifier_instance
                        )
                        # 累加到总计数
                        total_files_downloaded += downloaded
                        total_files_skipped += skipped
                        total_files_failed += failed

                        # --- 移除下载后的分类步骤 --- (仍然移除)
                        # 分类现在在 download_file 内部完成

                except Exception as course_err:
                    # 捕获处理单个课程（获取链接、下载、分类）时发生的任何错误
                    log.exception(f"   !!! 处理课程 '{course_name}' 时发生错误 !!!")
                    course_failed_flag = True # 标记此课程失败

                # --- 单个课程处理结束日志 ---
                course_end_time = time.time()
                course_duration = course_end_time - course_start_time
                if not course_failed_flag:
                     processed_courses_success += 1
                     log.info(f"<- 课程 [{i+1}/{total_courses_found}] '{course_name}' 处理成功 (耗时: {course_duration:.2f} 秒)")
                else:
                     processed_courses_failed += 1
                     log.error(f"<- 课程 [{i+1}/{total_courses_found}] '{course_name}' 处理失败 (耗时: {course_duration:.2f} 秒)")
                log.info("-" * 40)
        else:
             log.info("[步骤 5/5] 未找到课程，跳过课程处理步骤。")

    # === 全局错误处理 (通常是启动阶段错误，已在前面处理并退出) ===
    except KeyboardInterrupt:
        log.warning("\n !!! 用户请求中断程序运行 !!!")
        # 退出码 0 通常表示正常退出，这里因用户中断也用 0
        # 统计信息会在 finally 中显示
        sys.exit(0)
    except Exception as general_err:
        # 捕获任何未被特定处理的异常
        log.critical("!!! 发生未预料的严重错误，程序意外终止 !!!", exc_info=True)
        sys.exit(1) # 非正常退出
    finally:
        # === 运行结束总结 ===
        end_time = time.time()
        duration = end_time - start_time
        log.info("=" * 50)
        log.info("--- Note Downloader 运行结束 ---")
        log.info(f"总耗时: {duration:.2f} 秒")
        log.info(f"共找到课程数: {total_courses_found}")
        log.info(f"成功处理课程数: {processed_courses_success}")
        log.info(f"处理失败课程数: {processed_courses_failed}")
        log.info("--- 文件统计 ---")
        log.info(f"实际下载文件数: {total_files_downloaded}")
        log.info(f"跳过文件数 (已存在/签名未变): {total_files_skipped}")
        log.info(f"处理失败文件数: {total_files_failed}")
        log.info("=" * 50)

        # === 结束前保存 Manifest === (保持不变)
        if manifest is not None and downloads_root and os.path.isdir(downloads_root): # 检查 manifest 是否存在且目录有效
             try:
                 import json # 确保 json 可用
                 # 使用 checker 里的函数来加载/保存可能更一致，但这里直接写也可以
                 with open(manifest_path, 'w', encoding='utf-8') as f:
                     json.dump(manifest, f, indent=2, ensure_ascii=False, sort_keys=True)
                 log.info(f"✅ 内容签名清单已更新并保存到: {manifest_path}")
             except ImportError:
                  log.error("   无法导入 'json' 模块，未能保存 Manifest。")
             except Exception as save_manifest_err:
                  log.error(f"   保存 Manifest 到 '{manifest_path}' 时出错: {save_manifest_err}")

        if session:
            session.close() # 关闭 session
            log.debug("Requests session 已关闭。")

        log.info("--- 程序执行完毕 ---") # 更明确的结束信息


if __name__ == "__main__":
    main()
