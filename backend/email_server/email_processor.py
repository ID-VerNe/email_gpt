import email
from bs4 import BeautifulSoup
import logging
import urllib.parse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class EmailProcessor:
    """
    用于处理原始邮件数据，提取文本内容和图片链接，并转换为ChatGPT友好格式的类。
    """
    def __init__(self):
        logging.info("EmailProcessor 初始化完成。")

    def process_email_for_chatgpt(self, html_content):
        """
        从HTML内容中提取文本内容和图片链接，并格式化为ChatGPT能使用的结构。

        Args:
            html_content (str): 邮件的HTML内容字符串。

        Returns:
            dict: 包含 'text_content' 和 'image_urls' 的字典。
                  'text_content' 是纯文本内容。
                  'image_urls' 是一个包含所有图片URL的列表。
        """
        text_content = ""
        image_urls = []

        if html_content:
            try:
                soup = BeautifulSoup(html_content, 'html.parser')

                # 提取所有图片链接，并过滤掉GIF格式
                for img in soup.find_all('img'):
                    if 'src' in img.attrs:
                        img_url = img['src']
                        # 解析URL以获取路径部分，忽略查询参数
                        parsed_url = urllib.parse.urlparse(img_url)
                        path = parsed_url.path
                        # 检查路径的扩展名，如果不是gif，则添加
                        if not path.lower().endswith('.gif'):
                            image_urls.append(img_url)
                        else:
                            # logging.info(f"已跳过GIF图片: {img_url}")
                            pass
                
                # 提取纯文本内容（从HTML中），处理P标签换行问题
                paragraphs = soup.find_all('p')
                if paragraphs:
                    text_content = "\n".join([p.get_text(strip=True) for p in paragraphs])
                else:
                    # 如果没有P标签，则使用默认的get_text
                    text_content = soup.get_text(separator='\n', strip=True)
            except Exception as e:
                logging.warning(f"处理HTML内容失败: {e}")
        
        return {
            "text_content": text_content,
            "image_urls": image_urls
        }

    def format_for_chatgpt_messages(self, from_field, subject_field, date_field, text_content, image_urls):
        """
        将提取的邮件信息转换为ChatGPT的messages格式。

        Args:
            from_field (str): 发件人信息。
            subject_field (str): 主题信息。
            date_field (str): 日期信息。
            text_content (str): 纯文本内容。
            image_urls (list): 包含所有图片URL的列表。

        Returns:
            list: 符合ChatGPT messages格式的列表。
        """
        messages = []
        content_parts = []

        # 添加邮件元数据作为文本内容的一部分
        metadata_text = f"发件人: {from_field}\n主题: {subject_field}\n日期: {date_field}\n\n"
        # content_parts.append({"type": "text", "text": metadata_text})

        # 添加邮件正文文本
        if text_content:
            text_content = metadata_text + text_content

        content_parts.append({"type": "text", "text": text_content})

        # 添加图片URL，并清理MIME类型
        for url in image_urls:
            # 检查是否是data URI
            if url.startswith('data:image'):
                # 分离MIME类型和数据部分
                header, data = url.split(',', 1)
                mime_type = header.split(';')[0].split(':')[1]
                # 重组为不含charset的data URI
                clean_url = f"data:{mime_type};base64,{data}"
            else:
                # 如果不是data URI，则保持原样
                clean_url = url

            content_parts.append({
                "type": "image_url",
                "image_url": {
                    "url": clean_url,
                    "detail": "auto"
                }
            })

        # 将所有内容部分组合成一个user消息
        if content_parts:
            messages.append({
                "role": "user",
                "content": content_parts
            })

        return messages

if __name__ == "__main__":
    # 这是一个简单的测试用例，实际使用时会从EmailFetcher获取HTML内容
    sample_html_content_single_image = """
<html>
<body>
<p>图片测试</p>
<img src="https://portali.hku.hk/bulkemail/html_email/images/0775dfa8eb52b13783955aa8b1f52df5.jpeg" alt="Image 1">
</body>
</html>
"""
    sample_html_content_multiple_images = """
<html>
<body>
<p>双图测试</p>
<img src="http://example.com/image1.jpg" alt="Image 1">
<p>Another paragraph.</p>
<img src="https://example.com/image2.png" alt="Image 2">
</body>
</html>
"""
    sample_html_content_text_only = """
<html>
<body>
<p>各位唔係hall住嘅同學：</p>
<p>想有hall activity但係又冇residential hall住嘅你？返到大學冇地方落腳？返嚟上實體堂，撞正天地堂，成日流流長點過？想識多啲唔同嘅朋友，又唔知點算好？</p>
</body>
</html>
"""

    processor = EmailProcessor()

    # 模拟邮件元数据
    sample_from = "Test Sender <test@example.com>"
    sample_subject = "Test Subject"
    sample_date = "Fri, 25 Jul 2025 09:00:00 +0800"

    # 测试单图
    processed_data_single = processor.process_email_for_chatgpt(sample_html_content_single_image)
    chatgpt_messages_single = processor.format_for_chatgpt_messages(
        sample_from, sample_subject, sample_date,
        processed_data_single['text_content'], processed_data_single['image_urls']
    )
    logging.info(f"单图测试结果:\n{chatgpt_messages_single}")

    # 测试多图
    processed_data_multiple = processor.process_email_for_chatgpt(sample_html_content_multiple_images)
    chatgpt_messages_multiple = processor.format_for_chatgpt_messages(
        sample_from, sample_subject, sample_date,
        processed_data_multiple['text_content'], processed_data_multiple['image_urls']
    )
    logging.info(f"多图测试结果:\n{chatgpt_messages_multiple}")

    # 测试纯文本
    processed_data_text_only = processor.process_email_for_chatgpt(sample_html_content_text_only)
    chatgpt_messages_text_only = processor.format_for_chatgpt_messages(
        sample_from, sample_subject, sample_date,
        processed_data_text_only['text_content'], processed_data_text_only['image_urls']
    )
    logging.info(f"纯文本测试结果:\n{chatgpt_messages_text_only}")
