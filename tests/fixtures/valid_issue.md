# Bug: Division by Zero Error

## Description

When dividing by zero, Python should raise a `ZeroDivisionError`, but the error message is unclear.

## Expected Behavior

Should raise `ZeroDivisionError: division by zero`

## Actual Behavior

Raises `ZeroDivisionError: division by zero`

## Code to Reproduce

```python
def divide(a, b):
    return a / b

result = divide(10, 0)
print(result)
```

## Environment

- Python 3.11
- No external dependencies
