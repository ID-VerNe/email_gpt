import sqlite3
import json
import logging
import re
import os
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class EmailDataManager:
    """
    用于解析ChatGPT返回的Markdown文本，并将其与原始邮件数据一起存入SQLite数据库。
    """
    def __init__(self, db_path=None):
        """
        初始化DataManager，连接到SQLite数据库并创建表。
        """
        load_dotenv(override=True)
        if db_path is None:
            db_path = os.getenv("DB_PATH", "emails.db")

        self.db_path = db_path
        self.conn = None
        try:
            self.conn = sqlite3.connect(self.db_path)
            self._create_table()
            logging.info(f"成功连接到数据库: {self.db_path}")
        except sqlite3.Error as e:
            logging.error(f"数据库连接失败: {e}")
            raise

    def _create_table(self):
        """
        创建用于存储邮件数据的表。
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS emails (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject TEXT,
                    from_name TEXT,
                    from_email TEXT,
                    received_date TEXT,
                    raw_email_body TEXT,
                    analysis_markdown TEXT,
                    analysis_json TEXT,
                    mailbox TEXT,
                    is_starred INTEGER DEFAULT 0,
                    is_read INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.conn.commit()
            logging.info("表 'emails' 已成功创建或已存在。")
        except sqlite3.Error as e:
            logging.error(f"创建表失败: {e}")

    def _parse_from_address(self, from_string):
        """
        从 "Name <email@example.com>" 格式的字符串中提取姓名和邮箱地址。
        """
        if not from_string:
            return "", ""
        
        match = re.match(r'(.*)<(.+)>', from_string)
        if match:
            name = match.group(1).strip().strip('"')
            email = match.group(2).strip()
            return name, email
        
        # 如果没有匹配到 < >，则假定整个字符串是邮箱地址
        return "", from_string

    def email_exists(self, subject, from_email, received_date):
        """
        检查具有相同主题、发件人和接收日期的邮件是否已存在。
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT id FROM emails 
                WHERE subject = ? AND from_email = ? AND received_date = ?
            """, (subject, from_email, received_date))
            return cursor.fetchone() is not None
        except sqlite3.Error as e:
            logging.error(f"查询邮件是否存在时出错: {e}")
            return False # 发生错误时，保守地返回False

    def parse_markdown_to_json(self, markdown_text):
        """
        将特定格式的Markdown文本解析为JSON对象。
        使用正则表达式来提取各个部分。
        """
        if not markdown_text:
            return "{}"

        # 清理和规范化Markdown文本
        if "### 邮件摘要" not in markdown_text:
            markdown_text = markdown_text.replace("## 邮件摘要", "### 邮件摘要")
            markdown_text = markdown_text.replace("## 郵件摘要", "### 邮件摘要")
            markdown_text = markdown_text.replace("### 意见摘要", "### 邮件摘要")
        
        if markdown_text.strip().startswith("---"):
            markdown_text = markdown_text.strip()[3:].strip()

        data = {}
        # 使用正则表达式按 ### 分割不同的部分
        sections = re.split(r'###\s*(.+?)\n', markdown_text)
        
        # 第一个元素是空字符串或前言，跳过
        sections = sections[1:]

        for i in range(0, len(sections), 2):
            section_title = sections[i].strip()
            section_content = sections[i+1].strip()
            
            # 将标题转换为蛇形命名法 (snake_case)
            section_key = section_title.lower().replace(' ', '_')
            
            items = []
            # 按 - 分割每个条目
            entries = re.split(r'-\s*(.+?)(?=\n-|\Z)', section_content, flags=re.DOTALL)
            entries = [e.strip() for e in entries if e.strip()]

            for entry in entries:
                item_data = {}
                lines = entry.split('\n')
                # 第一行是主条目
                main_line = lines[0]
                key, _, value = main_line.partition(':')
                item_data[key.strip()] = value.strip()

                # 后续行是子条目
                for line in lines[1:]:
                    line = line.strip()
                    if ':' in line:
                        sub_key, _, sub_value = line.partition(':')
                        item_data[sub_key.strip()] = sub_value.strip()
                items.append(item_data)
            
            data[section_key] = items

        return json.dumps(data, ensure_ascii=False, indent=4)

    def save_email_data(self, email_data, analysis_markdown, mailbox):
        """
        将邮件数据、分析结果（Markdown和JSON）存入数据库。

        Args:
            email_data (dict): 包含 'From', 'Subject', 'Date', 'Body' 的邮件字典。
            analysis_markdown (str): ChatGPT返回的Markdown格式分析结果。
            mailbox (str): 邮件所属的邮箱名称。
        """
        try:
            analysis_json = self.parse_markdown_to_json(analysis_markdown)
            
            cursor = self.conn.cursor()
            from_name, from_email = self._parse_from_address(email_data.get('From'))

            cursor.execute("""
                INSERT INTO emails (subject, from_name, from_email, received_date, raw_email_body, analysis_markdown, analysis_json, mailbox)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                email_data.get('Subject'),
                from_name,
                from_email,
                email_data.get('Date'),
                email_data.get('Body'),
                analysis_markdown,
                analysis_json,
                mailbox
            ))
            self.conn.commit()
            logging.info(f"成功将邮件 '{email_data.get('Subject')}' 的数据存入数据库。")
        except sqlite3.Error as e:
            logging.error(f"数据存储失败: {e}")
        except Exception as e:
            logging.error(f"解析或存储过程中发生错误: {e}")

    def get_email_by_id(self, email_id):
        """
        根据邮件ID获取单个邮件的完整数据。
        """
        try:
            # 使用 row_factory 使结果可以按列名访问
            self.conn.row_factory = sqlite3.Row
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM emails WHERE id = ?", (email_id,))
            row = cursor.fetchone()
            self.conn.row_factory = None # 重置 row_factory
            return dict(row) if row else None
        except sqlite3.Error as e:
            logging.error(f"获取邮件 ID: {email_id} 失败: {e}")
            return None

    def get_all_emails_for_reprocessing(self):
        """
        获取所有需要重新处理的邮件 (id 和 analysis_markdown)。
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT id, analysis_markdown FROM emails")
            return cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"获取所有邮件失败: {e}")
            return []

    def update_analysis_data(self, email_id, new_markdown, new_json):
        """
        根据邮件ID更新 analysis_markdown 和 analysis_json 字段。
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                UPDATE emails
                SET analysis_markdown = ?, analysis_json = ?
                WHERE id = ?
            """, (new_markdown, new_json, email_id))
            self.conn.commit()
            logging.info(f"成功更新邮件 ID: {email_id} 的分析数据。")
        except sqlite3.Error as e:
            logging.error(f"更新邮件 ID: {email_id} 失败: {e}")

    def update_email_status(self, email_id, is_starred=None, is_read=None):
        """
        根据邮件ID更新邮件的星标或已读状态。
        """
        try:
            cursor = self.conn.cursor()
            updates = []
            params = []

            if is_starred is not None:
                updates.append("is_starred = ?")
                params.append(1 if is_starred else 0)
            if is_read is not None:
                updates.append("is_read = ?")
                params.append(1 if is_read else 0)

            if not updates:
                logging.warning(f"未为邮件 ID: {email_id} 提供任何更新字段。")
                return

            query = f"UPDATE emails SET {', '.join(updates)} WHERE id = ?"
            params.append(email_id)

            cursor.execute(query, tuple(params))
            self.conn.commit()
            logging.info(f"成功更新邮件 ID: {email_id} 的状态。")
        except sqlite3.Error as e:
            logging.error(f"更新邮件 ID: {email_id} 状态失败: {e}")

    def update_email_urgency(self, email_id, new_urgency):
        """
        更新指定邮件的紧急程度。
        这将修改 analysis_markdown 和 analysis_json。
        """
        try:
            email = self.get_email_by_id(email_id)
            if not email:
                logging.error(f"未找到邮件 ID: {email_id}，无法更新紧急程度。")
                return None

            # 1. 更新 analysis_json
            analysis_json_str = email.get('analysis_json', '{}')
            analysis_data = json.loads(analysis_json_str)

            urgency_keys = ['邮件紧急程度评估', '郵件緊急程度評估']
            urgency_field_keys = ['- **紧急程度**', '- **緊急程度**']
            
            updated_json = False
            for key in urgency_keys:
                if key in analysis_data and isinstance(analysis_data.get(key), list) and analysis_data.get(key):
                    for field_key in urgency_field_keys:
                        if field_key in analysis_data[key][0]:
                            analysis_data[key][0][field_key] = new_urgency
                            updated_json = True
                            break
                if updated_json:
                    break
            
            if not updated_json:
                logging.warning(f"在邮件 ID: {email_id} 的 JSON 中未找到紧急程度字段，将创建它。")
                # 确保主键存在
                if urgency_keys[0] not in analysis_data:
                    analysis_data[urgency_keys[0]] = []
                # 确保列表不为空
                if not analysis_data[urgency_keys[0]]:
                    analysis_data[urgency_keys[0]].append({})
                # 设置值
                analysis_data[urgency_keys[0]][0][urgency_field_keys[0]] = new_urgency

            new_json_str = json.dumps(analysis_data, ensure_ascii=False, indent=4)

            # 2. 更新 analysis_markdown
            analysis_markdown = email.get('analysis_markdown', '')
            # 正则表达式匹配 "- **紧急程度**: xxx" 或 "- **緊急程度**: xxx"
            urgency_pattern = re.compile(r"(-\s*\*\*(?:紧急|緊急)程度\*\*:\s*)(.*)", re.IGNORECASE)
            
            if urgency_pattern.search(analysis_markdown):
                new_markdown = urgency_pattern.sub(r"\1" + new_urgency, analysis_markdown)
            else:
                # 如果在markdown中找不到，则在末尾追加
                logging.warning(f"在邮件 ID: {email_id} 的 Markdown 中未找到紧急程度部分，将进行追加。")
                new_markdown = analysis_markdown.strip() + f"\n\n### 邮件紧急程度评估\n\n- **紧急程度**: {new_urgency}\n"

            # 3. 保存回数据库
            self.update_analysis_data(email_id, new_markdown, new_json_str)
            
            # 返回更新后的完整邮件数据
            return self.get_email_by_id(email_id)

        except json.JSONDecodeError as e:
            logging.error(f"解析邮件 ID: {email_id} 的 JSON 失败: {e}")
            return None
        except Exception as e:
            logging.error(f"更新邮件 ID: {email_id} 紧急程度时发生未知错误: {e}")
            return None

    def close(self):
        """
        关闭数据库连接。
        """
        if self.conn:
            self.conn.close()
            logging.info("数据库连接已关闭。")

if __name__ == '__main__':
    # 这是一个简单的测试用例
    sample_markdown = """
