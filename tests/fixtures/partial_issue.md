# Bug: Pandas DataFrame Issue

## Description

Getting a weird error when trying to convert DataFrame column to int.

## Expected Behavior

Should convert to integer without error.

## Actual Behavior

Raises ValueError

## Code to Reproduce

```python
import pandas as pd
import numpy as np

df = pd.DataFrame({'col': [1, 2, np.nan]})
df['col'].astype(int)
```

## Environment

- pandas 2.0.0
- numpy 1.24.0
