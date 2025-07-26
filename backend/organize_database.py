import logging
import os
import sys
from dotenv import load_dotenv

# 将项目根目录添加到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.data_storage.email_data_manager import EmailDataManager

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 加载环境变量
load_dotenv()

def organize_database_entries():
    """
    整理数据库中所有邮件条目的 analysis_markdown 和 analysis_json 字段。
    """
    data_manager = None
    try:
        data_manager = EmailDataManager()
        logging.info("开始整理数据库中的邮件数据...")

        # 1. 获取所有需要处理的邮件
        emails_to_process = data_manager.get_all_emails_for_reprocessing()
        if not emails_to_process:
            logging.info("数据库中没有需要处理的邮件。")
            return

        logging.info(f"找到 {len(emails_to_process)} 条记录需要处理。")

        # 2. 遍历并处理每条记录
        for email_id, original_markdown in emails_to_process:
            if not original_markdown:
                logging.warning(f"邮件 ID: {email_id} 的 analysis_markdown 为空，跳过。")
                continue

            # a. 清理 markdown
            cleaned_markdown = original_markdown
            if "### 邮件摘要" not in cleaned_markdown:
                cleaned_markdown = cleaned_markdown.replace("## 邮件摘要", "### 邮件摘要")
                cleaned_markdown = cleaned_markdown.replace("## 郵件摘要", "### 邮件摘要")
                cleaned_markdown = cleaned_markdown.replace("### 意见摘要", "### 邮件摘要")

            if cleaned_markdown.strip().startswith("---"):
                cleaned_markdown = cleaned_markdown.strip()[3:].strip()

            # b. 重新生成 JSON
            new_json = data_manager.parse_markdown_to_json(cleaned_markdown)

            # c. 更新数据库
            data_manager.update_analysis_data(email_id, cleaned_markdown, new_json)

        logging.info("数据库整理完成。")

    except Exception as e:
        logging.error(f"整理数据库时发生错误: {e}")
    finally:
        if data_manager:
            data_manager.close()
        logging.info("数据库整理流程结束。")

if __name__ == "__main__":
    organize_database_entries()