### 邮件摘要

- **主题**: HKU Daily Notices (25 JUL 2025)
- **发件人**: eNotices System <enotices.daily.digest@hku.hk>
- **日期**: Fri, 25 Jul 2025 00:11:51 +0800
- **摘要**: 此邮件为香港大学的每日通知摘要...

### 工作安排

- **任务/会议**: ‘Enterprise and Economy in Modern China’ Conference Keynote Lecture
  - **描述**: Economic History of Asia as a Regional Entity...
  - **日期/时间**: Aug 21
- **任务/会议**: Chinese Business History Conference
  - **描述**: Enterprise and Economy in Modern China
  - **日期/时间**: Aug 21-23

### 行动事项

- **事项**: Register for Certificate Course
  - **截止日期**: August 1st 2025
  - **状态**: 待办
"""
    sample_email_data = {
        'Subject': 'HKU Daily Notices (25 JUL 2025)',
        'From': 'eNotices System <enotices.daily.digest@hku.hk>',
        'Date': 'Fri, 25 Jul 2025 00:11:51 +0800',
        'Body': '...raw email body...'
    }

    manager = EmailDataManager(db_path='test_emails.db')
    try:
        # 测试解析
        json_result = manager.parse_markdown_to_json(sample_markdown)
        logging.info("解析结果 (JSON):")
        print(json_result)

        # 测试存储
        # 假设测试用例的mailbox为 'test_mailbox'
        manager.save_email_data(sample_email_data, sample_markdown, 'test_mailbox')
    finally:
        manager.close()
