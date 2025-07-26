import os
import imaplib
import email
from dotenv import load_dotenv
import logging
from datetime import datetime, timedelta
import chardet # 导入 chardet 库
from backend.email_server.email_processor import EmailProcessor
from backend.chatgpt_handlers.email_analyzer import EmailAnalyzer
from backend.data_storage.email_data_manager import EmailDataManager
from backend.email_server.email_name_decode import IMAP_UTF7_Decoder # 导入解码器

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class EmailFetcher:
    """
    用于连接IMAP服务器并获取邮件的类。
    """
    def __init__(self):
        """
        初始化EmailFetcher，从环境变量加载配置。
        """
        # 从项目根目录加载 .env 文件，并强制覆盖现有环境变量
        load_dotenv(override=True)
        self.imap_server = os.getenv("IMAP_SERVER")
        self.imap_port = int(os.getenv("IMAP_PORT"))
        self.username = os.getenv("IMAP_USERNAME")
        self.password = os.getenv("IMAP_PASSWORD")
        self.mailbox_name = os.getenv("MAILBOX", "INBOX") # 从环境变量加载mailbox，默认为INBOX
        self.mail = None
        self.decoder = IMAP_UTF7_Decoder() # 实例化解码器
        logging.info("EmailFetcher 初始化完成，配置已加载。")

    def connect(self):
        """
        连接到IMAP服务器并登录。
        """
        try:
            logging.info(f"尝试连接到IMAP服务器: {self.imap_server}:{self.imap_port}")
            self.mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            self.mail.login(self.username, self.password)
            logging.info(f"成功登录到邮箱: {self.username}")
        except Exception as e:
            logging.error(f"连接或登录IMAP服务器失败: {e}")
            raise

    def list_mailboxes(self):
        """
        获取IMAP服务器上的所有邮箱列表。

        Returns:
            dict: 包含邮箱名称映射的字典，键为原始邮箱名，值为解码后的邮箱名。
        """
        if not self.mail:
            logging.warning("IMAP连接未建立，请先调用connect()方法。")
            return {}
        
        try:
            logging.info("正在获取邮箱列表...")
            status, mailbox_list = self.mail.list()
            if status != 'OK':
                logging.error(f"获取邮箱列表失败: {status}")
                return {}

            mailboxes_map = {}
            for item in mailbox_list:
                # item 是一个字节字符串，格式类似于: b'(\\HasNoChildren) "/" "INBOX"'
                # 我们需要解析出邮箱名
                # 尝试使用IMAP修改UTF-7解码，如果失败则回退到utf-8
                try:
                    # IMAP LIST命令返回的邮箱名通常是IMAP修改UTF-7编码的
                    # 但Python的imaplib.list()返回的item是原始字节串，需要先decode成字符串
                    # 这里的item.decode('utf-8', 'ignore')是针对整个LIST响应行的，
                    # 实际的邮箱名部分可能需要IMAP_UTF7_Decoder处理
                    decoded_item = item.decode('utf-8', 'ignore')
                    parts = decoded_item.split(' "/" ')
                    if len(parts) == 2:
                        original_mailbox_name = parts[1].strip('"')
                        # 尝试解码邮箱名
                        decoded_mailbox_name = self.decoder.decode_string(original_mailbox_name)
                        mailboxes_map[original_mailbox_name] = decoded_mailbox_name
                except Exception as decode_e:
                    logging.warning(f"解码邮箱名 '{item}' 失败: {decode_e}. 将使用原始名称。")
                    # 如果解码失败，尝试直接解析并使用原始名称
                    try:
                        parts = item.decode('utf-8', 'ignore').split(' "/" ')
                        if len(parts) == 2:
                            original_mailbox_name = parts[1].strip('"')
                            mailboxes_map[original_mailbox_name] = original_mailbox_name # 使用原始名称作为解码结果
                    except Exception as fallback_e:
                        logging.error(f"回退解析邮箱名 '{item}' 失败: {fallback_e}")
            
            logging.info(f"成功获取到 {len(mailboxes_map)} 个邮箱。")
            return mailboxes_map
        except Exception as e:
            logging.error(f"获取邮箱列表时发生错误: {e}")
            return {}

    def fetch_emails(self, mailbox="INBOX", criteria='ALL'):
        """
        从指定邮箱获取邮件。

        Args:
            mailbox (str): 要选择的邮箱，默认为"INBOX"。
            criteria (str): 邮件搜索条件，默认为'ALL'（所有邮件）。
                            例如: 'UNSEEN', 'FROM "sender@example.com"', 'SUBJECT "Test"'
        Returns:
            list: 包含邮件内容的列表，每封邮件是一个字典。
        """
        if not self.mail:
            logging.warning("IMAP连接未建立，请先调用connect()方法。")
            return []

        try:
            logging.info(f"选择邮箱: {mailbox}")
            # 将邮箱名编码为IMAP兼容的UTF-7格式
            # IMAP协议的邮箱名通常需要以UTF-7编码，或者更准确地说是IMAP的修改UTF-7规范
            # Python的imaplib库在处理非ASCII邮箱名时，需要进行此编码
            encoded_mailbox = mailbox.encode('utf-7').decode('ascii')
            status, messages = self.mail.select(encoded_mailbox)
            if status != 'OK':
                logging.error(f"选择邮箱失败: {status}")
                return []

            logging.info(f"搜索邮件，条件: {criteria}")
            status, message_numbers = self.mail.search(None, criteria)
            if status != 'OK':
                logging.error(f"搜索邮件失败: {status}")
                return []

            email_list = []
            for num in message_numbers[0].split():
                status, data = self.mail.fetch(num, '(RFC822)')
                if status != 'OK':
                    logging.warning(f"获取邮件 {num} 失败: {status}")
                    continue

                msg = email.message_from_bytes(data[0][1])
                
                # 解码主题，处理乱码
                decoded_subject = ""
                try:
                    # decode_header 返回一个 (value, charset) 对的列表
                    # 遍历列表并解码每个部分
                    parts = email.header.decode_header(msg.get("Subject", ""))
                    for value, charset in parts:
                        if isinstance(value, bytes):
                            try:
                                decoded_subject += value.decode(charset or 'utf-8', errors='replace')
                            except (UnicodeDecodeError, LookupError):
                                decoded_subject += value.decode('latin-1', errors='replace') # 尝试其他编码或替换错误
                        else:
                            decoded_subject += value
                except Exception as e:
                    logging.warning(f"解码邮件主题失败: {e}")
                    decoded_subject = msg.get("Subject", "") # 失败则使用原始主题

                # 解码发件人，处理乱码
                decoded_from = ""
                try:
                    parts = email.header.decode_header(msg.get("From", ""))
                    for value, charset in parts:
                        if isinstance(value, bytes):
                            try:
                                decoded_from += value.decode(charset or 'utf-8', errors='replace')
                            except (UnicodeDecodeError, LookupError):
                                decoded_from += value.decode('latin-1', errors='replace')
                        else:
                            decoded_from += value
                except Exception as e:
                    logging.warning(f"解码邮件发件人失败: {e}")
                    decoded_from = msg.get("From", "") # 失败则使用原始发件人

                mail_data = {
                    "From": decoded_from, # 使用解码后的发件人
                    "To": msg.get("To"),
                    "Subject": decoded_subject, # 使用解码后的主题
                    "Date": msg.get("Date"),
                    "Body": self._get_email_body(msg), # 仍然提供解析后的body，但用户主要关注Raw
                    "Raw": data[0][1] # 原始RFC822数据
                }
                email_list.append(mail_data)
                logging.info(f"已获取邮件: Subject='{msg.get('Subject')}' From='{msg.get('From')}'")
            return email_list
        except Exception as e:
            logging.error(f"获取邮件过程中发生错误: {e}")
            return []

    def _get_email_body(self, msg):
        """
        解析邮件内容，获取文本部分。
        """
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                cdispo = str(part.get('Content-Disposition'))

                # 忽略附件
                if ctype == 'text/html' and 'attachment' not in cdispo:
                    payload = part.get_payload(decode=True)
                    detected_charset = chardet.detect(payload)['encoding']
                    try:
                        # 优先获取HTML内容，尝试使用检测到的编码，如果失败则回退到utf-8或latin-1
                        body = payload.decode(detected_charset or part.get_content_charset() or 'utf-8', errors='replace')
                        break # 如果成功获取HTML，则不再继续查找纯文本
                    except Exception as e:
                        logging.warning(f"解码邮件HTML部分失败 (尝试编码: {detected_charset}): {e}")
                elif ctype == 'text/plain' and 'attachment' not in cdispo:
                    if not body: # 如果HTML内容未找到或解码失败，则尝试获取纯文本
                        payload = part.get_payload(decode=True)
                        detected_charset = chardet.detect(payload)['encoding']
                        try:
                            body = payload.decode(detected_charset or part.get_content_charset() or 'utf-8', errors='replace')
                        except Exception as e:
                            logging.warning(f"解码邮件文本部分失败 (尝试编码: {detected_charset}): {e}")
        else:
            payload = msg.get_payload(decode=True)
            detected_charset = chardet.detect(payload)['encoding']
            try:
                body = payload.decode(detected_charset or msg.get_content_charset() or 'utf-8', errors='replace')
            except Exception as e:
                logging.warning(f"解码邮件单一部分失败 (尝试编码: {detected_charset}): {e}")
        return body

    def logout(self):
        """
        从IMAP服务器登出并关闭连接。
        """
        if self.mail:
            try:
                self.mail.logout()
                logging.info("成功从IMAP服务器登出。")
            except Exception as e:
                logging.error(f"登出IMAP服务器失败: {e}")
            finally:
                self.mail = None

