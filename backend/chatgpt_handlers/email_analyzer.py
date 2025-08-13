import os
import openai
from datetime import datetime
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class EmailAnalyzer:
    """
    用于与OpenAI API交互，处理邮件内容并生成分析结果的类。
    """
    def __init__(self):
        """
        初始化EmailAnalyzer，从环境变量加载OpenAI配置。
        """
        # 从项目根目录加载 .env 文件
        load_dotenv()
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL")
        self.base_url = os.getenv("OPENAI_BASE_URL")

        if not self.api_key or not self.model or not self.base_url:
            logging.error("OpenAI API配置缺失。请检查.env文件中的OPENAI_API_KEY, OPENAI_MODEL, OPENAI_BASE_URL。")
            raise ValueError("OpenAI API配置缺失。")

        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        self.prompts = self._load_prompts()
        logging.info("EmailAnalyzer 初始化完成，OpenAI配置已加载。")

    def _load_prompts(self):
        """
        从prompts目录下加载所有prompt文件。
        每个文件内容作为一个prompt，文件名（不含扩展名）作为prompt的键。
        """
        # prompts目录现在位于chatgpt_handlers下
        prompts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'prompts')
        loaded_prompts = {}
        if not os.path.exists(prompts_dir):
            logging.warning(f"Prompt目录 '{prompts_dir}' 不存在。")
            return loaded_prompts

        for filename in os.listdir(prompts_dir):
            if filename.endswith(".txt"):
                prompt_name = os.path.splitext(filename)[0]
                filepath = os.path.join(prompts_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        loaded_prompts[prompt_name] = f.read().strip()
                    logging.info(f"已加载prompt: {prompt_name}")
                except Exception as e:
                    logging.error(f"加载prompt文件 '{filepath}' 失败: {e}")
        return loaded_prompts

    def get_prompt(self, prompt_name):
        """
        获取指定名称的prompt内容。
        """
        prompt = self.prompts.get(prompt_name)
        if not prompt:
            logging.warning(f"未找到名为 '{prompt_name}' 的prompt。")
        return prompt

    def analyze_email(self, chatgpt_messages, prompt_name, include_images=True):
        """
        使用OpenAI API分析邮件内容。

        Args:
            chatgpt_messages (list): 邮件内容，已转换为ChatGPT messages格式。
            prompt_name (str): 要使用的prompt名称。
            include_images (bool): 是否在请求中包含图片。

        Returns:
            str: OpenAI API返回的分析结果文本。
        """
        system_prompt = self.get_prompt(prompt_name)
        if not system_prompt:
            raise ValueError(f"错误：未找到指定的prompt '{prompt_name}'。")

        messages_to_send = list(chatgpt_messages)

        # 如果不包含图片，则过滤掉图片内容
        if not include_images:
            logging.info("正在从API请求中移除图片...")
            new_messages = []
            for msg in messages_to_send:
                if msg['role'] == 'user' and isinstance(msg['content'], list):
                    new_content = [item for item in msg['content'] if item.get('type') == 'text']
                    # 如果过滤后还有内容，则保留该消息
                    if new_content:
                        new_messages.append({'role': 'user', 'content': new_content})
                else:
                    new_messages.append(msg)
            messages_to_send = new_messages

        # 获取当前日期
        current_date = datetime.now().strftime("%Y年%m月%d日")
        date_message = f"今天是{current_date}，请在你的回答中考虑这个信息。"

        # 将系统prompt和日期信息添加到消息列表的开头
        messages_with_system_prompt = [{"role": "system", "content": "使用中文回复，请注意语言。"},
                                       {"role": "system", "content": date_message},
                                       {"role": "system", "content": system_prompt}] + messages_to_send

        try:
            image_status = "包含图片" if include_images else "不含图片"
            logging.info(f"调用OpenAI API ({image_status})，使用模型: {self.model}，prompt: {prompt_name}")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages_with_system_prompt,
                temperature=1.0,
                top_p=1.0,
                presence_penalty=0.0,
                frequency_penalty=0.0,
            )

            analysis_result = response.choices[0].message.content
            logging.info("OpenAI API调用成功。")
            if analysis_result.startswith("```markdown\n"):
                analysis_result = analysis_result[13:-3]

            return analysis_result
        except openai.APIError as e:
            logging.error(f"OpenAI API错误: {e}")
            # 将APIError重新抛出，以便上层逻辑可以捕获并处理
            raise
        except Exception as e:
            logging.error(f"分析邮件时发生未知错误: {e}")
            # 将其他异常也重新抛出
            raise

if __name__ == "__main__":
    # 这是一个简单的测试用例
    # 确保在运行前创建 src/email_server/prompts 目录并添加一些 .txt prompt 文件
    # 并在 .env 文件中配置 OPENAI_API_KEY, OPENAI_MODEL, OPENAI_BASE_URL

    # 模拟一个ChatGPT messages格式的邮件内容
    sample_chatgpt_messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "发件人: test@example.com\n主题: 会议通知\n日期: 2025-07-25\n\n正文：请注意，下周二上午10点在会议室A召开项目进展会议。请提前准备好您的报告。"}
            ]
        }
    ]

    # 示例prompt内容（假设存在 prompts/summary.txt）
    # "你是一个邮件摘要助手，请总结邮件的关键信息。"

    try:
        analyzer = EmailAnalyzer()
        # 假设有一个名为 'summary' 的prompt文件
        analysis_result = analyzer.analyze_email(sample_chatgpt_messages, "summary")
        logging.info(f"\n--- 邮件分析结果 (summary) ---")
        logging.info(analysis_result)

        # 假设有一个名为 'task_extraction' 的prompt文件
        # analysis_result_tasks = analyzer.analyze_email(sample_chatgpt_messages, "task_extraction")
        # logging.info(f"\n--- 邮件分析结果 (task_extraction) ---")
        # logging.info(analysis_result_tasks)

    except ValueError as e:
        logging.error(f"初始化失败: {e}")
    except Exception as e:
        logging.error(f"测试过程中发生错误: {e}")
