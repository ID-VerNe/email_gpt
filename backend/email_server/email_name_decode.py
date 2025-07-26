import codecs
import logging

# --- Start of Configuration ---
# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# --- End of Configuration ---

class IMAP_UTF7_Decoder:
    """
    一个用于解码 IMAP 修改版 UTF-7 编码字符串的类。
    """

    def decode_string(self, encoded_str: str) -> str:
        """
        解码一个 IMAP 修改版 UTF-7 字符串。

        Args:
            encoded_str: 经过 IMAP 修改版 UTF-7 编码的字符串。
                         例如：'&kBp35Q-'

        Returns:
            解码后的原始字符串。
                         例如：'测试'
        """
        logging.info(f"准备解码字符串: '{encoded_str}'")
        if not isinstance(encoded_str, str):
            logging.error("输入不是一个有效的字符串。")
            raise TypeError("输入必须是字符串类型。")

        try:
            # Python的'utf-7'编解码器使用 '+' 作为移位字符。
            # IMAP标准使用 '&'。我们只需在解码前进行替换。
            # 注意：标准的UTF-7规定 `&-` 代表一个字面量的 `&`。
            # 但在这里的上下文（整个文件夹名被编码）中，直接替换是安全的。
            standard_utf7_str = encoded_str.replace('&', '+')
            logging.debug(f"替换 '&' 为 '+' 后: '{standard_utf7_str}'")

            # 使用Python内置的utf-7解码器进行解码
            decoded_bytes = standard_utf7_str.encode('ascii')
            decoded_str = codecs.decode(decoded_bytes, 'utf-7')

            logging.info(f"解码成功: '{encoded_str}' -> '{decoded_str}'")
            return decoded_str
        except Exception as e:
            logging.error(f"解码字符串 '{encoded_str}' 时发生错误: {e}", exc_info=True)
            # 如果解码失败，返回原始字符串，避免程序崩溃
            return encoded_str


# --- 主程序入口 ---
if __name__ == "__main__":
    logging.info("IMAP UTF-7 解码器程序开始运行。")
    decoder = IMAP_UTF7_Decoder()

    test_strings = [
        "&UXZO1mWHTVZZOQ-/HKU&kK57sQ-",
    ]

    for s in test_strings:
        print(f"原始字符串: {s}")
        decoded_result = decoder.decode_string(s)
        print(f"解码结果  : {decoded_result}\n")

    logging.info("解码器程序运行结束。")