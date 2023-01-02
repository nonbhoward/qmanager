from time import time


def announce_duration(timed_func):
    """Monitor execution time of functions and announce result

    :param timed_func: the function to be timed
    :return: the timing wrapper
    """
    def wrapper(*args, **kwargs):
        # execute function
        time_before = time()
        timed_func(*args, **kwargs)
        time_after = time()

        # format time and get wrapped function name
        time_elapsed = int(1000 * (time_after - time_before))
        print(f'{timed_func.__name__} executed in {time_elapsed}ms')
    return wrapper
