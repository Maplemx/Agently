import functools


def exposed_interface(type='command'):
    """修饰对外提供的接口调用，支持传参"""
    def decorator(method):
        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            # 调用所有前置拦截方法
            for interceptor in self._pre_command_interceptors:
                interceptor(self, type, method.__name__, *args, **kwargs)

            # 调用实际的方法
            result = method(self, *args, **kwargs)

            # 调用所有后置拦截方法
            for interceptor in self._post_command_interceptors:
                interceptor(self, type, method.__name__, result)

            return result
        return wrapper
    return decorator