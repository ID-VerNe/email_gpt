import logging
from datetime import datetime, timedelta
import os
import sys
import openai
from dotenv import load_dotenv
import time # 导入 time 模块

# 将项目根目录添加到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.email_server.email_fetcher import EmailFetcher
from backend.email_server.email_processor import EmailProcessor
from backend.chatgpt_handlers.email_analyzer import EmailAnalyzer
from backend.data_storage.email_data_manager import EmailDataManager

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 加载环境变量
load_dotenv()

def update_emails_from_server():
    """
    主函数，用于获取、检查、分析和存储新邮件。
    """
    fetcher = EmailFetcher()
    data_manager = EmailDataManager() # db_path 将从 .env 加载
    
    try:
        # 1. 连接到邮件服务器
        fetcher.connect()

        # 2. 从 .env 文件获取搜索条件
        days_ago = int(os.getenv("FETCH_DAYS_AGO", 1))
        mailbox = os.getenv("MAILBOX", "INBOX")
        date_criteria = (datetime.now() - timedelta(days=days_ago)).strftime('%d-%b-%Y')
        criteria = f'SINCE {date_criteria}'
        
        logging.info(f"开始从邮箱 '{mailbox}' 获取 '{criteria}' 的邮件...")
        emails = fetcher.fetch_emails(mailbox=mailbox, criteria=criteria)
        
        if not emails:
            logging.info("没有找到新邮件。")
            return

        logging.info(f"获取到 {len(emails)} 封邮件，开始处理...")

        # 3. 初始化处理器和分析器
        processor = EmailProcessor()
        analyzer = EmailAnalyzer()

        # 4. 遍历邮件并更新到数据库
        for email_data in emails:
            subject = email_data.get('Subject')
            received_date = email_data.get('Date')
            # 从原始 'From' 字段解析出纯邮箱地址用于检查
            _, from_email = data_manager._parse_from_address(email_data.get('From'))

            # 检查邮件是否已存在
            if data_manager.email_exists(subject, from_email, received_date):
                logging.info(f"邮件 '{subject}' 已存在于数据库中，跳过。")
                continue

            logging.info(f"处理新邮件: '{subject}'")
            
            # a. 处理邮件内容
            processed_data = processor.process_email_for_chatgpt(email_data['Body'])
            
            # b. 格式化为ChatGPT输入
            chatgpt_messages = processor.format_for_chatgpt_messages(
                email_data['From'],
                subject,
                received_date,
                processed_data['text_content'],
                processed_data['image_urls']
            )
            
            # c. 使用AI分析邮件，带重试逻辑
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # 第一次尝试：带图片分析
                    all_in_one_result = analyzer.analyze_email(chatgpt_messages, "all_in_one", include_images=True)
                    logging.info(f"邮件 '{subject}' (带图片)分析成功。")
                    break # 成功则跳出重试循环
                except openai.APIError as e:
                    if "Request timed out." in str(e):
                        delay = 20
                        logging.warning(f"带图片的邮件分析请求超时: {e}。将在 {delay} 秒后重试 (尝试 {attempt + 1}/{max_retries})...")
                        time.sleep(delay)
                    else:
                        delay = 10
                        logging.warning(f"带图片的邮件分析失败: {e}。将在 {delay} 秒后重试 (尝试 {attempt + 1}/{max_retries})...")
                        time.sleep(delay)
                except Exception as e:
                    delay = 10
                    logging.warning(f"带图片的邮件分析发生未知错误: {e}。将在 {delay} 秒后重试 (尝试 {attempt + 1}/{max_retries})...")
                    time.sleep(delay)
            else: # 如果所有重试都失败了
                logging.error(f"邮件 '{subject}' 经过 {max_retries} 次重试后仍无法带图片分析。将尝试不带图片进行分析...")
                try:
                    # 尝试不带图片分析
                    all_in_one_result = analyzer.analyze_email(chatgpt_messages, "all_in_one", include_images=False)
                    logging.info(f"邮件 '{subject}' (不带图片)分析成功。")
                except Exception as retry_e:
                    logging.error(f"邮件 '{subject}' 不带图片的分析也失败了: {retry_e}")
                    continue # 跳过这封邮件的处理

            # d. 存储到数据库
            try:
                # 传递 mailbox 参数
                data_manager.save_email_data(email_data, all_in_one_result, mailbox)
            except Exception as db_e:
                logging.error(f"存储邮件 '{subject}' 到数据库失败: {db_e}")
            
            time.sleep(5) # 每处理一封邮件后等待5秒

    except Exception as e:
        logging.error(f"执行邮件更新时发生严重错误: {e}")
    finally:
        # 5. 关闭连接
        if fetcher:
            fetcher.logout()
        if data_manager:
            data_manager.close()
        logging.info("邮件更新流程结束。")

if __name__ == "__main__":
    update_emails_from_server()
