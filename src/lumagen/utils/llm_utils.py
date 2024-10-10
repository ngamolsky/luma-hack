import tiktoken


def count_tokens(text: str, encoding_name: str = "cl100k_base") -> int:
    """
    Count the number of tokens in a given text using tiktoken.

    Args:
        text (str): The input text to count tokens for.
        encoding_name (str): The name of the encoding to use. Default is "cl100k_base".

    Returns:
        int: The number of tokens in the text.
    """
    encoding = tiktoken.get_encoding(encoding_name)
    return len(encoding.encode(text))