if __name__ == "__main__":
    fetcher = EmailFetcher()
    try:
        fetcher.connect()
        # 示例：获取所有邮件
        # 您可以修改 'mailbox' 和 'criteria' 参数来指定要读取的邮件。
        # 例如：
        # emails = fetcher.fetch_emails(mailbox="INBOX", criteria='ALL') # 获取收件箱所有邮件
        # emails = fetcher.fetch_emails(mailbox="INBOX", criteria='UNSEEN') # 获取收件箱所有未读邮件
        # emails = fetcher.fetch_emails(mailbox="INBOX", criteria='FROM "sender@example.com"') # 获取来自特定发件人的邮件
        # emails = fetcher.fetch_emails(mailbox="INBOX", criteria='SUBJECT "Your Subject Here"') # 获取主题包含特定内容的邮件

        # 获取今天的邮件
        date_criteria = (datetime.now() - timedelta(days=0)).strftime('%d-%b-%Y') # 获取昨天的日期


        logging.info(f"搜索日期: {date_criteria}")

        # 获取指定日期之后的邮件
        emails = fetcher.fetch_emails(mailbox=fetcher.mailbox_name, criteria=f'SINCE {date_criteria}')[:3]
        if emails:
            logging.info(f"获取到 {len(emails)} 封邮件。")
            for i, email_data in enumerate(emails):
                logging.info(f"\n--- 邮件 {i+1} ---")
                logging.info(f"发件人: {email_data['From']}")
                logging.info(f"主题: {email_data['Subject']}")
                logging.info(f"日期: {email_data['Date']}")
                
                # 使用 EmailProcessor 处理原始邮件数据
                processor = EmailProcessor()
                processed_data = processor.process_email_for_chatgpt(email_data['Body']) # 传入HTML内容
                
                # logging.info(f"ChatGPT 格式化文本内容:\n{processed_data['text_content']}")
                # logging.info(f"ChatGPT 格式化图片URL:\n{processed_data['image_urls']}")
                
                # 将处理后的数据转换为ChatGPT messages格式，包含所有邮件信息
                chatgpt_messages = processor.format_for_chatgpt_messages(
                    email_data['From'],
                    email_data['Subject'],
                    email_data['Date'],
                    processed_data['text_content'],
                    processed_data['image_urls']
                )
                # logging.info(f"ChatGPT Messages 格式:\n{chatgpt_messages}")

                # 使用 EmailAnalyzer 处理邮件
                try:
                    analyzer = EmailAnalyzer()
                    # 使用 'all_in_one' prompt 处理邮件
                    all_in_one_result = analyzer.analyze_email(chatgpt_messages, "all_in_one")
                    logging.info(f"\n--- 邮件综合分析结果 ---")
                    logging.info(all_in_one_result)

                    # 解析并存储数据
                    try:
                        data_manager = EmailDataManager()
                        # 传递 mailbox_name 给 save_email_data
                        data_manager.save_email_data(email_data, all_in_one_result, fetcher.mailbox_name)
                        data_manager.close()
                    except Exception as db_e:
                        logging.error(f"数据存储失败: {db_e}")

                except Exception as e:
                    logging.error(f"邮件分析失败: {e}")
                
                # 原始数据仍然可以打印，如果需要详细调试
                # logging.info(f"原始数据:\n{email_data['Raw'].decode('utf-8', errors='replace')}") 
        else:
            logging.info("没有获取到邮件。")
    except Exception as e:
        logging.error(f"程序执行过程中发生错误: {e}")
    finally:
        fetcher.logout()
