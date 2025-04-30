# What is Recursion?
# This example demonstrates how recursion works by calculating the factorial of a number

def factorial(n):
    """Recursive function to calculate the factorial of a given number."""
    # Base case: if n is 0, return 1
    if n == 0:
        return 1
    # Recursive case: multiply n by the factorial of (n - 1)
    return n * factorial(n - 1)

# Test the function with an example
print(factorial(5))  # Output should be 120

# Breakdown of recursive calls:
# factorial(5) = 5 * factorial(4)
# factorial(4) = 4 * factorial(3)
# factorial(3) = 3 * factorial(2)
# factorial(2) = 2 * factorial(1)
# factorial(1) = 1 * factorial(0)
# factorial(0) = 1 (base case)
