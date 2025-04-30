# Factorial using a loop

def factorial_loop(n):
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result

print("Loop Result:", factorial_loop(5))  # Output: 120

# Factorial using recursion

def factorial_recursive(n):
    if n == 0:
        return 1
    return n * factorial_recursive(n - 1)

print("Recursive Result:", factorial_recursive(5))  # Output: 120
