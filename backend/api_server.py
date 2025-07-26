import sqlite3
import json
import os
import logging
import sys
# 将项目根目录添加到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from dotenv import load_dotenv, set_key, dotenv_values
import subprocess
import time
import threading
from backend.email_server.email_fetcher import EmailFetcher

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 加载环境变量
load_dotenv()

# 计算 frontend/build 目录的路径
# __file__ 是 src/api_server.py -> os.path.dirname(__file__) 是 src/
# os.path.join(..., '..') 移动到项目根目录
# os.path.join(..., 'frontend', 'build') 指向静态文件目录
build_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend', 'build')

app = Flask(__name__, static_folder=build_dir, static_url_path='')
# 为所有路由启用CORS，允许来自任何源的请求
CORS(app)

def get_db_connection():
    """创建并返回一个数据库连接。"""
    # 每次连接数据库时重新加载 .env 文件，确保获取最新配置
    load_dotenv(override=True)
    db_path = os.getenv('DB_PATH')
    if not db_path:
        logging.error("DB_PATH 环境变量未设置。")
        raise ValueError("DB_PATH not configured in .env file")
    
    if not os.path.exists(db_path):
        logging.error(f"数据库文件未找到: {db_path}")
        raise FileNotFoundError(f"Database file not found at {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # 这让我们可以通过列名访问数据
    return conn

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    """服务前端React应用的静态文件。"""
    # 如果请求的路径存在于静态文件夹中（例如 /static/js/main.js），则提供该文件
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return app.send_static_file(path)
    # 否则，提供主页 index.html，让 React Router 处理前端路由
    else:
        return app.send_static_file('index.html')


@app.route('/api/emails', methods=['GET'])
def get_emails():
    """获取所有邮件数据的API端点。"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 每次请求时重新加载 .env 文件，确保获取最新配置
        load_dotenv(override=True) # override=True 强制重新加载并覆盖现有环境变量
        mailbox_filter = os.getenv("MAILBOX")
        
        if mailbox_filter:
            # 如果 MAILBOX 存在，则按 mailbox 过滤邮件
            cursor.execute("""
                SELECT id, subject, from_name, from_email, received_date, 
                       raw_email_body, analysis_markdown, analysis_json, mailbox
                FROM emails 
                WHERE mailbox = ?
                ORDER BY received_date DESC
            """, (mailbox_filter,))
            logging.info(f"正在获取邮箱 '{mailbox_filter}' 中的邮件。")
        else:
            # 如果 MAILBOX 不存在，则获取所有邮件（或者可以定义一个默认行为）
            cursor.execute("""
                SELECT id, subject, from_name, from_email, received_date, 
                       raw_email_body, analysis_markdown, analysis_json, mailbox
                FROM emails 
                ORDER BY received_date DESC
            """)
            logging.info("MAILBOX 环境变量未设置，获取所有邮件。")

        emails_rows = cursor.fetchall()
        conn.close()

        emails_list = []
        for row in emails_rows:
            email_dict = dict(row)
            # 尝试解析 analysis_json 字段
            try:
                if email_dict.get('analysis_json'):
                    email_dict['analysis_json'] = json.loads(email_dict['analysis_json'])
                else:
                    email_dict['analysis_json'] = {}
            except (json.JSONDecodeError, TypeError) as e:
                logging.warning(f"邮件 ID {email_dict.get('id')} 的 analysis_json 解析失败: {e}. 将其设置为空字典。")
                email_dict['analysis_json'] = {}
            
            emails_list.append(email_dict)
            
        return jsonify(emails_list)
    except Exception as e:
        logging.error(f"获取邮件时发生错误: {e}", exc_info=True)
        return jsonify({"error": "服务器内部错误", "message": str(e)}), 500

@app.route('/api/sync-emails', methods=['POST', 'GET'])
def sync_emails():
    """触发邮件同步和数据库整理，并以流式响应返回实时日志。"""
    logging.info("收到同步邮件请求，开始流式传输日志。")

    def generate_output():
        """生成器函数，用于执行脚本并逐行产生输出。"""
        try:
            python_executable = os.path.join(os.getcwd(), '.venv', 'Scripts', 'python.exe')
            if not os.path.exists(python_executable):
                raise FileNotFoundError("Python 解释器未在 .venv/Scripts/python.exe 中找到。")

            scripts = [
                ("邮件更新", os.path.join(os.getcwd(), 'backend', 'update_emails.py')),
                ("数据库整理", os.path.join(os.getcwd(), 'backend', 'organize_database.py'))
            ]

            for name, script_path in scripts:
                yield f"data: --- 开始执行: {name} ---\n\n"
                logging.info(f"执行命令: {python_executable} {script_path}")

                process = subprocess.Popen(
                    [python_executable, script_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,  # 将 stderr 重定向到 stdout
                    text=True,
                    cwd=os.getcwd(),
                    bufsize=1,
                    universal_newlines=True
                )

                # 逐行读取输出
                for line in process.stdout:
                    # SSE 格式要求以 'data: ' 开头，以 '\n\n' 结尾
                    yield f"data: {line.strip()}\n\n"
                
                process.wait()  # 等待子进程结束

                if process.returncode != 0:
                    error_message = f"脚本 '{name}' 执行失败，返回码: {process.returncode}。"
                    logging.error(error_message)
                    yield f"data: ERROR: {error_message}\n\n"
                    # 如果一个脚本失败，则终止整个流程
                    return
                
                yield f"data: --- 完成: {name} ---\n\n"

            yield "data: SYNC_COMPLETE\n\n"  # 发送一个特殊信号表示全部完成

        except FileNotFoundError as e:
            error_msg = f"执行环境错误: {e}"
            logging.error(error_msg)
            yield f"data: ERROR: {error_msg}\n\n"
        except Exception as e:
            error_msg = f"同步过程中发生未知错误: {e}"
            logging.error(error_msg, exc_info=True)
            yield f"data: ERROR: {error_msg}\n\n"

    # 返回一个流式响应
    return Response(generate_output(), mimetype='text/event-stream')

@app.route('/api/settings', methods=['GET'])
def get_settings():
    """获取 .env 文件中的设置。"""
    try:
        env_path = os.path.join(os.getcwd(), '.env')
        if not os.path.exists(env_path):
            return jsonify({"error": ".env 文件未找到"}), 404
        
        # 读取 .env 文件内容
        settings = dotenv_values(env_path)
        # 过滤掉敏感信息，例如密码，或者只返回允许修改的键
        # 这里为了演示，返回所有键，但实际应用中应谨慎
        filtered_settings = {k: v for k, v in settings.items() if k not in ['OPENAI_API_KEY']} # 示例：不返回敏感信息
        return jsonify(filtered_settings), 200
    except Exception as e:
        logging.error(f"获取设置时发生错误: {e}", exc_info=True)
        return jsonify({"error": "服务器内部错误", "message": str(e)}), 500

@app.route('/api/mailboxes', methods=['GET'])
def get_mailboxes():
    """获取邮箱列表的API端点。"""
    fetcher = EmailFetcher()
    try:
        fetcher.connect()
        mailboxes = fetcher.list_mailboxes()
        fetcher.logout()
        return jsonify(mailboxes), 200
    except Exception as e:
        logging.error(f"获取邮箱列表时发生错误: {e}", exc_info=True)
        return jsonify({"error": "服务器内部错误", "message": str(e)}), 500

@app.route('/api/settings', methods=['POST'])
def update_settings():
    """更新 .env 文件中的设置并尝试重启后端服务。"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "请求体为空或不是有效的JSON"}), 400

    env_path = os.path.join(os.getcwd(), '.env')
    if not os.path.exists(env_path):
        return jsonify({"error": ".env 文件未找到"}), 404

    try:
        # 更新 .env 文件
        for key, value in data.items():
            # 仅允许更新已存在的键，防止注入新键
            if key in dotenv_values(env_path):
                set_key(env_path, key, value)
                logging.info(f"更新 .env: {key}={value}")
            else:
                logging.warning(f"尝试更新不存在的键: {key}")
        
        # 强制重新加载环境变量，确保当前进程也使用最新配置
        load_dotenv(override=True)

        # 尝试重启应用
        # 这种方法会替换当前进程，可能导致请求中断
        # 更好的方法是使用外部进程管理器，但这里为了满足“自动重启”要求
        def restart_server():
            logging.info("尝试重启服务器...")
            time.sleep(1) # 确保当前响应发送出去
            python = sys.executable
            # 获取当前脚本的完整路径
            script_path = os.path.abspath(sys.argv[0])
            # 重新执行当前脚本，并传递相同的命令行参数
            os.execl(python, python, script_path, *sys.argv[1:])

        # 在一个新线程中执行重启，以允许当前请求完成
        threading.Thread(target=restart_server).start()

        return jsonify({"message": "设置已保存，服务器正在重启..."}), 200
    except Exception as e:
        logging.error(f"更新设置或重启服务器时发生错误: {e}", exc_info=True)
        return jsonify({"error": "服务器内部错误", "message": str(e)}), 500

if __name__ == '__main__':
    # 在 0.0.0.0 上运行，使其可以从本地网络访问
    # React 开发服务器通常在 3000 端口，所以我们用 5001 避免冲突
    app.run(host='0.0.0.0', port=5001, debug=True)
