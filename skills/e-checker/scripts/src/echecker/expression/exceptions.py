"""表达式求值异常定义

严格模式错误处理，用于表达式求值过程中的各种错误。
"""


class ExpressionError(Exception):
    """表达式求值基础异常"""
    pass


class ExpressionTypeError(ExpressionError):
    """表达式类型错误

    当操作数类型不匹配操作要求时抛出。
    例如：对字符串执行数学运算，或比较不兼容的类型。
    """
    pass


class ExpressionZeroDivisionError(ExpressionError):
    """表达式除零错误

    当除法或取模运算中除数为零时抛出。
    """
    pass


class ExpressionNameError(ExpressionError):
    """表达式未定义变量错误

    当引用未定义的变量时抛出。
    """
    pass


class ExpressionValueError(ExpressionError):
    """表达式值错误

    当值本身不合法或无法处理时抛出。
    """
    pass
